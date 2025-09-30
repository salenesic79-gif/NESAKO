from __future__ import annotations
import itertools
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Optional sources
try:
    from . import sofascore
except Exception:
    sofascore = None  # type: ignore

try:
    from . import fudbal91
except Exception:
    fudbal91 = None  # type: ignore

try:
    # tsdb functions are optional
    from .tsdb import search_team as tsdb_search_team, events_next_team as tsdb_next, events_last_team as tsdb_last  # type: ignore
except Exception:
    tsdb_search_team = None  # type: ignore
    tsdb_next = None  # type: ignore
    tsdb_last = None  # type: ignore


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _match_key(s: str, t: str) -> bool:
    s, t = _norm(s), _norm(t)
    return s == t or s.replace(" ", "") == t.replace(" ", "")


def _parse_iso(iso_str: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _similar_event(a: Dict, b: Dict) -> bool:
    # Similar if same teams order-agnostic and kickoff within 30 minutes
    ma, mb = _norm(a.get("match", "")), _norm(b.get("match", ""))
    parts_a = [p.strip() for p in ma.replace("–", "-").split("-")]
    parts_b = [p.strip() for p in mb.replace("–", "-").split("-")]
    if len(parts_a) == 2 and len(parts_b) == 2:
        teams_a = set(parts_a)
        teams_b = set(parts_b)
        if teams_a != teams_b:
            return False
    else:
        if ma != mb:
            return False
    # kickoff compare
    ka = _parse_iso(a.get("kickoff", ""))
    kb = _parse_iso(b.get("kickoff", ""))
    if not ka or not kb:
        return True
    diff = abs((ka - kb).total_seconds())
    return diff <= 1800  # 30 minutes


def _confidence(agree_count: int, total_sources: int) -> float:
    if total_sources <= 0:
        return 0.0
    base = agree_count / float(total_sources)
    # Weight by timeliness (future matches more stable)
    return round(min(1.0, max(0.0, base)), 2)


def fetch_sofascore(team: Optional[str], key: Optional[str], date: Optional[str], hours: Optional[int], exact: bool, nocache: bool, debug: bool) -> Dict:
    if not sofascore:
        return {"source": "sofascore", "items": [], "error": "module_unavailable"}
    try:
        if key:
            data = sofascore.fetch_competition(key=key, hours=hours, debug=debug, team=team, date=date, nocache=nocache, exact=exact)
        else:
            data = sofascore.fetch_quick(hours=hours, keys=None, debug=debug, team=team, date=date, nocache=nocache, exact=exact)
        data["source"] = "sofascore"
        return data
    except Exception as e:
        return {"source": "sofascore", "items": [], "error": str(e)}


def fetch_fudbal91(team: Optional[str], key: Optional[str], date: Optional[str], hours: Optional[int], exact: bool, nocache: bool, debug: bool) -> Dict:
    if not fudbal91:
        return {"source": "fudbal91", "items": [], "error": "module_unavailable"}
    try:
        if key:
            data = fudbal91.fetch_competition(key, hours=hours)
        else:
            data = fudbal91.fetch_quick_odds(hours=hours)
        data["source"] = "fudbal91"
        # Team filter
        if team:
            tt = _norm(team)
            data["items"] = [it for it in data.get("items", []) if tt in _norm(it.get("match", ""))]
        return data
    except Exception as e:
        return {"source": "fudbal91", "items": [], "error": str(e)}


def fetch_tsdb(team: Optional[str], key: Optional[str], date: Optional[str], hours: Optional[int], exact: bool, nocache: bool, debug: bool) -> Dict:
    if not (tsdb_search_team and tsdb_next):
        return {"source": "tsdb", "items": [], "error": "module_unavailable"}
    try:
        items: List[Dict] = []
        if team:
            # Use TSDB search + next events
            try:
                team_id = None
                for cand in tsdb_search_team(team):  # type: ignore
                    if _match_key(cand.get("name", ""), team) or team.lower() in cand.get("name", "").lower():
                        team_id = cand.get("id")
                        break
                if team_id:
                    for ev in tsdb_next(team_id):  # type: ignore
                        items.append({
                            "league": ev.get("league", ""),
                            "match": ev.get("match", ""),
                            "kickoff": ev.get("kickoff", ""),
                            "odds": ev.get("odds", {}),
                            "source": "tsdb",
                            "eventId": ev.get("id"),
                        })
            except Exception:
                pass
        data = {"source": "tsdb", "items": items}
        return data
    except Exception as e:
        return {"source": "tsdb", "items": [], "error": str(e)}


def aggregate_verify(team: Optional[str] = None,
                      key: Optional[str] = None,
                      date: Optional[str] = None,
                      hours: Optional[int] = None,
                      exact: bool = False,
                      nocache: bool = False,
                      debug: bool = False) -> Dict:
    """Query multiple sources, cross-validate events, and compute confidence.

    Returns:
      {
        "results": [ {event, evidence: [source names], confidence: 0..1} ],
        "sources": {sofascore: {...}, fudbal91: {...}, tsdb: {...}},
        "used": ["sofascore","fudbal91","tsdb"],
      }
    """
    sources = []
    # Query all three
    sources.append(fetch_sofascore(team, key, date, hours, exact, nocache, debug))
    sources.append(fetch_fudbal91(team, key, date, hours, exact, nocache, debug))
    sources.append(fetch_tsdb(team, key, date, hours, exact, nocache, debug))

    used = [s.get("source") for s in sources]
    # Flatten items with source tag
    tagged: List[Tuple[Dict, str]] = []
    for s in sources:
        for it in s.get("items", []) or []:
            tagged.append((it, s.get("source", "unknown")))

    # Group similar events
    groups: List[List[Tuple[Dict, str]]] = []
    for ev, src in tagged:
        placed = False
        for g in groups:
            if _similar_event(ev, g[0][0]):
                g.append((ev, src))
                placed = True
                break
        if not placed:
            groups.append([(ev, src)])

    results: List[Dict] = []
    total_sources = len([s for s in used if s])
    for g in groups:
        # choose a representative event (first) and compute confidence
        rep = g[0][0].copy()
        evidence = [src for (_, src) in g]
        conf = _confidence(len(set(evidence)), total_sources)
        rep["evidence"] = evidence
        rep["confidence"] = conf
        results.append(rep)

    # Sort by kickoff time asc
    def _kick_ts(e: Dict) -> float:
        d = _parse_iso(e.get("kickoff", ""))
        return d.timestamp() if d else float("inf")

    results.sort(key=_kick_ts)

    return {
        "used": used,
        "results": results,
        "sources": {s.get("source", f"s{i}"): {k: v for k, v in s.items() if k != "items"} | {"count": len(s.get("items", []) or [])} for i, s in enumerate(sources)},
        "counts": {s.get("source", f"s{i}"): len(s.get("items", []) or []) for i, s in enumerate(sources)},
    }
