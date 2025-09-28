import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
from typing import List, Dict, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,sr;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "DNT": "1",
    "Referer": "https://www.fudbal91.com/",
}

DEFAULT_TIMEOUT = 15
WINDOW_HOURS = 82

# Simple in-process cache to reduce repeated fetching and mitigate anti-bot
_CACHE: Dict[str, Dict] = {}
_CACHE_TTL_SECONDS = 120  # 2 minutes


def _get_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
    s.mount('https://', HTTPAdapter(max_retries=retries))
    s.mount('http://', HTTPAdapter(max_retries=retries))
    return s


def _parse_kickoff(text: str) -> Optional[datetime]:
    if not text:
        return None
    text = text.strip()
    # Try common formats: 2025-09-27 19:45, 27.09.2025 19:45, 27/09/2025 19:45, 2025-09-27T19:45Z
    patterns = [
        (r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})", "%Y-%m-%d %H:%M"),
        (r"(\d{2})[./](\d{2})[./](\d{4}).?(\d{2}:\d{2})?", None),
        (r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})Z", "%Y-%m-%d %H:%M"),
    ]
    for pat, fmt in patterns:
        m = re.search(pat, text)
        if m:
            try:
                if fmt:
                    dt = datetime.strptime(f"{m.group(1)} {m.group(2)}", fmt)
                    return dt.replace(tzinfo=timezone.utc)
                else:
                    # dd.mm.yyyy HH:MM
                    day, mon, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    hhmm = m.group(4) or "00:00"
                    dt = datetime.strptime(f"{year:04d}-{mon:02d}-{day:02d} {hhmm}", "%Y-%m-%d %H:%M")
                    return dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def _within_window(dt: Optional[datetime], hours: Optional[int] = WINDOW_HOURS) -> bool:
    if not dt:
        return False
    if hours is None:
        return True
    now = datetime.now(timezone.utc)
    return now <= dt <= now + timedelta(hours=hours)


def _fetch_html(url: str) -> Optional[str]:
    # Cache first
    now = datetime.now(timezone.utc)
    c = _CACHE.get(url)
    if c and (now - c["ts"]).total_seconds() < _CACHE_TTL_SECONDS:
        return c["html"]
    try:
        sess = _get_session()
        r = sess.get(url, headers=UA, timeout=DEFAULT_TIMEOUT)
        if r.status_code != 200:
            return None
        html = r.text
        # Save in cache
        _CACHE[url] = {"ts": now, "html": html}
        return html
    except Exception:
        return None


def fetch_quick_odds(hours: Optional[int] = WINDOW_HOURS, debug: bool = False) -> Dict:
    url = "https://www.fudbal91.com/quick_odds"
    html = _fetch_html(url)
    if not html:
        return {"source": url, "items": []}
    soup = BeautifulSoup(html, "lxml")
    items: List[Dict] = []
    if not soup:
        return {"source": url, "items": items}

    # Heuristic selectors
    rows = soup.select(
        "table tr, .match, .row, .match-row, .fixture-row, .event-row, .game, .fixture"
    )
    for row in rows:
        try:
            league = (row.select_one(".league") or row.select_one(".comp") or row.select_one(".competition")
                      or row.find(attrs={"data-league": True}))
            league_name = league.get_text(strip=True) if league else ""
            # Teams
            home = row.select_one('.home, .team-home, .home-team, .team1')
            away = row.select_one('.away, .team-away, .away-team, .team2')
            if home and away:
                teams_text = f"{home.get_text(strip=True)} - {away.get_text(strip=True)}"
            else:
                teams_text = " ".join(el.get_text(" ", strip=True) for el in row.select(".teams, .match-name, .teams-wrap"))
                if not teams_text:
                    # Fallback regex from full row text
                    txt = row.get_text(" ", strip=True)
                    m = re.search(r"([\w .'-]+)\s*[-–]\s*([\w .'-]+)", txt)
                    teams_text = f"{m.group(1)} - {m.group(2)}" if m else txt[:200]
            time_el = row.select_one("time, .kickoff, .ko, .date, .time")
            if time_el and time_el.has_attr('datetime'):
                ko_text = time_el.get('datetime', '')
            else:
                ko_text = (time_el.get_text(strip=True) if time_el else "")
                if not ko_text:
                    # Try data attributes on row
                    for attr in ['data-kickoff', 'data-time', 'data-date']:
                        if row.has_attr(attr):
                            ko_text = row.get(attr) or ''
                            break
            kickoff = _parse_kickoff(ko_text) or _parse_kickoff(row.get_text(" ", strip=True))

            # Odds
            odds = {}
            for lab in ["1", "X", "2", "1X", "12", "X2", "O2.5", "U2.5"]:
                el = row.find(attrs={"data-market": lab}) or row.find("td", string=re.compile(rf"\b{re.escape(lab)}\b"))
                if el:
                    # Value might be next sibling or in same cell
                    val = None
                    if el and el.next_sibling and hasattr(el.next_sibling, "get_text"):
                        val = el.next_sibling.get_text(strip=True)
                    if not val:
                        val = el.get_text(strip=True)
                    odds[lab] = val

            if _within_window(kickoff, hours=hours):
                items.append({
                    "league": league_name,
                    "match": teams_text,
                    "kickoff": kickoff.isoformat() if kickoff else None,
                    "odds": odds
                })
        except Exception:
            continue
    return {"source": url, "items": items}


