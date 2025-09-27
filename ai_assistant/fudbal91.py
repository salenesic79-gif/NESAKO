import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
from typing import List, Dict, Optional

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}

DEFAULT_TIMEOUT = 12
WINDOW_HOURS = 82


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


def _within_window(dt: Optional[datetime], hours: int = WINDOW_HOURS) -> bool:
    if not dt:
        return False
    now = datetime.now(timezone.utc)
    return now <= dt <= now + timedelta(hours=hours)


def _get_soup(url: str) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=UA, timeout=DEFAULT_TIMEOUT)
        if r.status_code != 200:
            return None
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None


def fetch_quick_odds() -> Dict:
    url = "https://www.fudbal91.com/quick_odds"
    soup = _get_soup(url)
    items: List[Dict] = []
    if not soup:
        return {"source": url, "items": items}

    # Heuristic selectors
    rows = soup.select("table tr, .match, .row")
    for row in rows:
        try:
            league = (row.select_one(".league") or row.select_one(".comp") or row.select_one(".competition"))
            league_name = league.get_text(strip=True) if league else ""
            teams_text = " ".join(el.get_text(" ", strip=True) for el in row.select(".teams, .home, .away, .match-name"))
            if not teams_text:
                teams_text = row.get_text(" ", strip=True)[:200]
            time_el = row.select_one("time, .kickoff, .ko, .date, .time")
            ko_text = time_el.get("datetime", "") if time_el and time_el.has_attr("datetime") else (time_el.get_text(strip=True) if time_el else "")
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

            if _within_window(kickoff):
                items.append({
                    "league": league_name,
                    "match": teams_text,
                    "kickoff": kickoff.isoformat() if kickoff else None,
                    "odds": odds
                })
        except Exception:
            continue
    return {"source": url, "items": items}


def fetch_odds_changes() -> Dict:
    url = "https://www.fudbal91.com/odds_changes"
    soup = _get_soup(url)
    items: List[Dict] = []
    if not soup:
        return {"source": url, "items": items}

    blocks = soup.select(".change, .odds-change, table tr")
    for b in blocks:
        try:
            txt = b.get_text(" ", strip=True)
            kickoff = _parse_kickoff(txt)
            if not _within_window(kickoff):
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


def fetch_competition(url_or_key: str) -> Dict:
    url = COMPETITION_MAP.get(url_or_key.lower(), url_or_key)
    soup = _get_soup(url)
    items: List[Dict] = []
    if not soup:
        return {"source": url, "items": items}

    # Try to find match rows
    rows = soup.select("table tr, .match, .fixture, .game")
    for row in rows:
        try:
            league_el = soup.select_one("h1, .competition-title, .title")
            league_name = league_el.get_text(strip=True) if league_el else ""
            teams = " ".join(e.get_text(" ", strip=True) for e in row.select(".teams, .home, .away, .match-name"))
            if not teams:
                teams = row.get_text(" ", strip=True)[:200]
            time_el = row.select_one("time, .kickoff, .ko, .date, .time")
            ko_text = time_el.get("datetime", "") if time_el and time_el.has_attr("datetime") else (time_el.get_text(strip=True) if time_el else "")
            kickoff = _parse_kickoff(ko_text) or _parse_kickoff(row.get_text(" ", strip=True))

            odds = {}
            odds_cells = row.select("td")
            if odds_cells and len(odds_cells) <= 10:
                # naive grab float-like numbers
                floats = re.findall(r"\d+\.\d+", " ".join(c.get_text(" ", strip=True) for c in odds_cells))
                if floats:
                    odds["list"] = floats[:10]

            if _within_window(kickoff):
                items.append({
                    "league": league_name,
                    "match": teams,
                    "kickoff": kickoff.isoformat() if kickoff else None,
                    "odds": odds
                })
        except Exception:
            continue

    return {"source": url, "items": items}
