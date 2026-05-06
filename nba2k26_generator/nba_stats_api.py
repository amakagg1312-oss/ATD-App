"""NBA Stats API wrapper with disk caching.

Fetches from stats.nba.com via nba_api and caches results for 6 hours
so repeated calls are instant and the app doesn't hammer the API.
"""
import json
import os
import sys
import time
from pathlib import Path

CACHE_TTL = 21600  # 6 hours

def _cache_dir():
    here = Path(__file__).parent
    d = here / "stats_cache"
    d.mkdir(exist_ok=True)
    return d

def _key(*parts):
    return "_".join(str(p).replace("/", "-").replace(" ", "_").lower() for p in parts if str(p))

def _read(key):
    path = _cache_dir() / f"{key}.json"
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > CACHE_TTL:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _write(key, data):
    path = _cache_dir() / f"{key}.json"
    path.write_text(json.dumps(data, default=str), encoding="utf-8")

def _df_to_records(df):
    """Convert DataFrame to JSON-safe list of dicts."""
    import math
    records = []
    for row in df.to_dict(orient="records"):
        clean = {}
        for k, v in row.items():
            if isinstance(v, float) and math.isnan(v):
                clean[k] = None
            else:
                clean[k] = v
        records.append(clean)
    return records


def fetch_player_stats(season="2024-25", season_type="Regular Season",
                       per_mode="PerGame", measure_type="Base"):
    key = _key("players_v3", season, season_type, per_mode, measure_type)
    cached = _read(key)
    if cached:
        cached["cached"] = True
        return cached

    from nba_api.stats.endpoints import LeagueDashPlayerStats
    ep = LeagueDashPlayerStats(
        season=season,
        season_type_all_star=season_type,
        per_mode_detailed=per_mode,
        measure_type_detailed_defense=measure_type,
        timeout=30,
    )
    df = ep.get_data_frames()[0]
    # Drop duplicate column names that the NBA API occasionally returns
    df = df.loc[:, ~df.columns.duplicated()]
    result = {"ok": True, "data": _df_to_records(df), "cached": False,
              "season": season, "season_type": season_type, "per_mode": per_mode, "measure_type": measure_type}
    _write(key, result)
    return result


def fetch_team_stats(season="2024-25", season_type="Regular Season",
                     per_mode="PerGame", measure_type="Base"):
    key = _key("teams", season, season_type, per_mode, measure_type)
    cached = _read(key)
    if cached:
        cached["cached"] = True
        return cached

    from nba_api.stats.endpoints import LeagueDashTeamStats
    ep = LeagueDashTeamStats(
        season=season,
        season_type_all_star=season_type,
        per_mode_detailed=per_mode,
        measure_type_detailed_defense=measure_type,
        timeout=30,
    )
    df = ep.get_data_frames()[0]
    result = {"ok": True, "data": _df_to_records(df), "cached": False,
              "season": season, "season_type": season_type}
    _write(key, result)
    return result


def fetch_league_leaders(season="2024-25", season_type="Regular Season",
                         stat_category="PTS", per_mode="PerGame"):
    key = _key("leaders", season, season_type, stat_category, per_mode)
    cached = _read(key)
    if cached:
        cached["cached"] = True
        return cached

    from nba_api.stats.endpoints import LeagueLeaders
    ep = LeagueLeaders(
        season=season,
        season_type_all_star=season_type,
        stat_category_abbreviation=stat_category,
        per_mode48=per_mode,
        timeout=30,
    )
    df = ep.get_data_frames()[0]
    result = {"ok": True, "data": _df_to_records(df), "cached": False,
              "category": stat_category}
    _write(key, result)
    return result