def fetch_odds_changes(hours: Optional[int] = WINDOW_HOURS, debug: bool = False) -> Dict:
    url = "https://www.fudbal91.com/odds_changes"
    html = _fetch_html(url)
    if not html:
        return {"source": url, "items": []}
    soup = BeautifulSoup(html, "lxml")
    items: List[Dict] = []
    if not soup:
        return {"source": url, "items": items}

    blocks = soup.select(".change, .odds-change, table tr, .row, .event-row")
    for b in blocks:
        try:
            txt = b.get_text(" ", strip=True)
            kickoff = _parse_kickoff(txt)
            if not _within_window(kickoff, hours=hours):
                continue
            match = txt[:140]
            # Extract any number-like odds changes
            odds = {}
            for token in re.findall(r"\b\d+\.\d+\b", txt):
                odds.setdefault("values", []).append(token)
            items.append({
                "match": match,
                "kickoff": kickoff.isoformat() if kickoff else None,
                "changes": odds
            })
        except Exception:
            continue
    return {"source": url, "items": items}


COMPETITION_MAP = {
    "ucl": "https://www.fudbal91.com/competition/UEFA_Champions_League_-_League_phase/2025-2026",
    "laliga": "https://www.fudbal91.com/competition/Spain,_La_Liga_EA_Sports/2025-2026",
    "epl": "https://www.fudbal91.com/competition/England,_Premier_League/2025-2026",
    "bundesliga": "https://www.fudbal91.com/competition/Germany,_Bundesliga/2025-2026",
    "seriea": "https://www.fudbal91.com/competition/Italy,_Serie_A_Enilive/2025-2026",
    "ligue1": "https://www.fudbal91.com/competition/France,_Ligue_1_McDonald%E2%80%99s/2025-2026",
    "serbia": "https://www.fudbal91.com/competition/Serbia,_Mozzart_Bet_Superliga_-_1.deo/2025-2026",
}


def fetch_competition(url_or_key: str, hours: Optional[int] = WINDOW_HOURS, debug: bool = False) -> Dict:
    url = COMPETITION_MAP.get(url_or_key.lower(), url_or_key)
    html = _fetch_html(url)
    if not html:
        return {"source": url, "items": []}
    soup = BeautifulSoup(html, "lxml")
    items: List[Dict] = []
    if not soup:
        return {"source": url, "items": items}

    # Try to find match rows
    rows = soup.select(
        "table tr, .match, .fixture, .game, .match-row, .fixture-row, .event-row, .row"
    )
    for row in rows:
        try:
            league_el = soup.select_one("h1, .competition-title, .title, header h1, .page-title")
            league_name = league_el.get_text(strip=True) if league_el else ""
            # Teams extraction
            home = row.select_one('.home, .team-home, .home-team, .team1')
            away = row.select_one('.away, .team-away, .away-team, .team2')
            if home and away:
                teams = f"{home.get_text(strip=True)} - {away.get_text(strip=True)}"
            else:
                teams = " ".join(e.get_text(" ", strip=True) for e in row.select(".teams, .match-name, .teams-wrap"))
                if not teams:
                    txt = row.get_text(" ", strip=True)
                    m = re.search(r"([\w .'-]+)\s*[-–]\s*([\w .'-]+)", txt)
                    teams = f"{m.group(1)} - {m.group(2)}" if m else txt[:200]
            time_el = row.select_one("time, .kickoff, .ko, .date, .time")
            if time_el and time_el.has_attr('datetime'):
                ko_text = time_el.get('datetime', '')
            else:
                ko_text = (time_el.get_text(strip=True) if time_el else "")
                if not ko_text:
                    for attr in ['data-kickoff', 'data-time', 'data-date']:
                        if row.has_attr(attr):
                            ko_text = row.get(attr) or ''
                            break
            kickoff = _parse_kickoff(ko_text) or _parse_kickoff(row.get_text(" ", strip=True))

            odds = {}
            odds_cells = row.select("td")
            if odds_cells and len(odds_cells) <= 10:
                # naive grab float-like numbers
                floats = re.findall(r"\d+\.\d+", " ".join(c.get_text(" ", strip=True) for c in odds_cells))
                if floats:
                    odds["list"] = floats[:10]

            if _within_window(kickoff, hours=hours):
                items.append({
                    "league": league_name,
                    "match": teams,
                    "kickoff": kickoff.isoformat() if kickoff else None,
                    "odds": odds
                })
        except Exception:
            continue

    return {"source": url, "items": items}
