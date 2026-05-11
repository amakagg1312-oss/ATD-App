"""
Contract Explorer — reads salary data from HoopsHype team pages.
HoopsHype is a Next.js app; salary data is embedded in __NEXT_DATA__ JSON,
so we parse that directly instead of scraping HTML tables.
24-hour disk cache.
"""
import json
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

CACHE_TTL = 86400  # 24 hours

# (slug, numeric_team_id) — IDs confirmed from hoopshype.com/salaries/teams/
TEAM_INFO = {
    "Atlanta Hawks":          ("atlanta-hawks",          1),
    "Boston Celtics":         ("boston-celtics",         2),
    "Brooklyn Nets":          ("brooklyn-nets",          17),
    "Charlotte Hornets":      ("charlotte-hornets",      5312),
    "Chicago Bulls":          ("chicago-bulls",          4),
    "Cleveland Cavaliers":    ("cleveland-cavaliers",    5),
    "Dallas Mavericks":       ("dallas-mavericks",       6),
    "Denver Nuggets":         ("denver-nuggets",         7),
    "Detroit Pistons":        ("detroit-pistons",        8),
    "Golden State Warriors":  ("golden-state-warriors",  9),
    "Houston Rockets":        ("houston-rockets",        10),
    "Indiana Pacers":         ("indiana-pacers",         11),
    "Los Angeles Clippers":   ("los-angeles-clippers",   12),
    "Los Angeles Lakers":     ("los-angeles-lakers",     13),
    "Memphis Grizzlies":      ("memphis-grizzlies",      29),
    "Miami Heat":             ("miami-heat",             14),
    "Milwaukee Bucks":        ("milwaukee-bucks",        15),
    "Minnesota Timberwolves": ("minnesota-timberwolves", 16),
    "New Orleans Pelicans":   ("new-orleans-pelicans",   3),
    "New York Knicks":        ("new-york-knicks",        18),
    "Oklahoma City Thunder":  ("oklahoma-city-thunder",  25),
    "Orlando Magic":          ("orlando-magic",          19),
    "Philadelphia 76ers":     ("philadelphia-76ers",     20),
    "Phoenix Suns":           ("phoenix-suns",           21),
    "Portland Trail Blazers": ("portland-trail-blazers", 22),
    "Sacramento Kings":       ("sacramento-kings",       23),
    "San Antonio Spurs":      ("san-antonio-spurs",      24),
    "Toronto Raptors":        ("toronto-raptors",        28),
    "Utah Jazz":              ("utah-jazz",              26),
    "Washington Wizards":     ("washington-wizards",     27),
}

# Show contract seasons from this year onwards (2024-25 = season int 2025)
_MIN_SEASON = 2025

_HDRS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "identity",
    "Referer": "https://hoopshype.com/salaries/",
}


def _cache_dir():
    here = Path(__file__).parent
    d = here / "contracts_cache"
    try:
        d.mkdir(exist_ok=True)
        t = d / ".wt"
        t.touch()
        t.unlink()
        return d
    except OSError:
        pass
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / "ATD 2K APP" / "contracts_cache"
    else:
        base = Path.home() / "Library" / "Application Support" / "ATD 2K APP" / "contracts_cache"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _name_to_slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9\s]", "", s.lower())
    return re.sub(r"\s+", "-", s.strip())


def _read_cache():
    p = _cache_dir() / "contracts_v7.json"
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_cache(data):
    p = _cache_dir() / "contracts_v7.json"
    p.write_text(json.dumps(data, default=str), encoding="utf-8")


def _season_to_year(season_int):
    """2025 → '2025-26', 2026 → '2026-27', etc. (season int = start year)"""
    return f"{season_int}-{str(season_int + 1)[2:]}"


def _extract_player_url_map(page_html):
    """Scan raw HTML for /salaries/players/{slug}/{id}/ links → {slug: id}."""
    return {
        m.group(1): m.group(2)
        for m in re.finditer(r'/salaries/players/([a-z0-9-]+)/(\d+)/', page_html)
    }


def _parse_next_data(page_html, team_name, debug=False):
    """Extract player contracts from embedded __NEXT_DATA__ JSON."""
    # Build slug→id map from HTML links before touching JSON
    url_map = _extract_player_url_map(page_html)
    if debug:
        print(f"[DEBUG] {team_name}: found {len(url_map)} player URLs in HTML", file=sys.stderr)

    nd = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', page_html, re.S)
    if not nd:
        if debug:
            print(f"[DEBUG] {team_name}: no __NEXT_DATA__ found", file=sys.stderr)
        return []

    try:
        data = json.loads(nd.group(1))
    except json.JSONDecodeError as e:
        if debug:
            print(f"[DEBUG] {team_name}: JSON parse error: {e}", file=sys.stderr)
        return []

    queries = (
        data.get("props", {})
            .get("pageProps", {})
            .get("dehydratedState", {})
            .get("queries", [])
    )

    raw_contracts = None
    for q in queries:
        q_data = q.get("state", {}).get("data", {})
        if isinstance(q_data, dict) and "contracts" in q_data:
            raw_contracts = q_data["contracts"].get("contracts", [])
            if debug:
                print(f"[DEBUG] {team_name}: found {len(raw_contracts)} contracts via query key={q.get('queryKey')}", file=sys.stderr)
            break

    if not raw_contracts:
        if debug:
            print(f"[DEBUG] {team_name}: no contracts query found. Query keys: {[q.get('queryKey') for q in queries]}", file=sys.stderr)
        return []

    if debug and raw_contracts:
        print(f"[DEBUG] {team_name}: sample contract keys: {list(raw_contracts[0].keys())}", file=sys.stderr)

    players = []
    for contract in raw_contracts:
        name = (contract.get("playerName") or "").strip()
        if not name:
            continue

        player_slug = (
            contract.get("playerSlug") or
            contract.get("slug") or
            _name_to_slug(name)
        )
        # Prefer ID from JSON fields, fall back to the HTML link map
        player_id = (
            contract.get("playerId") or
            contract.get("hhPlayerId") or
            contract.get("id") or
            contract.get("personId") or
            contract.get("nbaId") or
            url_map.get(player_slug)
        )

        salaries = {}
        options = {}

        for s in contract.get("seasons", []):
            season_int = s.get("season")
            salary = s.get("salary", 0)
            if not season_int or season_int < _MIN_SEASON:
                continue
            year = _season_to_year(season_int)
            if salary > 0:
                salaries[year] = salary
            if s.get("teamOption"):
                options[year] = "TO"
            elif s.get("playerOption"):
                options[year] = "PO"
            elif s.get("qualifyingOffer"):
                options[year] = "QO"
            elif s.get("twoWayContract"):
                options[year] = "TW"

        if name and salaries:
            players.append({
                "name": name,
                "team": team_name,
                "salaries": salaries,
                "options": options,
                "player_id": player_id,
                "player_slug": player_slug,
            })

    return players


