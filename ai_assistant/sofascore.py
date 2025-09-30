import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

# Lightweight SofaScore integration (public JSON). Odds are generally not exposed publicly.
# We provide fixtures and basic event info within a time window.

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9,sr;q=0.8",
}

BASE = "https://api.sofascore.com/api/v1"
WINDOW_HOURS = 82
_CACHE: Dict[str, Dict] = {}
_CACHE_TTL_SECONDS = 120

COMP_KEYS = {
    # Map user-friendly keys to SofaScore tournament IDs (examples; may need adjustments)
    # These IDs can change per season; we fetch by date instead and filter by tournament name strings below.
    "ucl": ["Champions League"],
    "epl": ["Premier League"],
    "laliga": ["LaLiga", "La Liga"],
    "bundesliga": ["Bundesliga"],
    "seriea": ["Serie A"],
    "ligue1": ["Ligue 1"],
    "serbia": ["Super Liga"],
}


def _cache_get(key: str) -> Optional[Dict]:
    item = _CACHE.get(key)
    if not item:
        return None
    if (datetime.now(timezone.utc) - item["ts"]).total_seconds() > _CACHE_TTL_SECONDS:
        return None
    return item["data"]


def _cache_set(key: str, data: Dict):
    _CACHE[key] = {"ts": datetime.now(timezone.utc), "data": data}


def _get(url: str) -> Optional[Dict]:
    try:
        r = requests.get(url, headers=UA, timeout=12)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _dates_for_window(hours: Optional[int]) -> List[str]:
    now = datetime.now(timezone.utc)
    # If hours is None (all=1), take a wider safe window of next 7 days
    if hours is None:
        end = now + timedelta(days=7)
    else:
        end = now + timedelta(hours=hours)
    days = []
    d = now.date()
    while datetime(d.year, d.month, d.day, tzinfo=timezone.utc) <= end:
        days.append(d.strftime("%Y-%m-%d"))
        d = d + timedelta(days=1)
    return days


def _within_window(ts: int, hours: Optional[int]) -> bool:
    if hours is None:
        return True
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    return now <= dt <= now + timedelta(hours=hours)


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _match_comp(competitions: List[str], names: List[str], exact: bool) -> bool:
    if not competitions:
        return True
    n1 = _norm(names[0] if len(names) > 0 else "")
    n2 = _norm(names[1] if len(names) > 1 else "")
    if exact:
        for c in competitions:
            cc = _norm(c)
            if cc == n1 or cc == n2:
                return True
        return False
    else:
        nm = f"{n1} {n2}".strip()
        for c in competitions:
            if _norm(c) in nm:
                return True
        return False


def fetch_quick(
    hours: Optional[int] = WINDOW_HOURS,
    keys: Optional[List[str]] = None,
    debug: bool = False,
    *,
    team: Optional[str] = None,
    date: Optional[str] = None,  # YYYY-MM-DD
    nocache: bool = False,
    exact: bool = False,
) -> Dict:
    """Fetch scheduled football events in the next window (or a specific date) and filter by competition/team.

    - keys: list of competition name strings from COMP_KEYS; matched loosely or exactly
    - team: filter events where home or away contains this substring
    - date: fetch only a specific YYYY-MM-DD (ignores hours window)
    - nocache: bypass short in-memory cache
    - exact: when True, competition must exactly equal tournament/category name
    """
    cache_key = f"sofa:quick:{hours}:{date}:{team}:{exact}:{','.join(keys or [])}"
    if not nocache:
        cached = _cache_get(cache_key)
        if cached:
            return cached

    items: List[Dict] = []
    comp_names = []
    if keys:
        for k in keys:
            comp_names.extend(COMP_KEYS.get(k, []))

    days = [date] if date else _dates_for_window(hours)
    debug_notes = []
    day_counts = {}

    for day in days:
        url = f"{BASE}/sport/football/scheduled-events/{day}"
        data = _get(url)
        if not data or "events" not in data:
            debug_notes.append(f"no_data:{day}")
            continue
        day_counts[day] = len(data.get("events", []))
        for ev in data["events"]:
            try:
                t = ev.get("tournament", {})
                tn = t.get("name", "")
                cc = t.get("category", {}).get("name", "")
                names = [tn, cc]
                if keys and not _match_comp(comp_names, names, exact):
                    continue
                start_ts = ev.get("startTimestamp")
                if not start_ts or not _within_window(start_ts, hours):
                    continue
                home = ev.get("homeTeam", {}).get("name", "")
                away = ev.get("awayTeam", {}).get("name", "")
                if team:
                    tt = _norm(team)
                    if tt not in _norm(home) and tt not in _norm(away):
                        continue
                api_url = url
                event_id = ev.get("id")
                items.append({
                    "league": f"{cc} - {tn}".strip(" -"),
                    "match": f"{home} - {away}",
                    "kickoff": datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(),
                    "odds": {},  # SofaScore public JSON usually lacks odds
                    "source": "sofascore",
                    "api_url": api_url,
                    "tournament": tn,
                    "category": cc,
                    "eventId": event_id,
                    "startTimestamp": start_ts,
                })
            except Exception:
                continue

    resp = {"source": "sofascore", "items": items}
    if debug:
        resp["debug"] = {
            "days": days,
            "notes": debug_notes,
            "per_day_raw_counts": day_counts,
            "filtered_competitions": comp_names or None,
            "count": len(items)
        }
    if not nocache:
        _cache_set(cache_key, resp)
    return resp


def fetch_competition(
    key: str,
    hours: Optional[int] = WINDOW_HOURS,
    debug: bool = False,
    *,
    team: Optional[str] = None,
    date: Optional[str] = None,
    nocache: bool = False,
    exact: bool = False,
) -> Dict:
    """Fetch a single competition by key within the window/date with optional strict match/team filter."""
    keys = [key] if key else None
    return fetch_quick(hours=hours, keys=keys, debug=debug, team=team, date=date, nocache=nocache, exact=exact)