def fetch_tracking_stats(season="2024-25", season_type="Regular Season",
                         pt_measure_type="Drives", per_mode="PerGame"):
    key = _key("tracking_v3", season, season_type, pt_measure_type, per_mode)
    cached = _read(key)
    if cached:
        cached["cached"] = True
        return cached
    from nba_api.stats.endpoints import LeagueDashPtStats
    # player_or_team renamed from player_or_team_abbreviation in newer nba_api versions
    try:
        ep = LeagueDashPtStats(
            season=season,
            season_type_all_star=season_type,
            pt_measure_type=pt_measure_type,
            per_mode_simple=per_mode,
            player_or_team="Player",
            timeout=30,
        )
    except TypeError:
        ep = LeagueDashPtStats(
            season=season,
            season_type_all_star=season_type,
            pt_measure_type=pt_measure_type,
            per_mode_simple=per_mode,
            timeout=30,
        )
    df = ep.get_data_frames()[0]
    result = {"ok": True, "data": _df_to_records(df), "cached": False,
              "season": season, "pt_measure_type": pt_measure_type}
    _write(key, result)
    return result


def fetch_hustle_stats(season="2024-25", season_type="Regular Season", per_mode="PerGame"):
    key = _key("hustle", season, season_type, per_mode)
    cached = _read(key)
    if cached:
        cached["cached"] = True
        return cached
    from nba_api.stats.endpoints import LeagueHustleStatsPlayer
    ep = LeagueHustleStatsPlayer(
        season=season,
        season_type_all_star=season_type,
        per_mode_time=per_mode,
        timeout=30,
    )
    df = ep.get_data_frames()[0]
    result = {"ok": True, "data": _df_to_records(df), "cached": False, "season": season}
    _write(key, result)
    return result


def fetch_player_bio(player_id):
    key = _key("bio", str(player_id))
    cached = _read(key)
    if cached:
        cached["cached"] = True
        return cached
    from nba_api.stats.endpoints import CommonPlayerInfo
    ep = CommonPlayerInfo(player_id=int(player_id), timeout=30)
    dfs = ep.get_data_frames()
    info = _df_to_records(dfs[0])[0] if dfs and len(dfs[0]) > 0 else {}
    result = {"ok": True, "data": info, "cached": False}
    _write(key, result)
    return result


def fetch_shot_chart(player_id, season="2024-25", season_type="Regular Season"):
    key = _key("shots", str(player_id), season, season_type)
    cached = _read(key)
    if cached:
        cached["cached"] = True
        return cached
    from nba_api.stats.endpoints import ShotChartDetail
    ep = ShotChartDetail(
        player_id=int(player_id),
        team_id=0,
        season_nullable=season,
        season_type_all_star=season_type,
        context_measure_simple="FGA",
        timeout=30,
    )
    dfs = ep.get_data_frames()
    keep = {"LOC_X", "LOC_Y", "SHOT_MADE_FLAG", "SHOT_TYPE", "ACTION_TYPE",
            "SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "SHOT_DISTANCE", "PERIOD",
            "MINUTES_REMAINING", "SECONDS_REMAINING"}
    raw = _df_to_records(dfs[0]) if dfs else []
    shots = [{k: v for k, v in r.items() if k in keep} for r in raw]
    result = {"ok": True, "shots": shots, "cached": False,
              "season": season, "total": len(shots)}
    _write(key, result)
    return result


def fetch_player_career(player_id):
    key = _key("career", str(player_id))
    cached = _read(key)
    if cached:
        cached["cached"] = True
        return cached
    from nba_api.stats.endpoints import PlayerCareerStats
    ep = PlayerCareerStats(player_id=int(player_id), per_mode36="PerGame", timeout=30)
    dfs = ep.get_data_frames()
    regular = _df_to_records(dfs[0]) if dfs else []
    result = {"ok": True, "regular": regular, "cached": False}
    _write(key, result)
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint", choices=["players", "teams", "leaders"])
    parser.add_argument("--season", default="2024-25")
    parser.add_argument("--season-type", default="Regular Season")
    parser.add_argument("--per-mode", default="PerGame")
    parser.add_argument("--measure-type", default="Base")
    parser.add_argument("--category", default="PTS")
    args = parser.parse_args()

    try:
        if args.endpoint == "players":
            result = fetch_player_stats(args.season, args.season_type, args.per_mode, args.measure_type)
        elif args.endpoint == "teams":
            result = fetch_team_stats(args.season, args.season_type, args.per_mode, args.measure_type)
        else:
            result = fetch_league_leaders(args.season, args.season_type, args.category, args.per_mode)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