def _fetch_team(team_name, slug, team_id, debug=False):
    url = f"https://hoopshype.com/salaries/teams/{slug}/{team_id}/"
    try:
        req = Request(url, headers=_HDRS)
        with urlopen(req, timeout=25) as r:
            raw = r.read()
        try:
            page_html = raw.decode("utf-8")
        except UnicodeDecodeError:
            page_html = raw.decode("latin-1")

        if debug:
            print(f"[DEBUG] {team_name}: fetched {len(page_html)} chars", file=sys.stderr)

        players = _parse_next_data(page_html, team_name, debug=debug)
        return team_name, players, None
    except Exception as e:
        return team_name, [], str(e)


def fetch_contracts(force=False, debug=False):
    if not force:
        cached = _read_cache()
        if cached:
            cached["cached"] = True
            return cached

    all_players = []
    errors = {}

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {
            ex.submit(_fetch_team, name, slug, tid, debug): name
            for name, (slug, tid) in TEAM_INFO.items()
        }
        for fut in as_completed(futs):
            team_name, players, err = fut.result()
            if err:
                errors[team_name] = err
            else:
                all_players.extend(players)

    result = {
        "ok": True,
        "players": all_players,
        "errors": errors,
        "fetched_at": int(time.time()),
        "team_count": 30 - len(errors),
    }
    if all_players:
        _write_cache(result)
    return result


def _parse_player_history(page_html, player_slug, debug=False):
    nd = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', page_html, re.S)
    if not nd:
        return {"ok": False, "error": "no __NEXT_DATA__ found"}
    try:
        data = json.loads(nd.group(1))
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"JSON: {e}"}

    queries = (
        data.get("props", {})
            .get("pageProps", {})
            .get("dehydratedState", {})
            .get("queries", [])
    )
    for q in queries:
        q_data = q.get("state", {}).get("data", {})
        if not isinstance(q_data, dict) or "contracts" not in q_data:
            continue
        contracts = q_data["contracts"].get("contracts", [])
        if not contracts:
            continue

        # Player name from first contract
        name = (contracts[0].get("playerName") or "").strip() or player_slug.replace("-", " ").title()

        # Collect seasons from ALL contracts (each past/current contract is a separate entry)
        seen = set()
        seasons = []
        for contract in contracts:
            for s in contract.get("seasons", []):
                season_int = s.get("season")
                if not season_int or season_int in seen:
                    continue
                seen.add(season_int)
                year = _season_to_year(season_int)
                salary = s.get("salary", 0)
                opt = None
                if s.get("teamOption"): opt = "TO"
                elif s.get("playerOption"): opt = "PO"
                elif s.get("qualifyingOffer"): opt = "QO"
                elif s.get("twoWayContract"): opt = "TW"
                seasons.append({"year": year, "salary": salary, "option": opt})

        seasons.sort(key=lambda x: x["year"])
        if debug:
            print(f"[DEBUG] {player_slug}: {len(contracts)} contracts, {len(seasons)} seasons total", file=sys.stderr)
        return {"ok": True, "name": name, "seasons": seasons}

    return {"ok": False, "error": "no contract data found"}


def fetch_player_history(player_slug, player_id="", debug=False):
    if not player_id:
        return {"ok": False, "error": "Player ID not available — hit Refresh on the Contracts page to re-fetch data with IDs."}
    url = f"https://hoopshype.com/salaries/players/{player_slug}/{player_id}/"
    try:
        req = Request(url, headers=_HDRS)
        with urlopen(req, timeout=25) as r:
            raw = r.read()
        page_html = raw.decode("utf-8", errors="replace")
        if debug:
            print(f"[DEBUG] player {player_slug}: fetched {len(page_html)} chars", file=sys.stderr)
        return _parse_player_history(page_html, player_slug, debug=debug)
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    force = "--force" in sys.argv
    debug = "--debug" in sys.argv
    r = fetch_contracts(force=force, debug=debug)
    if debug:
        print(f"[DEBUG] total players={len(r.get('players', []))}, errors={list(r.get('errors', {}).keys())}", file=sys.stderr)
    print(json.dumps(r, indent=2))
