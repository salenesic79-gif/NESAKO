import os
import requests
from typing import Dict, List, Optional

API_KEY = os.getenv("THE_SPORTS_DB_KEY", "1")  # demo key by default
BASE = "https://www.thesportsdb.com/api/v1/json"
UA = {
    "User-Agent": "NESAKO-AI/1.0 (+local)",
    "Accept": "application/json,text/plain,*/*",
}


def _get(path: str, params: Optional[Dict] = None) -> Optional[Dict]:
    try:
        url = f"{BASE}/{API_KEY}/{path}"
        r = requests.get(url, headers=UA, params=params or {}, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def search_team(name: str) -> Optional[str]:
    if not name:
        return None
    data = _get("searchteams.php", {"t": name}) or {}
    teams = data.get("teams") or []
    if not teams:
        return None
    name_lc = name.strip().lower()
    for t in teams:
        if str(t.get("strTeam", "")).strip().lower() == name_lc:
            return t.get("idTeam")
    return teams[0].get("idTeam")


def events_next_team(team_id: str, n: int = 10) -> List[Dict]:
    data = _get("eventsnext.php", {"id": team_id}) or {}
    events = data.get("events") or []
    return events[: max(1, min(n, len(events)))]


def events_last_team(team_id: str, n: int = 5) -> List[Dict]:
    data = _get("eventslast.php", {"id": team_id}) or {}
    events = data.get("results") or []
    return events[: max(1, min(n, len(events)))]


def search_league(name: str) -> Optional[str]:
    if not name:
        return None
    data = _get("search_all_leagues.php", {"s": "Soccer"}) or {}
    leagues = data.get("countrys") or []
    if not leagues:
        return None
    name_lc = name.strip().lower()
    for lg in leagues:
        if str(lg.get("strLeague", "")).strip().lower() == name_lc:
            return lg.get("idLeague")
    for lg in leagues:
        if name_lc in str(lg.get("strLeague", "")).strip().lower():
            return lg.get("idLeague")
    return None


def events_next_league(league_id: str, n: int = 15) -> List[Dict]:
    data = _get("eventsnextleague.php", {"id": league_id}) or {}
    events = data.get("events") or []
    return events[: max(1, min(n, len(events)))]
