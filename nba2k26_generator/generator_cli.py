import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from nba2k26_generator.nba_site_normalization import load_nba_site_rows
except Exception:
    try:
        from nba_site_normalization import load_nba_site_rows  # type: ignore
    except Exception:
        load_nba_site_rows = None  # type: ignore

# ML attribute computation (sklearn models + committee 11+ correction + role boosts)
_compute_attributes_ml = None
try:
    from nba2k26_generator.generator_cli_ml import compute_attributes_ml as _ml_fn
    _compute_attributes_ml = _ml_fn
except Exception:
    try:
        from generator_cli_ml import compute_attributes_ml as _ml_fn
        _compute_attributes_ml = _ml_fn
    except Exception:
        _compute_attributes_ml = None

# Committee attribute floors cache
_COMMITTEE_FLOORS_CACHE: Optional[Dict[str, Dict[str, int]]] = None


def _load_committee_floors() -> Dict[str, Dict[str, int]]:
    """Load NBA 2K27 ATD Committee attributes from the Excel file.

    Returns dict mapping player_name -> {attribute_name: value}
    """
    global _COMMITTEE_FLOORS_CACHE
    if _COMMITTEE_FLOORS_CACHE is not None:
        return _COMMITTEE_FLOORS_CACHE

    _COMMITTEE_FLOORS_CACHE = {}

    try:
        import pandas as pd

        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "Player Roles", "attributes two.xlsx"),
            os.path.join(os.getcwd(), "Player Roles", "attributes two.xlsx"),
        ]

        excel_path = None
        for c in candidates:
            if os.path.exists(c):
                excel_path = c
                break

        if excel_path is None:
            return _COMMITTEE_FLOORS_CACHE

        df = pd.read_excel(excel_path, header=None)
        attr_names = df.iloc[4].tolist()

        name_map = {
            "Driving Layup": "Driving Layup",
            "Standing Dunk": "Standing Dunk",
            "Driving Dunk": "Driving Dunk",
            "Close Shot": "Close Shot",
            "Mid-Range Shot": "Mid-Range Shot",
            "Three-Point Shot": "Three-Point Shot",
            "Free Thow": "Free Throw",
            "Free Throw": "Free Throw",
            "Post Hook": "Post Hook",
            "Post Fade": "Post Fade",
            "Post Control": "Post Control",
            "Draw Foul": "Draw Foul",
            "Shot IQ": "Shot IQ",
            "Ball Handle": "Ball Handle",
            "Speed with Ball": "Speed with Ball",
            "Hands": "Hands",
            "Pass Accuracy": "Pass Accuracy",
            "Pass IQ": "Pass IQ",
            "Pass Vision": "Pass Vision",
            "Offensive Consistency": "Offensive Consistency",
            "Interior Defense": "Interior Defense",
            "Perimeter Defense": "Perimeter Defense",
            "Steal": "Steal",
            "Block": "Block",
            "Offensive Rebound": "Offensive Rebound",
            "Defensive Rebound": "Defensive Rebound",
            "Help Defense IQ": "Help Defense IQ",
            "Pass Perception": "Pass Perception",
            "Defensive Consistency": "Defensive Consistency",
            "Speed": "Speed",
            "Agility": "Agility",
            "Strength": "Strength",
            "Vertical": "Vertical",
            "Stamina\n(Second To last)": "Stamina",
            "Stamina": "Stamina",
            "Intangibles\n(Last)": "Intangibles",
            "Intangibles": "Intangibles",
            "Hustle": "Hustle",
        }

        for idx in range(5, len(df)):
            row_data = df.iloc[idx]
            player_name = str(row_data.iloc[1]).strip()
            if not player_name or player_name == "nan":
                continue

            attrs = {}
            for col_idx in range(2, min(len(row_data), len(attr_names))):
                attr_name_raw = attr_names[col_idx]
                if pd.isna(attr_name_raw):
                    continue
                attr_name_raw = str(attr_name_raw).strip()
                mapped_name = name_map.get(attr_name_raw, attr_name_raw)

                val = row_data.iloc[col_idx]
                if pd.notna(val):
                    try:
                        attrs[mapped_name] = int(float(val))
                    except (ValueError, TypeError):
                        pass

            if attrs:
                normalized_name = unicodedata.normalize("NFKD", player_name.lower()).encode("ascii", "ignore").decode("ascii")
                _COMMITTEE_FLOORS_CACHE[normalized_name] = attrs

    except Exception:
        pass

    return _COMMITTEE_FLOORS_CACHE


def _apply_committee_correction(
    attributes: Dict[str, int],
    player_name: str,
    season: str = "",
) -> Dict[str, int]:
    """Apply committee correction when rule-based attributes are off by 10+ points.

    Only for 2025-26 season. If the committee value is 10+ points higher
    than the computed value, use the committee value. Otherwise keep computed.
    Shot IQ always uses the sheet value regardless of difference.
    """
    season_str = str(season).strip().lower()
    if "2025-26" not in season_str and "2025_26" not in season_str:
        return attributes

    floors = _load_committee_floors()
    normalized_name = unicodedata.normalize("NFKD", player_name.lower()).encode("ascii", "ignore").decode("ascii")
    player_floors = floors.get(normalized_name)
    if not player_floors:
        return attributes

    result = dict(attributes)
    for attr_name, committee_val in player_floors.items():
        current = attributes.get(attr_name)
        if current is None:
            norm_key = re.sub(r"[^a-z0-9]+", "_", attr_name.strip().lower()).strip("_")
            current = attributes.get(norm_key)

        if current is not None:
            if attr_name == "Shot IQ":
                result[attr_name] = committee_val
                norm_key = re.sub(r"[^a-z0-9]+", "_", attr_name.strip().lower()).strip("_")
                result[norm_key] = committee_val
            elif committee_val - current >= 10:
                result[attr_name] = committee_val
                norm_key = re.sub(r"[^a-z0-9]+", "_", attr_name.strip().lower()).strip("_")
                result[norm_key] = committee_val

    return result

try:
    from nba2k26_generator.badges import (
        compute_badge_groups,
        compute_badges,
        compute_badge_count_from_stats,
        load_badge_catalog,
        BADGE_TIER_ORDER,
        BADGE_TIER_THRESHOLDS,
        BADGE_MAX_TOTAL,
        BADGE_MAX_LEGEND,
        BADGE_MAX_HOF,
    )
except Exception:
    try:
        from badges import (  # type: ignore
            compute_badge_groups,
            compute_badges,
            compute_badge_count_from_stats,
            load_badge_catalog,
            BADGE_TIER_ORDER,
            BADGE_TIER_THRESHOLDS,
            BADGE_MAX_TOTAL,
            BADGE_MAX_LEGEND,
            BADGE_MAX_HOF,
        )
    except Exception:
        compute_badge_groups = None  # type: ignore
        compute_badges = None  # type: ignore
        compute_badge_count_from_stats = None  # type: ignore
        load_badge_catalog = None  # type: ignore
        BADGE_TIER_ORDER = ["Bronze", "Silver", "Gold", "HOF", "Legend"]
        BADGE_TIER_THRESHOLDS = {
            "Bronze": 45.0,
            "Silver": 57.0,
            "Gold": 68.0,
            "HOF": 80.0,
            "Legend": 91.0,
        }
        BADGE_MAX_TOTAL = 20
        BADGE_MAX_LEGEND = 1
        BADGE_MAX_HOF = 3


MISSING_VALUES = {"", "NA", "N/A", "NONE", "NULL"}
_WORKBOOK_CAP_CACHE: Dict[str, Dict[str, Tuple[int, int]]] = {}
_TEAM_ROSTER_CACHE: Dict[Tuple[str, str], Optional[set[str]]] = {}
_TEAM_ROSTER_SIGNATURE_CACHE: Dict[
    Tuple[str, str], Optional[Tuple[set[str], set[str]]]
] = {}
_ESPN_TEAM_ID_CACHE: Optional[Dict[str, str]] = None
ACTIVE_ROSTER_MIN_GAMES_BY_YEAR: Dict[int, int] = {2025: 10}
ESPN_TEAM_ABBR_ALIASES: Dict[str, str] = {
    "GSW": "GS",
    "NOP": "NO",
    "NYK": "NY",
    "SAS": "SA",
    "UTA": "UTAH",
    "WAS": "WSH",
}

# Performance caches for team generation — avoid redundant O(n) passes through all_rows.
_SEASON_CACHE: Dict[str, Dict[str, Any]] = {}
_PLAYER_CONTEXT_CACHE: Dict[str, Dict[str, Any]] = {}


def _build_season_context(
    all_rows: List[Dict[str, Any]], season_label: str
) -> Dict[str, Any]:
    """Build and cache season-level data once per season. O(n) pass through all_rows."""
    cache_key = season_label.lower().strip()
    if cache_key in _SEASON_CACHE:
        return _SEASON_CACHE[cache_key]

    same_season = [
        r
        for r in all_rows
        if str(r.get("season_label", "")).strip().lower() == cache_key
    ]

    def season_games_played(r: Dict[str, Any]) -> float:
        return max(
            0.0,
            as_float(r, "totals_g", as_float(r, "advanced_g", as_float(r, "per_game_g"))),
        )

    season_max_games = max(
        (season_games_played(r) for r in same_season), default=82.0
    )
    season_max_games = max(season_max_games, 1.0)

    def position_bucket(pos_text: str) -> str:
        p = (pos_text or "").upper()
        if ("C" in p) and ("PF" not in p):
            return "C"
        if ("PF" in p) or ("SF" in p):
            return "F"
        return "G"

    same_bucket: Dict[str, List[Dict[str, Any]]] = {}
    for r in same_season:
        b = position_bucket(str(r.get("position", "")))
        same_bucket.setdefault(b, []).append(r)

    season_player_ids: Dict[str, List[Dict[str, Any]]] = {}
    for r in same_season:
        pid = str(r.get("player_id", "")).strip()
        if pid:
            season_player_ids.setdefault(pid, []).append(r)

    career_player_ids: Dict[str, List[Dict[str, Any]]] = {}
    for r in all_rows:
        pid = str(r.get("player_id", "")).strip()
        if pid:
            career_player_ids.setdefault(pid, []).append(r)

    heavy_minute_pool = [
        r
        for r in same_season
        if as_float(r, "per_game_mp_per_game") >= 30.0
        and as_float(r, "totals_mp") >= 1800.0
    ]
    heavy_mpg_threshold = 30.0 if len(heavy_minute_pool) >= 55 else 28.0

    result = {
        "same_season": same_season,
        "same_bucket": same_bucket,
        "season_max_games": season_max_games,
        "season_player_ids": season_player_ids,
        "career_player_ids": career_player_ids,
        "heavy_minute_pool": heavy_minute_pool,
        "heavy_mpg_threshold": heavy_mpg_threshold,
        "season_games_played": season_games_played,
        "position_bucket": position_bucket,
    }
    _SEASON_CACHE[cache_key] = result
    return result


def _build_player_context(
    row: Dict[str, Any], all_rows: List[Dict[str, Any]], season_ctx: Dict[str, Any]
) -> Dict[str, Any]:
    """Build and cache per-player data. O(1) lookups from pre-computed season context."""
    player_id = str(row.get("player_id", "")).strip()
    season_label = str(row.get("season_label", "")).strip()
    cache_key = f"{player_id}:{season_label}"
    if cache_key in _PLAYER_CONTEXT_CACHE:
        return _PLAYER_CONTEXT_CACHE[cache_key]

    season_games_played = season_ctx["season_games_played"]
    season_player_ids = season_ctx["season_player_ids"]
    career_player_ids = season_ctx["career_player_ids"]
    same_season = season_ctx["same_season"]
    same_bucket = season_ctx["same_bucket"]
    season_max_games = season_ctx["season_max_games"]
    position_bucket_fn = season_ctx["position_bucket"]

    player_rows = season_player_ids.get(player_id, [])
    if player_id:
        player_rows = [
            r for r in player_rows
            if str(r.get("season_label", "")).strip().lower() == season_label.lower().strip()
        ]

    durability_availability_score = 70.0
    if player_id:
        played = min(
            sum(season_games_played(r) for r in player_rows), season_max_games
        )
        missed_pct = clamp((season_max_games - played) / season_max_games, 0.0, 1.0)
        durability_availability_score = 100.0 * (1.0 - missed_pct)

    ironman_seasons = 0
    if player_id:
        player_seasons = set(
            str(r.get("season_label", "")).strip()
            for r in career_player_ids.get(player_id, [])
            if str(r.get("season_label", "")).strip()
        )
        for sl in player_seasons:
            sl_player = [
                r
                for r in career_player_ids.get(player_id, [])
                if str(r.get("season_label", "")).strip() == sl
            ]
            if sl_player:
                sl_gp = min(sum(season_games_played(r) for r in sl_player), season_max_games)
                if sl_gp / season_max_games >= 70.0 / 82.0:
                    ironman_seasons += 1

    def defense_season_score(r: Dict[str, Any]) -> float:
        stl_s = remap(as_float(r, "advanced_stl_percent"), 0.8, 3.4, 0.0, 100.0)
        blk_s = remap(as_float(r, "advanced_blk_percent"), 0.2, 4.5, 0.0, 100.0)
        dws_s = remap(as_float(r, "advanced_dws"), 0.08, 0.20, 0.0, 100.0)
        mp_s = remap(as_float(r, "totals_mp"), 700.0, 3100.0, 0.0, 100.0)
        return clamp(0.38 * stl_s + 0.20 * blk_s + 0.30 * dws_s + 0.12 * mp_s, 0.0, 100.0)

    defense_peak_signal = defense_season_score(row)
    if player_rows:
        defense_peak_signal = max(defense_season_score(pr) for pr in player_rows)
    if player_id:
        _career_rows = career_player_ids.get(player_id, [])
        if _career_rows:
            defense_peak_signal = max(
                defense_peak_signal,
                max(defense_season_score(pr) for pr in _career_rows),
            )

    position = str(row.get("position", ""))
    bucket = position_bucket_fn(position)
    bucket_rows = same_bucket.get(bucket, same_season)

    dunks = as_float(row, "shooting_num_of_dunks")
    dunks_share = as_float(row, "shooting_percent_dunks_of_fga")

    def _build_percentile_lookup(rows: List[Dict[str, Any]], key: str) -> Dict[float, float]:
        vals = [as_float(r, key) for r in rows]
        vals = [v for v in vals if not math.isnan(v) and not math.isinf(v)]
        if not vals:
            return {}
        sorted_vals = sorted(vals)
        n = float(len(sorted_vals))
        lookup: Dict[float, float] = {}
        for i, v in enumerate(sorted_vals):
            if v not in lookup:
                below = i
                j = i
                while j < len(sorted_vals) and sorted_vals[j] == v:
                    j += 1
                equal = j - i
                lookup[v] = ((below + (0.5 * equal)) / n) * 100.0
        return lookup

    def _lookup_percentile(lookup: Dict[float, float], val: float, default: float = 50.0) -> float:
        if val in lookup:
            return lookup[val]
        best_diff = float("inf")
        best_pct = default
        for k, v in lookup.items():
            d = abs(k - val)
            if d < best_diff:
                best_diff = d
                best_pct = v
        return best_pct

    dunk_values = [as_float(r, "shooting_num_of_dunks") for r in bucket_rows]
    dunk_share_values = [as_float(r, "shooting_percent_dunks_of_fga") for r in bucket_rows]
    dunk_count_pct = _lookup_percentile(_build_percentile_lookup(bucket_rows, "shooting_num_of_dunks"), dunks)
    dunk_share_pct = _lookup_percentile(_build_percentile_lookup(bucket_rows, "shooting_percent_dunks_of_fga"), dunks_share)
    dunk_positional_score = (0.65 * dunk_count_pct) + (0.35 * dunk_share_pct)

    percentile_lookups_bucket: Dict[str, Dict[float, float]] = {}
    percentile_lookups_global: Dict[str, Dict[float, float]] = {}

    result = {
        "player_rows": player_rows,
        "durability_availability_score": durability_availability_score,
        "ironman_seasons": ironman_seasons,
        "defense_peak_signal": defense_peak_signal,
        "dunk_positional_score": dunk_positional_score,
        "percentile_lookups_bucket": percentile_lookups_bucket,
        "percentile_lookups_global": percentile_lookups_global,
        "bucket_rows": bucket_rows,
        "same_season": same_season,
        "season_max_games": season_max_games,
    }
    _PLAYER_CONTEXT_CACHE[cache_key] = result
    return result


def clear_team_generation_caches() -> None:
    """Clear caches before a new team generation run to avoid stale data."""
    _SEASON_CACHE.clear()
    _PLAYER_CONTEXT_CACHE.clear()


def configure_output_streams() -> None:
    # Prevent Windows cp1252 encoding crashes on names with non-ASCII bytes.
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                # Best-effort hardening; do not fail generation if stream cannot be changed.
                pass


def repair_mojibake_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""

    def _likely_mojibake(s: str) -> bool:
        hints = (
            "\u00c3",
            "\u00c2",
            "\u00e2",
            "\u00c4",
            "\u00c5",
            "\u00d0",
            "\u00f0",
            "\u2021",
        )
        if any(h in s for h in hints):
            return True
        return any(0x80 <= ord(ch) <= 0x9F for ch in s)

    def _to_byte_stream(s: str) -> Optional[bytes]:
        out = bytearray()
        for ch in s:
            code = ord(ch)
            if code <= 0xFF:
                out.append(code)
                continue
            try:
                raw = ch.encode("cp1252")
            except Exception:
                return None
            if len(raw) != 1:
                return None
            out.extend(raw)
        return bytes(out)

    fixed = text
    for _ in range(2):
        if not _likely_mojibake(fixed):
            break
        raw = _to_byte_stream(fixed)
        if not raw:
            break
        try:
            decoded = raw.decode("utf-8")
        except Exception:
            break
        if not decoded or decoded == fixed:
            break
        fixed = decoded

    if fixed:
        return fixed

    return text


def normalize_player_name_for_match(value: Any) -> str:
    text = repair_mojibake_text(value)
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


@dataclass
class TendencyRule:
    name: str
    norm_range: Tuple[int, int]
    recommended_cap: int
    absolute_cap: int


@dataclass
class TendencyResult:
    name: str
    pre_cap: float
    final: int
    recommended_cap: int
    absolute_cap: int
    norm_range: Tuple[int, int]
    evidence: Dict[str, Any]


@dataclass(frozen=True)
class EraProfile:
    key: str
    label: str
    three_point_cap_delta: int
    mid_post_cap_delta: int
    iso_cap_delta: int
    dribble_cap_delta: int
    flashy_cap_delta: int
    defense_cap_delta: int


ERA_PROFILES: Dict[str, EraProfile] = {
    "2000_2008": EraProfile(
        key="2000_2008",
        label="2000-2008",
        three_point_cap_delta=-12,
        mid_post_cap_delta=6,
        iso_cap_delta=4,
        dribble_cap_delta=-6,
        flashy_cap_delta=-6,
        defense_cap_delta=2,
    ),
    "2009_2014": EraProfile(
        key="2009_2014",
        label="2009-2014",
        three_point_cap_delta=-7,
        mid_post_cap_delta=4,
        iso_cap_delta=2,
        dribble_cap_delta=-3,
        flashy_cap_delta=-3,
        defense_cap_delta=1,
    ),
    "2015_2019": EraProfile(
        key="2015_2019",
        label="2015-2019",
        three_point_cap_delta=-3,
        mid_post_cap_delta=2,
        iso_cap_delta=1,
        dribble_cap_delta=-1,
        flashy_cap_delta=-1,
        defense_cap_delta=0,
    ),
    "2020_2025": EraProfile(
        key="2020_2025",
        label="2020-2025",
        three_point_cap_delta=0,
        mid_post_cap_delta=0,
        iso_cap_delta=0,
        dribble_cap_delta=0,
        flashy_cap_delta=0,
        defense_cap_delta=0,
    ),
}


THREE_POINT_RULES = {
    "Shot 3",
    "Spot-Up 3",
    "Off-Screen 3",
    "Contested 3",
    "Step-Back 3",
    "Transition Pull-Up 3",
    "Dribble Pull-Up 3",
}

MID_POST_RULES = {
    "Shot Mid",
    "Spot-Up Mid",
    "Off-Screen Mid",
    "Contested Mid",
    "Step-Back Mid",
    "Spin Jumper",
    "Dribble Pull-Up Mid",
    "Post Up",
    "Post Back Down",
    "Post Aggressive Back Down",
    "Post Face Up",
    "Post Spin",
    "Post Drive",
    "Post Drop Step",
    "Shoot From Post",
    "Post Hook Left",
    "Post Hook Right",
    "Post Fade Left",
    "Post Fade Right",
    "Post Shimmy",
    "Post Hop Shot",
    "Post Step Back",
    "Post Up & Under",
    "Triple Threat Pump Fake",
    "Triple Threat Jab Step",
    "Triple Threat Shoot",
}

ISO_RULES = {"ISO vs Elite", "ISO vs Good", "ISO vs Average", "ISO vs Poor"}

DRIBBLE_RULES = {
    "Set Up Size-Up",
    "Set Up Hesitation",
    "No Setup Dribble",
    "Drive Crossover",
    "Drive Double Crossover",
    "Drive Spin",
    "Drive Half Spin",
    "Drive Step Back",
    "Drive Behind Back",
    "Drive Hesitation",
    "Drive In & Out",
    "No Drive Dribble Move",
}

FLASHY_RULES = {"Flashy Dunk", "Flashy Pass"}

DEFENSE_RULES = {
    "Take Charge",
    "Foul",
    "Hard Foul",
    "Pass Interception",
    "On-Ball Steal",
    "Block",
    "Contest Shot",
}


ATTRIBUTE_ORDER = [
    "Driving Layup",
    "Standing Dunk",
    "Driving Dunk",
    "Close Shot",
    "Mid-Range Shot",
    "Three-Point Shot",
    "Free Throw",
    "Post Hook",
    "Post Fade",
    "Post Control",
    "Draw Foul",
    "Shot IQ",
    "Ball Handle",
    "Speed with Ball",
    "Hands",
    "Pass Accuracy",
    "Pass IQ",
    "Pass Vision",
    "Offensive Consistency",
    "Interior Defense",
    "Perimeter Defense",
    "Steal",
    "Block",
    "Offensive Rebound",
    "Defensive Rebound",
    "Help Defense IQ",
    "Pass Perception",
    "Defensive Consistency",
    "Speed",
    "Agility",
    "Strength",
    "Vertical",
    "Stamina",
    "Intangibles",
    "Hustle",
    "Overall Durability",
    "Potential",
]

ATTRIBUTE_MIN = 25
ATTRIBUTE_MAX = 95

ATTR_CONFIG: Dict[str, Dict[str, float]] = {
    "three": {
        "fg3a_pg_min": 0.5,
        "fg3a_pg_max": 8.0,
        "fg3a36_min": 0.4,
        "fg3a36_max": 13.0,
        "three_pct_min": 0.30,
        "three_pct_max": 0.41,
        "ft_pct_min": 0.60,
        "ft_pct_max": 0.90,
        "assisted3_min": 0.10,
        "assisted3_max": 0.85,
    },
    "mid": {
        "two_pct_min": 0.42,
        "two_pct_max": 0.62,
        "ft_pct_min": 0.55,
        "ft_pct_max": 0.95,
        "ts_pct_min": 0.48,
        "ts_pct_max": 0.68,
        "fg3a_pg_min": 0.5,
        "fg3a_pg_max": 8.0,
    },
    "ft": {
        "ft_pct_min": 0.58,
        "ft_pct_max": 0.93,
        "fta36_min": 0.8,
        "fta36_max": 12.0,
        "minutes_min": 350.0,
        "minutes_max": 3000.0,
    },
    "iq": {
        "usg_min": 12.0,
        "usg_max": 35.0,
        "ts_pct_min": 0.48,
        "ts_pct_max": 0.68,
        "efg_pct_min": 0.44,
        "efg_pct_max": 0.64,
        "tov_pct_min": 8.0,
        "tov_pct_max": 20.0,
        "minutes_min": 350.0,
        "minutes_max": 3000.0,
    },
}

ATTRIBUTE_FAMILIES: Dict[str, List[str]] = {
    "Finishing": [
        "Driving Layup",
        "Standing Dunk",
        "Driving Dunk",
        "Close Shot",
        "Post Hook",
        "Post Fade",
        "Post Control",
        "Draw Foul",
        "Hands",
    ],
    "Shooting": [
        "Mid-Range Shot",
        "Three-Point Shot",
        "Free Throw",
        "Shot IQ",
        "Offensive Consistency",
    ],
    "Playmaking": [
        "Ball Handle",
        "Speed with Ball",
        "Pass Accuracy",
        "Pass IQ",
        "Pass Vision",
    ],
    "Defense": [
        "Interior Defense",
        "Perimeter Defense",
        "Steal",
        "Block",
        "Offensive Rebound",
        "Defensive Rebound",
        "Help Defense IQ",
        "Pass Perception",
        "Defensive Consistency",
    ],
    "Physical": [
        "Speed",
        "Agility",
        "Strength",
        "Vertical",
        "Stamina",
    ],
    "Intangibles": [
        "Intangibles",
        "Hustle",
        "Potential",
    ],
}


def load_badge_catalog(badges_txt_path: str) -> Dict[str, List[Dict[str, str]]]:
    sections: Dict[str, List[Dict[str, str]]] = {
        "Finishing": [],
        "Shooting": [],
        "Playmaking": [],
        "Defense": [],
        "Post": [],
        "Off-Ball": [],
    }
    if not badges_txt_path or not os.path.exists(badges_txt_path):
        return sections

    current_section = "Off-Ball"
    pending_badge_name = ""
    seen_names: set = set()

    def clean_badge_name(raw_name: str) -> str:
        name = str(raw_name or "").strip()
        # Normalize editorial suffixes like "(fixed name)" in source text files.
        name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        return name

    try:
        with open(badges_txt_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = str(raw_line or "").strip()
                if not line:
                    continue
                upper = line.upper()
                lower = line.lower()
                # Section detection: only trigger on lines starting with emoji
                # (all section headers in the file use emoji prefixes).
                # This prevents badge names like "Off-Ball Pest" or descriptions
                # containing "shooting"/"defense" from triggering false changes.
                is_header = any(
                    line.startswith(e)
                    for e in (
                        "\U0001f3af",
                        "\U0001f6e1",
                        "\U0001f3c0",
                        "\U0001f9e0",
                        "\u26a0",
                    )
                )
                if is_header:
                    if "FINISHING" in upper:
                        current_section = "Finishing"
                        pending_badge_name = ""
                    elif "SHOOTING" in upper:
                        current_section = "Shooting"
                        pending_badge_name = ""
                    elif "PLAYMAKING" in upper:
                        current_section = "Playmaking"
                        pending_badge_name = ""
                    elif "DEFENSE" in upper or "REBOUNDING" in upper:
                        current_section = "Defense"
                        pending_badge_name = ""
                    elif "POST / BIG MAN" in upper:
                        current_section = "Post"
                        pending_badge_name = ""
                    elif "OFF-BALL" in upper:
                        current_section = "Off-Ball"
                        pending_badge_name = ""
                    elif "NON-STANDARD" in upper:
                        pending_badge_name = ""
                        current_section = "Off-Ball"
                    continue
                if lower.startswith("these are not official"):
                    pending_badge_name = ""
                    continue
                if "->" in line or "→" in line:
                    if pending_badge_name:
                        desc = line.replace("->", "").replace("→", "").strip()
                        cleaned_name = clean_badge_name(pending_badge_name)
                        if cleaned_name and cleaned_name.lower() not in seen_names:
                            sections.setdefault(current_section, []).append(
                                {"name": cleaned_name, "description": desc}
                            )
                            seen_names.add(cleaned_name.lower())
                        pending_badge_name = ""
                    continue
                if (
                    line.startswith("🏀")
                    or line.startswith("🎯")
                    or line.startswith("🛡️")
                    or line.startswith("⚠️")
                ):
                    continue
                if "work ethic" in line.lower() or "marketability" in line.lower():
                    continue
                if line.endswith(":") and ("badge" in lower or "official" in lower):
                    continue
                pending_badge_name = line
    except Exception:
        return sections

    return sections


# Badge functions are now imported from nba2k26_generator.badges (unified system).

ROLE_REDUNDANCY_GROUPS = [
    {"BUL", "PHY"},
    {"SHO", "H3P", "L3P"},
    {"JAT", "TWB"},
]

ROLE_CONTRADICTIONS = [
    {"SPT", "ISO"},
    {"CON", "SHH"},
    {"SHO", "FIN"},
]


def load_text_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_role_catalog(player_roles_dir: str) -> Dict[str, List[str]]:
    file_path = os.path.join(player_roles_dir, "Player Roles.txt")
    content = load_text_file(file_path)
    sections: Dict[str, List[str]] = {}
    current_section = ""
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "=" not in line and not line.endswith("("):
            section_title = re.sub(r"^\W+", "", line)
            section_title = re.sub(r"\s*\(\d+\)\s*$", "", section_title).strip()
            current_section = section_title or line
            sections.setdefault(current_section, [])
            continue
        if "=" in line:
            code = line.split("=", 1)[0].strip()
            if code:
                sections.setdefault(current_section or "roles", []).append(code)
    return sections


def load_attribute_definitions(player_roles_dir: str) -> Dict[str, str]:
    file_path = os.path.join(player_roles_dir, "NBA 2K26 ATTRIBUTES & DEFINITIONS.txt")
    content = load_text_file(file_path)
    definitions: Dict[str, str] = {}
    current_name: Optional[str] = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "(" in line and line.endswith(")") and line[0].isalpha():
            current_name = line.split("(", 1)[0].strip()
            definitions.setdefault(current_name, "")
            continue
        if current_name:
            existing = definitions.get(current_name, "")
            definitions[current_name] = (existing + " " + line).strip()
    return definitions


def compute_attribute_family_averages(attributes: Dict[str, int]) -> Dict[str, int]:
    family_scores: Dict[str, int] = {}
    for family_name, family_attributes in ATTRIBUTE_FAMILIES.items():
        values = [
            attributes[attr_name]
            for attr_name in family_attributes
            if attr_name in attributes
        ]
        if not values:
            continue
        family_scores[family_name] = int(round(sum(values) / float(len(values))))
    return family_scores


def _two_k_scale(raw: float) -> float:
    """Boost a raw composite score to align with NBA 2K's higher rating scale."""
    if raw >= 88:
        return min(99.0, raw + 3 + min(2.0, (raw - 88) * 0.3))
    if raw >= 78:
        return raw + 3
    if raw >= 68:
        return raw + 4
    if raw >= 56:
        return raw + 3
    if raw >= 40:
        return raw + 2
    return raw + 1


def compute_overall_rating(
    position: str,
    attributes: Dict[str, int],
    family_scores: Dict[str, int],
    usg: float = 0.0,
) -> int:
    """Position-aware OVR with 2K-style scaling.  Used for badge caps and backend reference."""
    pos = (position or "").upper()
    is_big = "C" in pos or "PF" in pos
    is_wing = not is_big and "SF" in pos

    fin = float(family_scores.get("Finishing", 50))
    sho = float(family_scores.get("Shooting", 50))
    plm = float(family_scores.get("Playmaking", 50))
    defe = float(family_scores.get("Defense", 50))
    phy = float(family_scores.get("Physical", 50))

    if is_big:
        # Reduced defense weight (was 0.30) – big bigs' Defense family averages
        # many non-elite attrs (off/def reb, help IQ), which dragged down elite
        # offensive bigs. Finishing elevated to reward dominant rim presence.
        base = fin * 0.30 + sho * 0.12 + plm * 0.14 + defe * 0.22 + phy * 0.22
    elif is_wing:
        # Reduced defense weight (was 0.28) for same reason; finishing raised
        # so two-way wings and offensive wings aren't over-penalised.
        base = fin * 0.24 + sho * 0.17 + plm * 0.19 + defe * 0.20 + phy * 0.20
    else:  # guard
        # Slight playmaking boost (was 0.28), shooting trimmed (was 0.26)
        base = fin * 0.10 + sho * 0.24 + plm * 0.30 + defe * 0.12 + phy * 0.24

    # Peak bonus: reward dominant performance in top 2–3 families.
    # Thresholds raised (76/73) and multipliers reduced to prevent over-rating.
    families = sorted([fin, sho, plm, defe, phy], reverse=True)
    top2_avg = sum(families[:2]) / 2.0
    top3_avg = sum(families[:3]) / 3.0

    # For guards, cap the peak bonus based on Usage%.  Low-USG facilitating
    # guards can accumulate assists on bad teams without being heliocentric
    # stars, inflating their Playmaking family.  Require higher usage to earn
    # a full peak bonus.
    if not is_big and not is_wing:
        if usg >= 30.0:
            peak_cap = 8.0  # true heliocentric superstar (Jokic-guard, SGA, Luka)
        elif usg >= 27.0:
            peak_cap = 7.0  # high-usage All-Star guard
        elif usg >= 24.0:
            peak_cap = 6.5  # solid starting guard
        else:
            peak_cap = 5.5  # low-usage facilitator / bench guard
    else:
        peak_cap = 8.0  # wings and bigs use tighter cap

    peak_bonus = min(
        peak_cap, max(0.0, top2_avg - 76) * 0.55 + max(0.0, top3_avg - 73) * 0.35
    )

    # Weakness penalty: lowered threshold (64→68) and increased multiplier (0.40→0.55)
    # to penalize one-dimensional players more aggressively.
    weakness_penalty = max(0.0, 68.0 - families[-1]) * 0.55 if top2_avg >= 78.0 else 0.0

    raw = base + peak_bonus - weakness_penalty
    scaled = _two_k_scale(raw)
    return int(round(max(25, min(99, scaled))))


def load_rows(database_dir: str) -> List[Dict[str, Any]]:
    import glob as _glob

    # Accept either a direct NBA Site data directory or a neighboring workspace folder.
    # Also check season subdirectories.
    base_candidates = [
        database_dir,
        os.path.join(database_dir, "NBA Site data"),
        os.path.join(os.path.dirname(database_dir), "NBA Site data"),
        os.path.join(os.getcwd(), "NBA Site data"),
    ]
    normalized_candidates: List[str] = []
    for bc in base_candidates:
        normalized_candidates.append(bc)
        # Also check all season subdirectories within each candidate.
        if os.path.isdir(bc):
            for sub in sorted(os.listdir(bc), reverse=True):
                subpath = os.path.join(bc, sub)
                if os.path.isdir(subpath):
                    normalized_candidates.append(subpath)
    seen: set[str] = set()
    normalized_dirs: List[str] = []
    for candidate in normalized_candidates:
        candidate_norm = os.path.normcase(os.path.abspath(candidate))
        if candidate_norm in seen:
            continue
        seen.add(candidate_norm)
        normalized_dirs.append(candidate)

    all_rows: List[Dict[str, Any]] = []
    for normalized_dir in normalized_dirs:
        matches = _glob.glob(
            os.path.join(normalized_dir, "player_traditional_*_regular_season.csv")
        )
        if not matches:
            continue
        if load_nba_site_rows is None:
            raise RuntimeError("NBA Site normalization module is unavailable.")
        rows = load_nba_site_rows(normalized_dir)
        for i, row in enumerate(rows):
            row.setdefault("__source_file", "NBA Site data (normalized)")
            row.setdefault("__row_index", i)
        all_rows.extend(rows)
    if all_rows:
        return all_rows
    raise FileNotFoundError(
        "Could not find NBA Site normalized input. "
        "Expected player_traditional_*_regular_season.csv in one of: "
        + ", ".join(normalized_dirs)
    )


def as_float(row: Dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def scale_0_100(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return clamp((value - low) / (high - low) * 100.0, 0.0, 100.0)


def remap(
    value: float, old_min: float, old_max: float, new_min: float, new_max: float
) -> float:
    if old_max <= old_min:
        return new_min
    v = clamp(value, old_min, old_max)
    proportion = (v - old_min) / (old_max - old_min)
    return new_min + proportion * (new_max - new_min)


def round_to_five(value: float) -> int:
    if value <= 0:
        return 0
    rounded = int(round(value / 5)) * 5
    return max(5, rounded) if value > 0 else 0


def normalized_weights(raw_weights: List[float]) -> List[float]:
    clipped = [max(0.0, w) for w in raw_weights]
    total = sum(clipped)
    if total <= 0.0:
        return [1.0 / len(raw_weights) for _ in raw_weights]
    return [w / total for w in clipped]


def stable_side_bias(player_key: str) -> float:
    # Deterministic per player key so left/right favorite does not change run-to-run.
    digest = hashlib.sha256(player_key.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16) / 0xFFFFFFFF
    return (value * 2.0) - 1.0


def build_zone_family_results(
    family_name: str,
    zone_names: List[str],
    raw_weights: List[float],
    parent_result: "TendencyResult",
    family_evidence: Dict[str, Any],
) -> List["TendencyResult"]:
    parent_final = parent_result.final
    if parent_final <= 0:
        return [
            TendencyResult(
                name=zone_name,
                pre_cap=0.0,
                final=0,
                recommended_cap=0,
                absolute_cap=0,
                norm_range=parent_result.norm_range,
                evidence={
                    **family_evidence,
                    "family": family_name,
                    "parent_tendency": parent_result.name,
                    "parent_final": parent_final,
                },
            )
            for zone_name in zone_names
        ]

    weights = normalized_weights(raw_weights)
    favorite_index = max(range(len(zone_names)), key=lambda i: weights[i])
    max_weight = max(weights)

    results: List[TendencyResult] = []
    for i, zone_name in enumerate(zone_names):
        if i == favorite_index:
            pre_cap = float(parent_final)
            final = parent_final
        else:
            rel = 0.0 if max_weight <= 0 else (weights[i] / max_weight)
            # Non-favorite zones are intentionally held below parent cap.
            ratio = 0.32 + (0.50 * rel)
            pre_cap = parent_final * ratio
            non_favorite_cap = max(0, parent_final - 5)
            final = round_to_five(clamp(pre_cap, 0.0, float(non_favorite_cap)))

        results.append(
            TendencyResult(
                name=zone_name,
                pre_cap=round(pre_cap, 1),
                final=final,
                recommended_cap=parent_final,
                absolute_cap=parent_final,
                norm_range=parent_result.norm_range,
                evidence={
                    **family_evidence,
                    "family": family_name,
                    "parent_tendency": parent_result.name,
                    "parent_final": parent_final,
                    "zone_weight": round(weights[i], 4),
                    "favorite_zone": zone_names[favorite_index],
                },
            )
        )

    return results


# Known basketball nickname aliases (both directions).
# Key is the full name, value is the nickname; matching checks both.
PLAYER_NICKNAME_ALIASES: Dict[str, str] = {
    "nicolas claxton": "nic claxton",
    "benjamin simmons": "ben simmons",
    "benjamin simmons": "ben simmons",
    "tj mcconnell": "t.j. mcconnell",
    "tj warren": "t.j. warren",
    "tj ford": "t.j. ford",
    "cj mccollum": "c.j. mccollum",
    "cj miles": "c.j. miles",
    "jr smith": "j.r. smith",
    "jrue holiday": "j.r. holiday",
    "jalen brunson": "jalen brunson",
    "deanthony melton": "de'anthony melton",
    "d'angelo russell": "dangelo russell",
    "deandre ayton": "dre ayton",
    "anthony davis": "ad",
    "lebron james": "king james",
    "giannis antetokounmpo": "giannis",
    "kostas antetokounmpo": "kostas",
    "thanasis antetokounmpo": "thanasis",
    "boban marjanovic": "boban",
    "lukas donic": "luka doncic",
    "luka doncic": "luka",
    "stephen curry": "steph curry",
    "william howard": "will howard",
    "miles bridges": "miles bridges",
    "miles mcbride": "miles mcbride",
    "isaiah stewart": "isaiah stewart",
    "isaiah jackson": "isaiah jackson",
    "isaiah livers": "isaiah livers",
    "isaiah mobley": "isaiah mobley",
    "evan mobley": "evan mobley",
    "marcus smart": "marcus smart",
    "marcus morris": "marcus morris sr",
    "markieff morris": "markieff morris",
    "ron artest": "metta world peace",
    "james harden": "james harden",
    "russell westbrook": "russ westbrook",
    "anthony edwards": "ant edwards",
    "jaylen brown": "jaylen brown",
    "jayson tatum": "jayson tatum",
    "kristaps porzingis": "kris porzingis",
    "domantas sabonis": "domas sabonis",
    "jonas valanciunas": "jonas",
    "nicolas batum": "nico batum",
    "nicolas tozzi": "nico tozzi",
    "christian wood": "chris wood",
    "christian braun": "chris braun",
    "christian kolo": "chris kolo",
}

# Build a reverse lookup: nickname -> full name
PLAYER_NICKNAME_REVERSE: Dict[str, str] = {
    v: k for k, v in PLAYER_NICKNAME_ALIASES.items()
}


def _find_player_match(
    target_key: str,
    rows: List[Dict[str, Any]],
    season_key: str,
) -> List[Dict[str, Any]]:
    """Hybrid player name matching: exact -> alias -> fuzzy fallback."""
    # 1. Exact match
    candidates = [
        r
        for r in rows
        if normalize_player_name_for_match(r.get("player_name", "")) == target_key
        and str(r.get("season_label", "")).strip().lower() == season_key
    ]
    if candidates:
        return candidates

    # 2. Alias match
    alias_key = PLAYER_NICKNAME_ALIASES.get(target_key)
    if alias_key:
        candidates = [
            r
            for r in rows
            if normalize_player_name_for_match(r.get("player_name", "")) == alias_key
            and str(r.get("season_label", "")).strip().lower() == season_key
        ]
        if candidates:
            return candidates

    reverse_alias = PLAYER_NICKNAME_REVERSE.get(target_key)
    if reverse_alias:
        candidates = [
            r
            for r in rows
            if normalize_player_name_for_match(r.get("player_name", "")) == reverse_alias
            and str(r.get("season_label", "")).strip().lower() == season_key
        ]
        if candidates:
            return candidates

    # 3. Fuzzy match using difflib
    import difflib

    season_rows = [
        r
        for r in rows
        if str(r.get("season_label", "")).strip().lower() == season_key
    ]
    if not season_rows:
        return []

    best_match: Optional[Dict[str, Any]] = None
    best_score = 0.0

    for row in season_rows:
        db_name = normalize_player_name_for_match(row.get("player_name", ""))
        if not db_name:
            continue
        score = difflib.SequenceMatcher(None, target_key, db_name).ratio()
        # Require a reasonably high similarity to avoid wrong matches
        if score > best_score and score >= 0.75:
            best_score = score
            best_match = row

    if best_match:
        return [best_match]

    return []


def select_player_season_row(
    rows: List[Dict[str, Any]], player_name: str, season_label: str
) -> Dict[str, Any]:
    target_player_key = normalize_player_name_for_match(player_name)
    target_season_key = str(season_label or "").strip().lower()

    candidates = _find_player_match(target_player_key, rows, target_season_key)

    # Fall back to 2024-25 for injured players with no 2025-26 data
    season_start = parse_season_start_year(season_label)
    if not candidates and season_start == 2025:
        candidates = _find_player_match(target_player_key, rows, "2024-25")

    if not candidates:
        raise ValueError(
            f"No records found for player='{player_name}' season='{season_label}'"
        )

    for row in candidates:
        if str(row.get("team_abbr", "")).upper() == "2TM":
            return row

    return max(candidates, key=lambda r: as_float(r, "totals_mp", 0.0))


def select_team_season_rows(
    rows: List[Dict[str, Any]], team_abbr: str, season_label: str
) -> List[Dict[str, Any]]:
    target_team = str(team_abbr or "").strip().upper()
    target_season = str(season_label or "").strip().lower()
    season_start = parse_season_start_year(target_season)
    min_games = (
        ACTIVE_ROSTER_MIN_GAMES_BY_YEAR.get(season_start, 0)
        if season_start is not None
        else 0
    )
    espn_signatures = (
        fetch_espn_team_roster_signatures(target_team, target_season)
        if season_start == 2025
        else None
    )
    if season_start == 2025 and not espn_signatures:
        raise ValueError(
            f"Could not fetch authoritative ESPN roster for team='{target_team}' season='{season_label}'. "
            "Generation stopped to avoid using stale local roster rows. Please retry in a moment."
        )
    if not target_team:
        raise ValueError("Team abbreviation is required.")

    season_rows = [
        r
        for r in rows
        if str(r.get("season_label", "")).strip().lower() == target_season
    ]
    if not season_rows:
        raise ValueError(
            f"No records found for team='{target_team}' season='{season_label}'"
        )

    by_player: Dict[str, List[Dict[str, Any]]] = {}
    for row in season_rows:
        key = str(row.get("player_id") or "").strip()
        if not key:
            key = normalize_player_name_for_match(row.get("player_name", ""))
        by_player.setdefault(key, []).append(row)

    selected: List[Dict[str, Any]] = []
    for _, player_rows in by_player.items():
        non_agg_rows = [
            r
            for r in player_rows
            if str(r.get("team_abbr", "")).strip().upper() != "2TM"
        ]
        if not non_agg_rows:
            continue

        # For traded players, keep the latest stint row in the source dataset.
        final_row = max(non_agg_rows, key=lambda r: int(r.get("__row_index", 0) or 0))
        if str(final_row.get("team_abbr", "")).strip().upper() == target_team:
            if (
                espn_signatures is None
                and min_games > 0
                and as_float(final_row, "totals_g", 0.0) < float(min_games)
            ):
                continue
            selected.append(final_row)

    if not selected:
        raise ValueError(
            f"No records found for team='{target_team}' season='{season_label}'"
        )

    # ESPN team roster endpoint is the source-of-truth for current-season rosters.
    if espn_signatures:
        espn_ids, espn_names = espn_signatures

        # For current-season team generation, build directly from ESPN roster names,
        # then resolve each player against local same-season data only.
        if season_start == 2025 and espn_names:
            resolved_rows: List[Dict[str, Any]] = []
            seen_keys: set[str] = set()

            # Build a 2024-25 fallback lookup keyed by normalized name
            prev_season_rows: Dict[str, Dict[str, Any]] = {}
            for r in rows:
                if str(r.get("season_label", "")).strip().lower() == "2024-25":
                    nkey = normalize_player_name_for_match(r.get("player_name", ""))
                    if nkey not in prev_season_rows:
                        prev_season_rows[nkey] = r

            for espn_name in sorted(espn_names):
                same_season_candidates = [
                    r
                    for r in season_rows
                    if normalize_player_name_for_match(r.get("player_name", ""))
                    == espn_name
                ]
                chosen = preferred_player_row(same_season_candidates)

                # Fall back to 2024-25 for injured players with no 2025-26 data
                if chosen is None:
                    chosen = prev_season_rows.get(espn_name)
                    if chosen is None:
                        continue

                dedupe_key = (
                    str(chosen.get("player_id", "")).strip().lower() or espn_name
                )
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                resolved_rows.append(chosen)

            if resolved_rows:
                return sorted(
                    resolved_rows,
                    key=lambda r: normalize_player_name_for_match(
                        r.get("player_name", "")
                    ),
                )

        espn_filtered = [
            row
            for row in selected
            if (
                str(row.get("player_id", "")).strip().lower() in espn_ids
                or normalize_player_name_for_match(row.get("player_name", ""))
                in espn_names
            )
        ]
        # For in-progress current-season generation (2025-26), treat ESPN as authoritative.
        if season_start == 2025 and espn_filtered:
            selected = espn_filtered
        else:
            # For historical seasons, apply external roster filter only when overlap is healthy.
            min_overlap = max(8, int(round(0.60 * len(selected))))
            if espn_filtered and len(espn_filtered) >= min_overlap:
                selected = espn_filtered

    return sorted(
        selected,
        key=lambda r: normalize_player_name_for_match(r.get("player_name", "")),
    )


def preferred_player_row(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows:
        return None
    for row in rows:
        if str(row.get("team_abbr", "")).strip().upper() == "2TM":
            return row
    return max(rows, key=lambda r: as_float(r, "totals_mp", 0.0))


def parse_season_start_year(season_label: str) -> Optional[int]:
    match = re.search(r"(\d{4})", str(season_label or ""))
    if not match:
        return None
    return int(match.group(1))


def parse_season_end_year(season_label: str) -> Optional[int]:
    start = parse_season_start_year(season_label)
    if start is None:
        return None
    return start + 1


def fetch_espn_team_id_map(timeout: float = 8.0) -> Dict[str, str]:
    global _ESPN_TEAM_ID_CACHE
    if _ESPN_TEAM_ID_CACHE is not None:
        return _ESPN_TEAM_ID_CACHE

    request = urllib.request.Request(
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "close",
        },
    )

    payload: Dict[str, Any] = {}
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
            break
        except Exception:
            if attempt == 2:
                _ESPN_TEAM_ID_CACHE = {}
                return _ESPN_TEAM_ID_CACHE
            time.sleep(0.6 * (attempt + 1))

    teams = payload.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
    out: Dict[str, str] = {}
    for entry in teams:
        team = entry.get("team", {}) if isinstance(entry, dict) else {}
        abbr = str(team.get("abbreviation", "")).strip().upper()
        tid = str(team.get("id", "")).strip()
        if abbr and tid:
            out[abbr] = tid

    _ESPN_TEAM_ID_CACHE = out
    return _ESPN_TEAM_ID_CACHE


def fetch_espn_team_roster_signatures(
    team_abbr: str,
    season_label: str,
    timeout: float = 8.0,
) -> Optional[Tuple[set[str], set[str]]]:
    team = str(team_abbr or "").strip().upper()
    team = ESPN_TEAM_ABBR_ALIASES.get(team, team)
    season = str(season_label or "").strip().lower()
    cache_key = (team, season)
    if cache_key in _TEAM_ROSTER_SIGNATURE_CACHE:
        return _TEAM_ROSTER_SIGNATURE_CACHE[cache_key]

    if not team:
        _TEAM_ROSTER_SIGNATURE_CACHE[cache_key] = None
        return None

    team_id = fetch_espn_team_id_map(timeout=timeout).get(team)
    if not team_id:
        _TEAM_ROSTER_SIGNATURE_CACHE[cache_key] = None
        return None

    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "close",
        },
    )

    payload: Dict[str, Any] = {}
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
            break
        except Exception:
            if attempt == 2:
                _TEAM_ROSTER_SIGNATURE_CACHE[cache_key] = None
                return None
            time.sleep(0.6 * (attempt + 1))

    ids: set[str] = set()
    names: set[str] = set()

    athletes = payload.get("athletes", []) if isinstance(payload, dict) else []
    for athlete in athletes:
        player = athlete if isinstance(athlete, dict) else {}
        # Some ESPN payloads nest players under section.items; support both shapes.
        candidates = [player]
        if isinstance(player.get("items"), list):
            candidates = [x for x in player.get("items", []) if isinstance(x, dict)]

        for p in candidates:
            pid = (
                str(p.get("id") or p.get("guid") or p.get("uid") or "").strip().lower()
            )
            if pid:
                ids.add(pid)
            full_name = repair_mojibake_text(
                p.get("fullName") or p.get("displayName") or ""
            ).strip()
            normalized = normalize_player_name_for_match(full_name)
            if normalized:
                names.add(normalized)

    if not ids and not names:
        _TEAM_ROSTER_SIGNATURE_CACHE[cache_key] = None
        return None

    _TEAM_ROSTER_SIGNATURE_CACHE[cache_key] = (ids, names)
    return _TEAM_ROSTER_SIGNATURE_CACHE[cache_key]


def fetch_espn_team_player_ids(
    team_abbr: str, season_label: str, timeout: float = 8.0
) -> Optional[set[str]]:
    cache_key = (
        str(team_abbr or "").strip().upper(),
        str(season_label or "").strip().lower(),
    )
    if cache_key in _TEAM_ROSTER_CACHE:
        return _TEAM_ROSTER_CACHE[cache_key]

    signatures = fetch_espn_team_roster_signatures(
        team_abbr, season_label, timeout=timeout
    )
    if not signatures:
        _TEAM_ROSTER_CACHE[cache_key] = None
        return None

    ids, _names = signatures
    _TEAM_ROSTER_CACHE[cache_key] = ids if ids else None
    return _TEAM_ROSTER_CACHE[cache_key]


def infer_era_key(row: Dict[str, Any]) -> str:
    start_year = parse_season_start_year(str(row.get("season_label", "")))
    if start_year is None:
        source_file = str(row.get("__source_file", ""))
        source_match = re.search(r"attribute_source_(\d{4})_(\d{4})", source_file)
        if source_match:
            start_year = int(source_match.group(2))

    if start_year is None:
        return "2020_2025"
    if start_year <= 2008:
        return "2000_2008"
    if start_year <= 2014:
        return "2009_2014"
    if start_year <= 2019:
        return "2015_2019"
    return "2020_2025"


def tendency_era_cap_delta(tendency_name: str, era_profile: EraProfile) -> int:
    if tendency_name in THREE_POINT_RULES:
        return era_profile.three_point_cap_delta
    if tendency_name in MID_POST_RULES:
        return era_profile.mid_post_cap_delta
    if tendency_name in ISO_RULES:
        return era_profile.iso_cap_delta
    if tendency_name in DRIBBLE_RULES:
        return era_profile.dribble_cap_delta
    if tendency_name in FLASHY_RULES:
        return era_profile.flashy_cap_delta
    if tendency_name in DEFENSE_RULES:
        return era_profile.defense_cap_delta
    return 0


def parse_cap_upper_bound(text: str) -> int | None:
    matches = [int(x) for x in re.findall(r"\d+", text or "")]
    if not matches:
        return None
    return max(matches)


def load_workbook_cap_overrides(workbook_path: str) -> Dict[str, Tuple[int, int]]:
    if workbook_path in _WORKBOOK_CAP_CACHE:
        return _WORKBOOK_CAP_CACHE[workbook_path]

    overrides: Dict[str, Tuple[int, int]] = {}
    if not os.path.exists(workbook_path):
        _WORKBOOK_CAP_CACHE[workbook_path] = overrides
        return overrides

    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    try:
        with ZipFile(workbook_path, "r") as z:
            workbook_xml = ET.fromstring(z.read("xl/workbook.xml"))
            sheet = workbook_xml.find("a:sheets/a:sheet", ns)
            if sheet is None:
                _WORKBOOK_CAP_CACHE[workbook_path] = overrides
                return overrides

            rid = sheet.attrib.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            )
            rels_xml = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
            target = None
            for rel in rels_xml:
                if rel.attrib.get("Id") == rid:
                    target = rel.attrib.get("Target")
                    break
            if not target:
                _WORKBOOK_CAP_CACHE[workbook_path] = overrides
                return overrides
            if not target.startswith("xl/"):
                target = "xl/" + target

            shared_strings: List[str] = []
            if "xl/sharedStrings.xml" in z.namelist():
                sst_xml = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in sst_xml.findall("a:si", ns):
                    shared_strings.append(
                        "".join((t.text or "") for t in si.findall(".//a:t", ns))
                    )

            sheet_xml = ET.fromstring(z.read(target))
            sheet_data = sheet_xml.find("a:sheetData", ns)
            if sheet_data is None:
                _WORKBOOK_CAP_CACHE[workbook_path] = overrides
                return overrides

            def cell_text(cell: ET.Element) -> str:
                value_elem = cell.find("a:v", ns)
                if value_elem is None:
                    inline = cell.find("a:is", ns)
                    if inline is None:
                        return ""
                    return "".join((t.text or "") for t in inline.findall(".//a:t", ns))
                raw = value_elem.text or ""
                if cell.attrib.get("t") == "s":
                    try:
                        idx = int(raw)
                    except ValueError:
                        return ""
                    if 0 <= idx < len(shared_strings):
                        return shared_strings[idx]
                    return ""
                return raw

            header_by_col: Dict[str, str] = {}
            rec_by_col: Dict[str, int] = {}
            abs_by_col: Dict[str, int] = {}

            for row in sheet_data.findall("a:row", ns):
                row_num = int(row.attrib.get("r", "0"))
                for cell in row.findall("a:c", ns):
                    ref = cell.attrib.get("r", "")
                    col = "".join(ch for ch in ref if ch.isalpha())
                    txt = cell_text(cell)
                    if row_num == 1:
                        header_by_col[col] = txt.strip()
                    elif row_num == 12:
                        cap = parse_cap_upper_bound(txt)
                        if cap is not None:
                            rec_by_col[col] = cap
                    elif row_num == 13:
                        cap = parse_cap_upper_bound(txt)
                        if cap is not None:
                            abs_by_col[col] = cap

            for col, name in header_by_col.items():
                if not name:
                    continue
                rec_cap = rec_by_col.get(col)
                abs_cap = abs_by_col.get(col)
                if rec_cap is None or abs_cap is None:
                    continue
                overrides[name] = (rec_cap, abs_cap)
    except Exception:
        # If workbook parsing fails, keep existing in-code caps.
        overrides = {}

    _WORKBOOK_CAP_CACHE[workbook_path] = overrides
    return overrides


def build_tendency_rules() -> Dict[str, TendencyRule]:
    rules: Dict[str, TendencyRule] = {
        "Shot": TendencyRule("Shot", (30, 45), 45, 70),
        "Touches": TendencyRule("Touches", (35, 45), 45, 70),
        "Shot Close": TendencyRule("Shot Close", (35, 45), 45, 55),
        "Shot Under": TendencyRule("Shot Under", (35, 45), 45, 65),
        "Shot Mid": TendencyRule("Shot Mid", (25, 35), 35, 55),
        "Spot-Up Mid": TendencyRule("Spot-Up Mid", (15, 25), 35, 45),
        "Off-Screen Mid": TendencyRule("Off-Screen Mid", (15, 25), 40, 45),
        "Shot 3": TendencyRule("Shot 3", (35, 45), 40, 60),
        "Spot-Up 3": TendencyRule("Spot-Up 3", (30, 45), 40, 50),
        "Off-Screen 3": TendencyRule("Off-Screen 3", (15, 25), 45, 45),
        "Contested Mid": TendencyRule("Contested Mid", (15, 25), 40, 45),
        "Contested 3": TendencyRule("Contested 3", (15, 25), 40, 40),
        "Step-Back Mid": TendencyRule("Step-Back Mid", (15, 25), 40, 45),
        "Step-Back 3": TendencyRule("Step-Back 3", (10, 20), 45, 45),
        "Spin Jumper": TendencyRule("Spin Jumper", (5, 15), 35, 35),
        "Transition Pull-Up 3": TendencyRule("Transition Pull-Up 3", (5, 15), 30, 35),
        "Dribble Pull-Up Mid": TendencyRule("Dribble Pull-Up Mid", (10, 20), 30, 45),
        "Dribble Pull-Up 3": TendencyRule("Dribble Pull-Up 3", (10, 25), 45, 50),
        "Drive": TendencyRule("Drive", (35, 40), 45, 60),
        "Spot-Up Drive": TendencyRule("Spot-Up Drive", (30, 45), 45, 60),
        "Off-Screen Drive": TendencyRule("Off-Screen Drive", (35, 40), 45, 60),
        "Use Glass": TendencyRule("Use Glass", (15, 25), 35, 45),
        "Step Through": TendencyRule("Step Through", (10, 20), 25, 35),
        "Spin Layup": TendencyRule("Spin Layup", (10, 15), 20, 35),
        "Eurostep": TendencyRule("Eurostep", (15, 25), 35, 45),
        "Hop Step": TendencyRule("Hop Step", (15, 25), 45, 35),
        "Floater": TendencyRule("Floater", (10, 25), 45, 55),
        "Standing Dunk": TendencyRule("Standing Dunk", (20, 45), 45, 65),
        "Driving Dunk": TendencyRule("Driving Dunk", (20, 45), 45, 55),
        "Flashy Dunk": TendencyRule("Flashy Dunk", (10, 20), 35, 50),
        "Alley-Oop": TendencyRule("Alley-Oop", (10, 25), 60, 75),
        "Putback": TendencyRule("Putback", (10, 25), 45, 50),
        "Crash": TendencyRule("Crash", (0, 35), 35, 35),
        "Drive Right": TendencyRule("Drive Right", (45, 55), 65, 65),
        "Triple Threat Pump Fake": TendencyRule(
            "Triple Threat Pump Fake", (20, 35), 35, 45
        ),
        "Triple Threat Jab Step": TendencyRule(
            "Triple Threat Jab Step", (20, 35), 35, 45
        ),
        "Triple Threat Idle": TendencyRule("Triple Threat Idle", (5, 40), 40, 40),
        "Triple Threat Shoot": TendencyRule("Triple Threat Shoot", (3, 55), 55, 55),
        "Set Up Size-Up": TendencyRule("Set Up Size-Up", (20, 35), 45, 45),
        "Set Up Hesitation": TendencyRule("Set Up Hesitation", (20, 35), 45, 45),
        "No Setup Dribble": TendencyRule("No Setup Dribble", (25, 40), 45, 45),
        "Drive Crossover": TendencyRule("Drive Crossover", (20, 35), 45, 45),
        "Drive Double Crossover": TendencyRule(
            "Drive Double Crossover", (20, 35), 45, 45
        ),
        "Drive Spin": TendencyRule("Drive Spin", (0, 15), 15, 15),
        "Drive Half Spin": TendencyRule("Drive Half Spin", (0, 10), 10, 10),
        "Drive Step Back": TendencyRule("Drive Step Back", (5, 15), 10, 25),
        "Drive Behind Back": TendencyRule("Drive Behind Back", (20, 35), 25, 45),
        "Drive Hesitation": TendencyRule("Drive Hesitation", (15, 30), 35, 35),
        "Drive In & Out": TendencyRule("Drive In & Out", (15, 30), 35, 35),
        "No Drive Dribble Move": TendencyRule(
            "No Drive Dribble Move", (35, 45), 45, 50
        ),
        "Attack Strong Drive": TendencyRule("Attack Strong Drive", (25, 50), 45, 50),
        "Dish": TendencyRule("Dish", (20, 35), 35, 50),
        "Flashy Pass": TendencyRule("Flashy Pass", (10, 20), 35, 45),
        "Alley-Oop Pass": TendencyRule("Alley-Oop Pass", (10, 20), 55, 65),
        "Roll vs Pop": TendencyRule("Roll vs Pop", (45, 55), 55, 65),
        "Spot vs Cut": TendencyRule("Spot vs Cut", (30, 45), 55, 65),
        "ISO vs Elite": TendencyRule("ISO vs Elite", (10, 20), 35, 35),
        "ISO vs Good": TendencyRule("ISO vs Good", (20, 30), 45, 45),
        "ISO vs Average": TendencyRule("ISO vs Average", (25, 35), 45, 50),
        "ISO vs Poor": TendencyRule("ISO vs Poor", (30, 40), 45, 55),
        "Play Discipline": TendencyRule("Play Discipline", (30, 45), 30, 50),
        "Post Up": TendencyRule("Post Up", (10, 25), 35, 55),
        "Post Back Down": TendencyRule("Post Back Down", (10, 25), 45, 50),
        "Post Aggressive Back Down": TendencyRule(
            "Post Aggressive Back Down", (10, 20), 35, 45
        ),
        "Post Face Up": TendencyRule("Post Face Up", (10, 25), 35, 45),
        "Post Spin": TendencyRule("Post Spin", (10, 25), 35, 45),
        "Post Drive": TendencyRule("Post Drive", (10, 25), 35, 45),
        "Post Drop Step": TendencyRule("Post Drop Step", (5, 15), 30, 45),
        "Shoot From Post": TendencyRule("Shoot From Post", (20, 30), 35, 50),
        "Post Hook Left": TendencyRule("Post Hook Left", (15, 30), 35, 45),
        "Post Hook Right": TendencyRule("Post Hook Right", (15, 30), 35, 45),
        "Post Fade Left": TendencyRule("Post Fade Left", (15, 30), 35, 45),
        "Post Fade Right": TendencyRule("Post Fade Right", (15, 30), 35, 45),
        "Post Shimmy": TendencyRule("Post Shimmy", (20, 25), 35, 45),
        "Post Hop Shot": TendencyRule("Post Hop Shot", (15, 25), 30, 45),
        "Post Step Back": TendencyRule("Post Step Back", (15, 25), 35, 45),
        "Post Up & Under": TendencyRule("Post Up & Under", (15, 25), 35, 45),
        "Take Charge": TendencyRule("Take Charge", (15, 35), 40, 50),
        "Foul": TendencyRule("Foul", (25, 35), 45, 70),
        "Hard Foul": TendencyRule("Hard Foul", (10, 20), 35, 70),
        "Pass Interception": TendencyRule("Pass Interception", (25, 35), 45, 70),
        "On-Ball Steal": TendencyRule("On-Ball Steal", (25, 35), 45, 70),
        "Block": TendencyRule("Block", (25, 35), 45, 70),
        "Contest Shot": TendencyRule("Contest Shot", (25, 40), 45, 70),
    }

    workbook_path = os.path.join(os.getcwd(), "Copilot_Optimized_ATD_Tendencies.xlsx")
    workbook_caps = load_workbook_cap_overrides(workbook_path)
    for rule_name, rule in list(rules.items()):
        caps = workbook_caps.get(rule_name)
        if not caps:
            continue
        rec_cap, abs_cap = caps
        rules[rule_name] = TendencyRule(rule.name, rule.norm_range, rec_cap, abs_cap)

    # Override defensive tendency caps: abs cap 70 for all except Take Charge
    defensive_overrides = {
        "Foul": (45, 70),
        "Hard Foul": (35, 70),
        "Pass Interception": (45, 70),
        "On-Ball Steal": (45, 70),
        "Block": (45, 70),
        "Contest Shot": (45, 70),
    }
    for name, (rec, abs_c) in defensive_overrides.items():
        if name in rules:
            rules[name] = TendencyRule(rules[name].name, rules[name].norm_range, rec, abs_c)

    # Crash is now explicitly bumper-tuned with a hard 0-35 range.
    if "Crash" in rules:
        crash_rule = rules["Crash"]
        rules["Crash"] = TendencyRule(crash_rule.name, (0, 35), 35, 35)

    # Anti-spam dribble constraints requested for all players.
    if "Drive Spin" in rules:
        rules["Drive Spin"] = TendencyRule("Drive Spin", (0, 15), 15, 15)
    if "Drive Half Spin" in rules:
        rules["Drive Half Spin"] = TendencyRule("Drive Half Spin", (0, 10), 10, 10)
    if "Triple Threat Idle" in rules:
        rules["Triple Threat Idle"] = TendencyRule(
            "Triple Threat Idle", (5, 40), 40, 40
        )
    if "Pass Interception" in rules:
        rules["Pass Interception"] = TendencyRule("Pass Interception", (20, 35), 45, 70)
    return rules


def compute_tendencies(row: Dict[str, Any]) -> List[TendencyResult]:
    rules = build_tendency_rules()
    era_key = infer_era_key(row)
    era_profile = ERA_PROFILES.get(era_key, ERA_PROFILES["2020_2025"])

    usg = as_float(row, "advanced_usg_percent")
    fga36 = as_float(row, "per_36_fga_per_36_min")
    fg3a36 = as_float(row, "per_36_x3pa_per_36_min")
    fg3ar = as_float(row, "advanced_x3p_ar")
    ast_pct = as_float(row, "advanced_ast_percent")
    ast100 = as_float(row, "per_100_ast_per_100_poss")
    fta36 = as_float(row, "per_36_fta_per_36_min")
    rim_share = as_float(row, "shooting_percent_fga_from_x0_3_range")
    close_share = as_float(row, "shooting_percent_fga_from_x3_10_range")
    mid_share = as_float(row, "shooting_percent_fga_from_x10_16_range")
    long_mid_share = as_float(row, "shooting_percent_fga_from_x16_3p_range")
    three_share = as_float(row, "shooting_percent_fga_from_x3p_range")
    corner_three_share = as_float(row, "shooting_percent_corner_3s_of_3pa")
    pullup3_freq = as_float(row, "pbp_features_pullup_3_freq")
    pullup3_pct = as_float(row, "pbp_features_pullup_3p_pct")
    assisted3 = as_float(row, "shooting_percent_assisted_x3p_fg")
    three_pct = as_float(
        row, "per_36_x3p_percent", as_float(row, "per_game_x3p_percent")
    )
    avg_dist = as_float(row, "shooting_avg_dist_fga")
    assisted2 = as_float(row, "shooting_percent_assisted_x2p_fg")
    dunks_share = as_float(row, "shooting_percent_dunks_of_fga")
    dunk_count = as_float(row, "shooting_num_of_dunks")
    pullup_freq = as_float(row, "pbp_features_pullup_freq")
    stepback_freq = as_float(row, "pbp_features_stepback_freq")
    fade_freq = as_float(row, "pbp_features_fadeaway_freq")
    hook_freq = as_float(row, "pbp_features_hook_freq")
    post_fta = as_float(row, "per_100_fta_per_100_poss")
    orb_pct = as_float(row, "advanced_orb_percent")
    tov_pct = as_float(row, "advanced_tov_percent")
    stl_pct = as_float(row, "advanced_stl_percent")
    blk_pct = as_float(row, "advanced_blk_percent")
    contest_proxy = as_float(row, "play_by_play_fga_blocked")
    hard_foul_proxy = as_float(row, "play_by_play_shooting_foul_committed")
    charges_drawn_pg = as_float(row, "hustle_charges_drawn_pg")
    deflections_pg = as_float(row, "hustle_deflections_pg")
    position = str(row.get("position", ""))
    is_big = ("C" in position) or ("PF" in position)
    is_guard = ("PG" in position) or ("SG" in position)

    # Playtype possession shares (0-1 ratio: what fraction of possessions used this play type).
    pt_iso_poss = as_float(row, "playtype_iso_poss_pct")
    pt_iso_fg = as_float(row, "playtype_iso_fg_pct")
    pt_iso_ppp = as_float(row, "playtype_iso_ppp")
    pt_iso_pctl = as_float(row, "playtype_iso_percentile")
    pt_spot_up_poss = as_float(row, "playtype_spot_up_poss_pct")
    pt_spot_up_fg = as_float(row, "playtype_spot_up_fg_pct")
    pt_ball_handler_poss = as_float(row, "playtype_ball_handler_poss_pct")
    pt_ball_handler_fg = as_float(row, "playtype_ball_handler_fg_pct")
    pt_ball_handler_ppp = as_float(row, "playtype_ball_handler_ppp")
    pt_off_screen_poss = as_float(row, "playtype_off_screen_poss_pct")
    pt_off_screen_fg = as_float(row, "playtype_off_screen_fg_pct")
    pt_hand_off_poss = as_float(row, "playtype_hand_off_poss_pct")
    pt_post_up_poss = as_float(row, "playtype_post_up_poss_pct")
    pt_post_up_fg = as_float(row, "playtype_post_up_fg_pct")
    pt_roll_man_poss = as_float(row, "playtype_roll_man_poss_pct")
    pt_cut_poss = as_float(row, "playtype_cut_poss_pct")

    # Tracking drive data.
    tracking_drives_pg = as_float(row, "tracking_drives_pg")
    tracking_drive_fg_pct = as_float(row, "tracking_drive_fg_pct")
    tracking_drive_pass_rate = as_float(row, "tracking_drive_pass_rate")
    tracking_paint_touches_pg = as_float(row, "tracking_paint_touches_pg")
    tracking_touches_pg = as_float(row, "tracking_touches_pg")
    tracking_avg_sec_per_touch = as_float(row, "tracking_avg_sec_per_touch")
    tracking_avg_drib_per_touch = as_float(row, "tracking_avg_drib_per_touch")

    # Catch-and-shoot data.
    catch_shoot_fg3a_pg = as_float(row, "tracking_catch_shoot_fg3a_pg")
    catch_shoot_fg3_pct = as_float(row, "tracking_catch_shoot_fg3_pct")

    # Shot dashboard: dribble breakdown.
    shot_dash_zero_drib_freq = as_float(row, "shot_dash_zero_drib_freq")
    shot_dash_zero_drib_fg_pct = as_float(row, "shot_dash_zero_drib_fg_pct")
    shot_dash_off_dribble_freq = as_float(row, "shot_dash_off_dribble_freq")
    shot_dash_7p_drib_freq = as_float(row, "shot_dash_7p_drib_freq")
    shot_dash_7p_drib_fg_pct = as_float(row, "shot_dash_7p_drib_fg_pct")

    # Shot dashboard: closest defender.
    shot_dash_contested_freq = as_float(row, "shot_dash_contested_freq")
    shot_dash_contested_fg_pct = as_float(row, "shot_dash_contested_fg_pct")
    shot_dash_contested_delta = as_float(row, "shot_dash_contested_delta")
    shot_dash_tight_fg_pct = as_float(row, "shot_dash_tight_fg_pct")
    shot_dash_very_tight_fg_pct = as_float(row, "shot_dash_very_tight_fg_pct")

    # Shot dashboard: touch time.
    shot_dash_touch_lt2_freq = as_float(row, "shot_dash_touch_lt2_freq")
    shot_dash_touch_lt2_efg = as_float(row, "shot_dash_touch_lt2_efg")
    shot_dash_touch_6p_freq = as_float(row, "shot_dash_touch_6p_freq")
    shot_dash_touch_6p_fg_pct = as_float(row, "shot_dash_touch_6p_fg_pct")

    # Transition playtype data.
    transition_poss_pct = as_float(row, "playtype_transition_poss_pct")
    transition_ppp = as_float(row, "playtype_transition_ppp")
    transition_score_pct = as_float(row, "playtype_transition_score_pct")
    transition_poss = as_float(row, "playtype_transition_poss")

    # Misc data.
    misc_pts_paint_pg = as_float(row, "misc_pts_paint_pg")
    misc_pts_fb_pg = as_float(row, "misc_pts_fb_pg")
    misc_pts_2nd_chance_pg = as_float(row, "misc_pts_2nd_chance_pg")
    misc_blka_pg = as_float(row, "misc_blka_pg")
    misc_pfd_pg = as_float(row, "misc_pfd_pg")

    # Elbow touch data.
    elbow_touches_pg = as_float(row, "tracking_elbow_touches_pg")
    elbow_touch_fg_pct = as_float(row, "tracking_elbow_touch_fg_pct")
    elbow_touch_pts_pct = as_float(row, "tracking_elbow_touch_pts_pct")

    # Scoring percentage data.
    scoring_pct_pts_paint = as_float(row, "scoring_pct_pts_paint")
    scoring_pct_pts_fb = as_float(row, "scoring_pct_pts_fb")
    scoring_pct_uast_2pm = as_float(row, "scoring_pct_uast_2pm")
    scoring_pct_uast_3pm = as_float(row, "scoring_pct_uast_3pm")

    # Hustle contest data.
    hustle_contested_shots_pg = as_float(row, "hustle_contested_shots_pg")
    hustle_contested_2pt_pg = as_float(row, "hustle_contested_2pt_pg")
    hustle_contested_3pt_pg = as_float(row, "hustle_contested_3pt_pg")

    # Defense dash data.
    defense_dash_overall_stop = as_float(row, "defense_dash_overall_stop_delta")
    defense_dash_3pt_stop = as_float(row, "defense_dash_3pt_stop_delta")
    defense_dash_lt6_stop = as_float(row, "defense_dash_lt6_stop_delta")

    # Zone FGA breakdowns for sub-zone tendencies.
    zone_restricted_fga = as_float(row, "zone_restricted_fga")
    zone_paint_non_ra_fga = as_float(row, "zone_paint_non_ra_fga")
    zone_mid_fga = as_float(row, "zone_mid_fga")
    zone_left_corner_3_fga = as_float(row, "zone_left_corner_3_fga")
    zone_right_corner_3_fga = as_float(row, "zone_right_corner_3_fga")
    zone_above_break_3_fga = as_float(row, "zone_above_break_3_fga")

    player_key = str(row.get("player_id") or row.get("player_name") or "unknown_player")
    side_bias = stable_side_bias(player_key)

    def normalize_freq_01(value: float) -> float:
        # Some feeds carry these as percentages (e.g., 11.7) instead of ratios (0.117).
        v = max(0.0, float(value))
        if v > 1.0:
            v = v / 100.0
        return clamp(v, 0.0, 1.0)

    pullup3_freq = normalize_freq_01(pullup3_freq)
    pullup_freq = normalize_freq_01(pullup_freq)
    stepback_freq = normalize_freq_01(stepback_freq)
    fade_freq = normalize_freq_01(fade_freq)
    hook_freq = normalize_freq_01(hook_freq)

    # Soft-cap power controls how much a player can exceed recommended caps toward absolute caps.
    # This is applied across tendencies (unless explicitly disabled per rule call).
    # Offensive track: driven by USG, FGA, AST%
    offense_cap_power = clamp(
        (
            0.45 * scale_0_100(usg, 16, 36)
            + 0.35 * scale_0_100(fga36, 9, 24)
            + 0.20 * scale_0_100(ast_pct, 6, 40)
            - 60.0
        )
        / 40.0,
        0.0,
        1.0,
    )
    # Defensive track: driven by BLK%, STL%, deflections
    defense_disruption = (
        0.40 * scale_0_100(blk_pct, 0.5, 5.0)
        + 0.35 * scale_0_100(stl_pct, 0.5, 3.5)
        + 0.25 * scale_0_100(deflections_pg, 0.5, 4.5)
    )
    defense_cap_power = clamp(
        (defense_disruption - 15.0) / 55.0,
        0.0,
        1.0,
    )
    soft_cap_power = max(offense_cap_power, defense_cap_power)
    post_soft_cap_power = max(
        soft_cap_power,
        clamp(
            (
                0.35 * scale_0_100(pt_post_up_poss, 0.01, 0.18)
                + 0.25 * scale_0_100(post_fta, 1.5, 12.0)
                + 0.20 * scale_0_100(hook_freq + fade_freq, 0.01, 0.20)
                + 0.20 * scale_0_100(tracking_paint_touches_pg, 2.0, 14.0)
                - 20.0
            )
            / 50.0,
            0.0,
            1.0,
        ),
    )

    def by_rule(
        name: str,
        pre_cap: float,
        evidence: Dict[str, Any],
        apply_recommended_cap: bool = True,
        soft_cap_power_override: Optional[float] = None,
    ) -> TendencyResult:
        rule = rules[name]
        era_cap_delta = tendency_era_cap_delta(name, era_profile)
        rec_cap = clamp(float(rule.recommended_cap + era_cap_delta), 0.0, 100.0)
        abs_cap = clamp(float(rule.absolute_cap + era_cap_delta), 0.0, 100.0)
        if abs_cap < rec_cap:
            abs_cap = rec_cap
        effective_soft_cap_power = (
            clamp(float(soft_cap_power_override), 0.0, 1.0)
            if soft_cap_power_override is not None
            else soft_cap_power
        )
        if apply_recommended_cap:
            if abs_cap > rec_cap:
                soft_rec_ceiling = rec_cap + (
                    (abs_cap - rec_cap) * effective_soft_cap_power
                )
                bounded = min(pre_cap, soft_rec_ceiling, abs_cap)
            else:
                bounded = min(pre_cap, rec_cap, abs_cap)
        else:
            bounded = min(pre_cap, abs_cap)
        final = round_to_five(clamp(bounded, 0.0, 100.0))
        return TendencyResult(
            name=name,
            pre_cap=round(clamp(pre_cap, 0.0, 100.0), 1),
            final=final,
            recommended_cap=int(round(rec_cap)),
            absolute_cap=int(round(abs_cap)),
            norm_range=rule.norm_range,
            evidence={
                **evidence,
                "apply_recommended_cap": apply_recommended_cap,
                "soft_cap_power": round(effective_soft_cap_power, 3),
                "era_key": era_profile.key,
                "era_label": era_profile.label,
                "era_cap_delta": era_cap_delta,
            },
        )

    efg_pct = as_float(row, "per_36_e_fg_percent")
    ts_pct = as_float(row, "advanced_ts_percent", efg_pct)
    mpg = as_float(row, "per_game_mp_per_game")
    gp = as_float(row, "per_game_g")

    # ── Role classification for Shot/Touch tendency ranges ──────────────
    # role_score determines player tier: Star, Starter, Bench, Sub-10
    role_score = clamp(
        0.40 * scale_0_100(mpg, 8, 38)
        + 0.35 * scale_0_100(usg, 10, 38)
        + 0.25 * scale_0_100(as_float(row, "per_game_pts_per_game"), 0, 35),
        0.0,
        100.0,
    )

    if gp < 10:
        # Players under 10 games: automatic 20-25 range
        shot = 20 + 5 * scale_0_100(fga36, 3, 12) / 100.0
        touch = 20 + 5 * scale_0_100(
            tracking_touches_pg, 20, 50
        ) / 100.0
    elif role_score >= 60:
        # Star: 50-65 range
        shot = 50 + 15 * scale_0_100(fga36, 12, 25) / 100.0
        touch = 50 + 15 * (
            0.60 * scale_0_100(tracking_touches_pg, 60, 100)
            + 0.40 * scale_0_100(ast_pct, 10, 45)
        ) / 100.0
    elif role_score >= 40:
        # Starter: 35-45 range
        shot = 35 + 10 * scale_0_100(fga36, 8, 18) / 100.0
        touch = 35 + 10 * (
            0.55 * scale_0_100(tracking_touches_pg, 40, 80)
            + 0.45 * scale_0_100(ast_pct, 5, 35)
        ) / 100.0
    elif role_score >= 20:
        # Bench: 20-30 range
        shot = 20 + 10 * scale_0_100(fga36, 5, 15) / 100.0
        touch = 20 + 10 * (
            0.50 * scale_0_100(tracking_touches_pg, 30, 60)
            + 0.50 * scale_0_100(ast_pct, 3, 25)
        ) / 100.0
    else:
        # Deep bench / end of rotation: 15-20 range
        shot = 15 + 5 * scale_0_100(fga36, 3, 10) / 100.0
        touch = 15 + 5 * (
            0.50 * scale_0_100(tracking_touches_pg, 20, 45)
            + 0.50 * scale_0_100(ast_pct, 2, 15)
        ) / 100.0

    # Shooter role floor: high-volume 3PT shooters need decent Shot tendency
    # even with low USG (catch-and-shoot specialists)
    if fg3a36 >= 8.0:
        shot = max(shot, 45.0)
    elif fg3a36 >= 6.0:
        shot = max(shot, 40.0)
    elif fg3a36 >= 4.0:
        shot = max(shot, 35.0)

    shot_creation_signal = (
        0.50 * scale_0_100(usg, 20, 36)
        + 0.35 * scale_0_100(fga36, 12, 24)
        + 0.15 * scale_0_100(1.0 - assisted2, 0.15, 0.85)
    )
    if is_guard:
        shot_soft_cap_power = max(
            soft_cap_power, 0.35 + 0.55 * (shot_creation_signal / 100.0)
        )
    else:
        shot_soft_cap_power = max(
            soft_cap_power, 0.30 + 0.50 * (shot_creation_signal / 100.0)
        )
    playtype_touch_signal = (
        0.40 * scale_0_100(pt_iso_poss, 0.02, 0.30)
        + 0.35 * scale_0_100(pt_post_up_poss, 0.01, 0.25)
        + 0.25 * scale_0_100(pt_ball_handler_poss, 0.02, 0.30)
    )
    total_zone_fga = (
        zone_restricted_fga
        + zone_paint_non_ra_fga
        + zone_mid_fga
        + zone_left_corner_3_fga
        + zone_right_corner_3_fga
        + zone_above_break_3_fga
    )
    zone_paint_share = zone_paint_non_ra_fga / max(total_zone_fga, 1.0)
    zone_restricted_share = zone_restricted_fga / max(total_zone_fga, 1.0)
    zone_mid_share_pct = zone_mid_fga / max(total_zone_fga, 1.0)
    shot_close = (
        0.50 * scale_0_100(close_share, 0.03, 0.35)
        + 0.30 * scale_0_100(zone_paint_share, 0.02, 0.20)
        + 0.20 * scale_0_100(fga36, 7, 25)
    )
    shot_under = (
        0.55 * scale_0_100(rim_share, 0.05, 0.75)
        + 0.25 * scale_0_100(zone_restricted_share, 0.10, 0.60)
        + 0.20 * scale_0_100(dunks_share, 0.00, 0.25)
    )
    shot_mid = (
        0.40 * scale_0_100(1.0 - fg3ar, 0.25, 0.85)
        + 0.30 * scale_0_100(zone_mid_share_pct, 0.05, 0.35)
        + 0.30 * scale_0_100(avg_dist, 6, 18)
    )
    spot_up_mid = (
        0.25 * scale_0_100(mid_share + long_mid_share, 0.03, 0.45)
        + 0.22 * scale_0_100(assisted2, 0.30, 0.95)
        + 0.22 * scale_0_100(pt_spot_up_poss, 0.02, 0.35)
        + 0.18 * scale_0_100(1.0 - fg3ar, 0.25, 0.85)
        + 0.13 * scale_0_100(shot_dash_zero_drib_freq, 0.30, 0.85)
    )
    off_screen_mid = (
        0.28 * scale_0_100(pt_off_screen_poss, 0.01, 0.15)
        + 0.25 * scale_0_100(mid_share, 0.02, 0.25)
        + 0.25 * scale_0_100(stepback_freq + fade_freq, 0.00, 0.10)
        + 0.22 * scale_0_100(pullup_freq, 0.00, 0.22)
    )
    off_screen_mid *= 0.55 + 0.45 * (scale_0_100(1.0 - assisted2, 0.10, 0.75) / 100.0)
    movement_mid_signal = (
        0.45 * scale_0_100(stepback_freq + fade_freq, 0.03, 0.20)
        + 0.35 * scale_0_100(pullup_freq, 0.04, 0.26)
        + 0.20 * scale_0_100(1.0 - assisted2, 0.15, 0.75)
    )
    off_screen_mid *= 0.45 + 0.55 * (movement_mid_signal / 100.0)
    if (not is_guard) and movement_mid_signal < 40.0:
        off_screen_mid *= 0.75
    if is_big and stepback_freq < 0.08 and fade_freq < 0.10:
        off_screen_mid *= 0.72
    if is_big and movement_mid_signal < 55.0:
        off_screen_mid *= 0.68
    if not is_guard:
        non_guard_off_mid_cap = (
            20.0
            + 20.0
            * (scale_0_100(stepback_freq + fade_freq + pullup_freq, 0.10, 0.55) / 100.0)
            + 10.0 * (scale_0_100(mid_share, 0.04, 0.25) / 100.0)
        )
        off_screen_mid = min(off_screen_mid, non_guard_off_mid_cap)
    shot_3 = (
        0.35 * scale_0_100(fg3a36, 0.5, 14.0)
        + 0.30 * scale_0_100(fg3ar, 0.05, 0.75)
        + 0.20 * scale_0_100(catch_shoot_fg3a_pg, 0.5, 8.0)
        + 0.15 * scale_0_100(pt_spot_up_poss, 0.02, 0.35)
    )
    if fg3a36 >= 0.9 and fg3ar >= 0.07:
        shot_3 = max(shot_3, 5.0)
    if fg3a36 >= 1.2 and fg3ar >= 0.075:
        shot_3 = max(shot_3, 15.0)
    if fg3a36 >= 2.4 and fg3ar >= 0.14:
        shot_3 = max(shot_3, 20.0)
    low_volume_assisted_penalty = (1.0 - (scale_0_100(fg3a36, 2.2, 7.5) / 100.0)) * (
        scale_0_100(assisted3, 0.70, 0.95) / 100.0
    )
    if fg3a36 >= 2.0:
        shot_3 *= 1.0 - 0.18 * low_volume_assisted_penalty

    # pullup_3 fields are often sparse; infer conservative fallback signals when missing.
    unassisted3_share = clamp(1.0 - assisted3, 0.0, 1.0)
    pullup3_fallback_freq_base = (
        0.45 * unassisted3_share
        + 0.30 * clamp((usg - 15.0) / 20.0, 0.0, 1.0)
        + 0.15 * clamp((fg3a36 - 2.0) / 8.0, 0.0, 1.0)
        + 0.10 * clamp((avg_dist - 11.0) / 10.0, 0.0, 1.0)
    ) * 0.15
    pullup3_creator_bonus = 0.025 * (
        scale_0_100(stepback_freq, 0.04, 0.20) / 100.0
    ) + 0.015 * (scale_0_100(fg3a36, 3.0, 10.5) / 100.0)
    pullup3_fallback_freq = clamp(
        pullup3_fallback_freq_base + pullup3_creator_bonus, 0.0, 0.22
    )
    pullup3_fallback_pct = clamp((0.75 * three_pct) + (0.25 * 0.33), 0.20, 0.48)

    used_pullup3_freq = pullup3_freq
    used_pullup3_pct = pullup3_pct
    used_pullup3_fallback = False
    if used_pullup3_freq <= 0.0001:
        used_pullup3_freq = pullup3_fallback_freq
        used_pullup3_fallback = True
    if used_pullup3_pct <= 0.0001:
        used_pullup3_pct = pullup3_fallback_pct
        used_pullup3_fallback = True

    shot_3_soft_cap_power = clamp(
        (
            0.30 * soft_cap_power
            + 0.70
            * clamp(
                (
                    0.45 * scale_0_100(fg3a36, 2.0, 14.0)
                    + 0.25 * scale_0_100(three_pct, 0.30, 0.45)
                    + 0.15 * scale_0_100(fg3ar, 0.12, 0.75)
                    + 0.15 * scale_0_100(stepback_freq + used_pullup3_freq, 0.02, 0.20)
                    - 50.0
                )
                / 40.0,
                0.0,
                1.0,
            )
        ),
        0.0,
        1.0,
    )
    low_three_usage_penalty = (1.0 - (scale_0_100(fg3a36, 2.2, 8.5) / 100.0)) * (
        1.0 - (scale_0_100(1.0 - assisted3, 0.18, 0.70) / 100.0)
    )
    if fg3a36 >= 2.0:
        shot_3 *= 1.0 - 0.14 * low_three_usage_penalty
    # Non-guards who are mostly assisted spot-up threats should not max generic Shot 3 tendency.
    if (not is_guard) and assisted3 >= 0.72:
        if fg3a36 < 6.0:
            shot_3 = min(shot_3, 35.0)
        elif fg3a36 < 8.0:
            shot_3 = min(shot_3, 40.0)
    spot_up_3 = (
        0.24 * scale_0_100(assisted3, 0.20, 0.98)
        + 0.22 * scale_0_100(pt_spot_up_poss, 0.02, 0.35)
        + 0.16 * scale_0_100(catch_shoot_fg3a_pg, 0.5, 6.0)
        + 0.12 * scale_0_100(fg3ar, 0.10, 0.80)
        + 0.10 * scale_0_100(catch_shoot_fg3_pct, 0.28, 0.44)
        + 0.10 * scale_0_100(shot_dash_zero_drib_freq, 0.30, 0.85)
        + 0.06 * scale_0_100(shot_dash_zero_drib_fg_pct, 0.35, 0.55)
    )
    three_volume_signal = 0.60 * scale_0_100(fg3a36, 1.2, 11.0) + 0.40 * scale_0_100(
        fg3ar, 0.12, 0.70
    )
    spot_up_3 *= 0.55 + 0.45 * (three_volume_signal / 100.0)
    if fg3a36 < 2.0 and fg3ar < 0.15:
        spot_up_3 *= 0.72
    if fg3a36 < 1.4 and fg3ar < 0.11:
        spot_up_3 *= 0.55
    if assisted3 > 0.85 and fg3a36 < 2.8:
        spot_up_3 *= 0.85
    if fg3a36 >= 2.0:
        spot_up_3 *= 1.0 - 0.22 * low_volume_assisted_penalty
    off_screen_three_movement = (0.65 * pullup_freq) + (0.35 * used_pullup3_freq)
    creator_three_signal = (
        0.40 * scale_0_100(fg3a36, 3.0, 11.0)
        + 0.30 * scale_0_100(1.0 - assisted3, 0.20, 0.75)
        + 0.30 * scale_0_100(stepback_freq + off_screen_three_movement, 0.04, 0.32)
    )
    creator_three_boost = 0.90 + 0.10 * (creator_three_signal / 100.0)
    off_screen_3 = (
        0.30 * scale_0_100(pt_off_screen_poss, 0.01, 0.15)
        + 0.25 * scale_0_100(stepback_freq + off_screen_three_movement, 0.00, 0.30)
        + 0.25 * scale_0_100(fg3a36, 1.0, 12.0)
        + 0.20 * scale_0_100(1.0 - assisted3, 0.02, 0.65)
    )
    off_screen_3 *= 0.45 + 0.55 * (three_volume_signal / 100.0)
    if fg3ar < 0.22 and fg3a36 < 3.0:
        off_screen_3 *= 0.65
    if assisted3 > 0.80 and fg3a36 < 4.0:
        off_screen_3 *= 0.80
    if used_pullup3_fallback:
        inferred_off_screen_3_cap = (
            15.0
            + 20.0 * (scale_0_100(fg3a36, 2.0, 10.0) / 100.0)
            + 15.0 * (scale_0_100(assisted3, 0.35, 0.90) / 100.0)
        )
        off_screen_3 = min(off_screen_3, inferred_off_screen_3_cap)
        if (
            is_guard
            and fg3a36 >= 3.0
            and pullup_freq >= 0.20
            and stepback_freq >= 0.10
            and assisted3 <= 0.45
        ):
            off_screen_3 = max(off_screen_3, 22.0)
    contested_mid = (
        0.28 * scale_0_100(1.0 - assisted2, 0.05, 0.70)
        + 0.20 * scale_0_100(scoring_pct_uast_2pm, 0.10, 0.70)
        + 0.17 * scale_0_100(usg, 10, 35)
        + 0.15 * scale_0_100(mid_share + long_mid_share, 0.05, 0.40)
        + 0.12 * scale_0_100(shot_dash_contested_freq, 0.10, 0.55)
        + 0.08 * scale_0_100(max(0.0, shot_dash_contested_delta + 0.20), 0.0, 0.20)
    )
    contested_mid_creator_signal = (
        0.45 * scale_0_100(1.0 - assisted2, 0.15, 0.80)
        + 0.30 * scale_0_100(usg, 15.0, 34.0)
        + 0.25 * scale_0_100(stepback_freq + pullup_freq, 0.02, 0.22)
    )
    contested_mid *= 0.50 + 0.50 * (contested_mid_creator_signal / 100.0)
    if contested_mid_creator_signal < 45.0:
        contested_mid = min(contested_mid, 35.0)
    if usg < 24.0 and stepback_freq < 0.08:
        contested_mid = min(contested_mid, 35.0)
    if usg < 20.0 and stepback_freq < 0.06:
        contested_mid = min(contested_mid, 30.0)
    if usg < 20.0 and ast_pct < 28.0 and stepback_freq < 0.12:
        contested_mid = min(contested_mid, 35.0)
    mid_diet = mid_share + long_mid_share
    if mid_diet < 0.16:
        contested_mid = min(contested_mid, 35.0)
    if mid_diet < 0.10:
        contested_mid = min(contested_mid, 30.0)
    contested_3 = (
        0.28 * scale_0_100(1.0 - assisted3, 0.02, 0.65)
        + 0.20 * scale_0_100(scoring_pct_uast_3pm, 0.05, 0.65)
        + 0.15 * scale_0_100(usg, 10, 35)
        + 0.15 * scale_0_100(fg3a36, 2.0, 12.0)
        + 0.12 * scale_0_100(shot_dash_contested_freq, 0.10, 0.55)
        + 0.10 * scale_0_100(max(0.0, shot_dash_contested_delta + 0.20), 0.0, 0.20)
    )
    contested_3 *= 0.45 + 0.55 * (three_volume_signal / 100.0)
    contested_3 *= creator_three_boost
    step_back_mid = 0.70 * scale_0_100(stepback_freq, 0.00, 0.10) + 0.30 * scale_0_100(
        1.0 - assisted2, 0.05, 0.70
    )
    step_back_mid_creator_signal = (
        0.50 * scale_0_100(stepback_freq, 0.02, 0.16)
        + 0.30 * scale_0_100(pullup_freq, 0.02, 0.22)
        + 0.20 * scale_0_100(usg, 15.0, 34.0)
    )
    step_back_mid *= 0.45 + 0.55 * (step_back_mid_creator_signal / 100.0)
    if stepback_freq < 0.045:
        step_back_mid = min(step_back_mid, 35.0)
    if stepback_freq < 0.03:
        step_back_mid = min(step_back_mid, 30.0)
    if usg < 24.0 and stepback_freq < 0.08:
        step_back_mid = min(step_back_mid, 35.0)
    if usg < 20.0 and stepback_freq < 0.06:
        step_back_mid = min(step_back_mid, 30.0)
    if usg < 20.0 and ast_pct < 28.0 and stepback_freq < 0.12:
        step_back_mid = min(step_back_mid, 35.0)
    step_back_3 = 0.75 * scale_0_100(stepback_freq, 0.00, 0.10) + 0.25 * scale_0_100(
        1.0 - assisted3, 0.02, 0.65
    )
    step_back_3 *= 0.45 + 0.55 * (three_volume_signal / 100.0)
    step_back_3 *= creator_three_boost

    # Keep off-the-dribble perimeter shot tendencies consistent with base 3PT shot profile.
    if shot_3 < 10.0 or fg3a36 < 1.0:
        contested_3 = min(contested_3, 10.0)
        step_back_3 = min(step_back_3, 5.0)
    elif shot_3 < 20.0 or fg3a36 < 2.0:
        contested_3 = min(contested_3, 20.0)
        step_back_3 = min(step_back_3, 10.0)
    spin_jumper = 0.65 * scale_0_100(fade_freq, 0.00, 0.10) + 0.35 * scale_0_100(
        mid_share, 0.02, 0.20
    )
    transition_pullup_3 = (
        0.35 * scale_0_100(used_pullup3_freq, 0.00, 0.15)
        + 0.30 * scale_0_100(fg3a36, 1.0, 11.0)
        + 0.20 * scale_0_100(transition_poss_pct, 0.05, 0.30)
        + 0.15 * scale_0_100(transition_score_pct, 0.30, 0.70)
    )
    transition_pullup_3 *= 0.45 + 0.55 * (three_volume_signal / 100.0)
    transition_pullup_3 *= creator_three_boost

    if used_pullup3_fallback:
        # Conservative mapping when we infer pull-up profile from secondary signals.
        dribble_pullup_3 = (
            0.65 * scale_0_100(used_pullup3_freq, 0.015, 0.20)
            + 0.20 * scale_0_100(used_pullup3_pct, 0.26, 0.44)
            + 0.15 * scale_0_100(shot_dash_off_dribble_freq, 0.05, 0.40)
        )
    else:
        dribble_pullup_3 = (
            0.50 * scale_0_100(used_pullup3_freq, 0.01, 0.20)
            + 0.28 * scale_0_100(used_pullup3_pct, 0.22, 0.44)
            + 0.22 * scale_0_100(shot_dash_off_dribble_freq, 0.05, 0.40)
        )
    dribble_pullup_3 *= 0.45 + 0.55 * (three_volume_signal / 100.0)
    dribble_pullup_3 *= creator_three_boost
    if usg < 18.0 and assisted3 >= 0.60:
        dribble_pullup_3 = min(dribble_pullup_3, 15.0)
    if usg < 16.0:
        dribble_pullup_3 = min(dribble_pullup_3, 10.0)
    dribble_pullup_mid = 0.65 * scale_0_100(
        pullup_freq + fade_freq, 0.00, 0.20
    ) + 0.35 * scale_0_100(mid_share + long_mid_share, 0.02, 0.45)
    dribble_pullup_mid_creator_signal = (
        0.45 * scale_0_100(pullup_freq + fade_freq, 0.03, 0.24)
        + 0.30 * scale_0_100(1.0 - assisted2, 0.15, 0.80)
        + 0.25 * scale_0_100(usg, 15.0, 34.0)
    )
    dribble_pullup_mid *= 0.48 + 0.52 * (dribble_pullup_mid_creator_signal / 100.0)
    if (not is_guard) and pullup_freq < 0.14:
        dribble_pullup_mid *= 0.80
    drive_creation_signal = (
        0.30 * scale_0_100(tracking_drives_pg, 2.0, 22.0)
        + 0.25 * scale_0_100(1.0 - assisted2, 0.12, 0.80)
        + 0.18 * scale_0_100(usg, 12, 35)
        + 0.15 * scale_0_100(pullup_freq, 0.02, 0.24)
        + 0.12 * scale_0_100(fta36, 1.0, 10.0)
    )
    player_weight_lb = as_float(
        row,
        "player_info_wt",
        as_float(row, "weight_lbs", as_float(row, "weight", 0.0)),
    )
    player_height_in = as_float(row, "player_info_ht_in_in", 0.0)
    size_bump_signal = 0.55 * scale_0_100(
        player_weight_lb, 180.0, 285.0
    ) + 0.45 * scale_0_100(player_height_in, 72.0, 84.0)
    contact_finish_signal = (
        0.28 * scale_0_100(fta36, 0.8, 10.0)
        + 0.22 * scale_0_100(rim_share, 0.08, 0.75)
        + 0.16 * scale_0_100(drive_creation_signal, 20.0, 85.0)
        + 0.12 * scale_0_100(tracking_drives_pg, 2.0, 22.0)
        + 0.10 * scale_0_100(misc_pfd_pg, 1.0, 8.0)
        + 0.07 * scale_0_100(usg, 10.0, 35.0)
        + 0.05 * scale_0_100(misc_pts_paint_pg, 2.0, 18.0)
    )

    drive = (
        0.24 * scale_0_100(tracking_drives_pg, 1.0, 22.0)
        + 0.20 * scale_0_100(fta36, 0.5, 9.0)
        + 0.16 * scale_0_100(rim_share, 0.05, 0.70)
        + 0.10 * scale_0_100(scoring_pct_pts_paint, 0.10, 0.70)
        + 0.10 * scale_0_100(usg, 10, 35)
        + 0.10 * drive_creation_signal
        + 0.05 * scale_0_100(transition_poss_pct, 0.05, 0.30)
        + 0.05 * scale_0_100(misc_pts_fb_pg, 0.5, 6.0)
    )
    # Contact profile influences willingness/ability to finish through traffic on drives.
    drive += 0.10 * contact_finish_signal
    if is_guard:
        drive *= 1.06
    elif is_big:
        drive *= 0.82 + 0.22 * (drive_creation_signal / 100.0)
    else:
        drive *= 0.90 + 0.18 * (drive_creation_signal / 100.0)
    if not is_guard:
        drive *= 0.85 + 0.20 * (scale_0_100(1.0 - assisted2, 0.20, 0.80) / 100.0)
    if is_big and rim_share > 0.60 and pullup_freq < 0.05:
        drive *= 0.85
    if assisted2 > 0.75 and pullup_freq < 0.08 and usg < 20.0:
        drive *= 0.75

    spot_up_drive = (
        0.35 * scale_0_100(drive / 100.0, 0.20, 0.70)
        + 0.25 * scale_0_100(pt_spot_up_poss, 0.02, 0.35)
        + 0.20 * scale_0_100(1.0 - assisted2, 0.05, 0.70)
        + 0.20 * scale_0_100(tracking_drives_pg, 2.0, 20.0)
    )
    spot_up_drive *= 0.70 + 0.30 * (drive_creation_signal / 100.0)

    off_screen_drive = 0.55 * scale_0_100(
        drive / 100.0, 0.20, 0.70
    ) + 0.45 * scale_0_100(off_screen_3 / 100.0, 0.10, 0.50)
    off_screen_drive *= 0.65 + 0.35 * (drive_creation_signal / 100.0)
    use_glass = clamp(
        0.25 * scale_0_100(rim_share, 0.05, 0.75)
        + 0.20 * scale_0_100(close_share, 0.05, 0.50)
        + 0.20 * scale_0_100(tracking_paint_touches_pg, 2.0, 14.0)
        + 0.15 * scale_0_100(scoring_pct_pts_paint, 0.20, 0.70)
        + 0.10 * scale_0_100(1.0 - dunks_share, 0.10, 0.90)
        + 0.10 * (55.0 if is_big else 35.0),
        0.0,
        100.0,
    )
    step_through = 0.45 * scale_0_100(post_fta, 2.0, 10.0) + 0.55 * (
        52.0 if is_big else 30.0
    )
    spin_layup = (
        0.35 * scale_0_100(1.0 - assisted2, 0.10, 0.80)
        + 0.25 * scale_0_100(drive / 100.0, 0.30, 0.85)
        + 0.20 * scale_0_100(tracking_drives_pg, 2.0, 20.0)
        + 0.20 * (65.0 if is_guard else 35.0)
    )
    spin_layup *= 0.72 + 0.28 * (drive_creation_signal / 100.0)

    eurostep = (
        0.40 * scale_0_100(drive / 100.0, 0.20, 0.70)
        + 0.30 * scale_0_100(tracking_drives_pg, 2.0, 20.0)
        + 0.30 * (70.0 if is_guard else 45.0)
    )
    eurostep *= 0.80 + 0.25 * (drive_creation_signal / 100.0)

    hop_step = (
        0.30 * scale_0_100(drive / 100.0, 0.30, 0.85)
        + 0.25 * scale_0_100(tracking_drives_pg, 2.0, 20.0)
        + 0.25 * scale_0_100(post_fta, 2.0, 10.0)
        + 0.20 * (60.0 if is_guard else 40.0)
    )
    hop_step *= 0.82 + 0.23 * (drive_creation_signal / 100.0)

    if not is_guard:
        non_guard_move_signal = 0.60 * scale_0_100(
            1.0 - assisted2, 0.20, 0.80
        ) + 0.40 * scale_0_100(pullup_freq, 0.03, 0.24)
        eurostep *= 0.72 + 0.28 * (non_guard_move_signal / 100.0)
        hop_step *= 0.72 + 0.28 * (non_guard_move_signal / 100.0)

        # Compress frontcourt handle-move clustering above 30 unless creator signals are strong.
        non_guard_high_move_keep = 0.40 + 0.42 * (non_guard_move_signal / 100.0)
        eurostep = 30.0 + max(0.0, eurostep - 30.0) * non_guard_high_move_keep
        hop_step = 30.0 + max(0.0, hop_step - 30.0) * non_guard_high_move_keep

        non_guard_elite_handle = (
            drive_creation_signal >= 62.0
            and (1.0 - assisted2) >= 0.45
            and drive >= 42.0
        )
        if not non_guard_elite_handle:
            eurostep = min(eurostep, 34.0)
            hop_step = min(hop_step, 34.0)
            if is_big:
                eurostep = min(eurostep, 32.0)
                hop_step = min(hop_step, 32.0)

    floater = (
        0.40 * scale_0_100(close_share, 0.02, 0.30)
        + 0.20 * scale_0_100(drive_creation_signal, 20.0, 85.0)
        + 0.20 * scale_0_100(tracking_drives_pg, 2.0, 20.0)
        + 0.20 * (65.0 if is_guard else 25.0)
    )
    if not is_guard:
        floater_creator_signal = 0.65 * scale_0_100(
            pullup_freq, 0.03, 0.22
        ) + 0.35 * scale_0_100(1.0 - assisted2, 0.20, 0.80)
        floater *= 0.65 + 0.35 * (floater_creator_signal / 100.0)

    if is_big and drive_creation_signal < 45.0:
        spin_layup *= 0.72
        eurostep *= 0.65
        hop_step *= 0.68
        floater *= 0.70
    dunk_reliability = clamp(dunk_count / 30.0, 0.0, 1.0)
    standing_dunk_dunks_weight = 0.35 + 0.30 * dunk_reliability
    dunk_count_signal = scale_0_100(dunk_count, 10, 120)
    dunks_combined = 0.50 * scale_0_100(dunks_share, 0.00, 0.25) + 0.50 * dunk_count_signal
    standing_dunk = (
        standing_dunk_dunks_weight * dunks_combined
        + (0.35 - standing_dunk_dunks_weight * 0.35) * scale_0_100(size_bump_signal, 20.0, 90.0)
        + 0.20 * scale_0_100(scoring_pct_pts_paint, 0.15, 0.70)
    )
    if dunk_count < 5:
        standing_dunk = min(standing_dunk, 8.0)
    elif dunks_share < 0.015:
        standing_dunk = min(standing_dunk, 12.0)
    elif dunks_share < 0.03:
        standing_dunk = min(standing_dunk, 18.0)
    driving_dunk = (
        0.50 * dunks_combined
        + 0.25 * scale_0_100(drive / 100.0, 0.20, 0.70)
        + 0.25 * scale_0_100(tracking_drives_pg, 2.0, 20.0)
    )
    if dunks_share < 0.015:
        driving_dunk = min(driving_dunk, 5.0)
    elif dunks_share < 0.03:
        driving_dunk = min(driving_dunk, 15.0)
    elite_guard_athletic = (
        is_guard and dunks_share >= 0.060 and drive >= 45.0 and fta36 >= 5.0
    )
    if is_guard and drive <= 30.0 and not elite_guard_athletic:
        driving_dunk = min(driving_dunk, 30.0)
    # Athletic guard/wing floor: high drives + high FTA + meaningful dunk count
    if (is_guard or "SF" in position) and tracking_drives_pg >= 8.0 and fta36 >= 5.0 and dunk_count >= 20:
        athletic_floor = 40.0 + scale_0_100(dunk_count, 20, 80) * 0.3
        driving_dunk = max(driving_dunk, athletic_floor)
    flashy_dunk = (
        0.35 * scale_0_100(driving_dunk / 100.0, 0.35, 0.90)
        + 0.20 * scale_0_100(dunks_share, 0.02, 0.18)
        + 0.15 * scale_0_100(dunk_count, 20, 100)
        + 0.15 * scale_0_100(1.0 - assisted2, 0.20, 0.85)
        + 0.15 * scale_0_100(usg, 10, 35)
    )
    if is_guard:
        flashy_dunk += 8.0
    elif "SF" in position:
        flashy_dunk += 3.0
    elif is_big:
        flashy_dunk -= 6.0

    if dunks_share < 0.015:
        flashy_dunk *= 0.50
    elif dunks_share < 0.030:
        flashy_dunk *= 0.72
    elif dunks_share < 0.050:
        flashy_dunk *= 0.88
    # High-volume dunkers with low share due to shot volume shouldn't be penalized.
    if dunk_count >= 60 and dunks_share >= 0.020:
        flashy_dunk = max(flashy_dunk, 40.0)
    elif dunk_count >= 40 and dunks_share >= 0.025:
        flashy_dunk = max(flashy_dunk, 35.0)
    elif dunk_count >= 25 and dunks_share >= 0.030:
        flashy_dunk = max(flashy_dunk, 30.0)

    if (not is_guard) and standing_dunk >= 30.0 and driving_dunk < 45.0:
        flashy_dunk *= 0.88

    # True athletic slashers should keep a meaningful flashy profile.
    if (is_guard or "SF" in position) and driving_dunk >= 40.0 and (dunks_share >= 0.035 or dunk_count >= 30):
        flashy_dunk = max(flashy_dunk, 35.0)
    if (is_guard or "SF" in position) and driving_dunk >= 50.0 and dunk_count >= 40:
        flashy_dunk = max(flashy_dunk, 40.0)

    high_athletic_non_guard_slasher = (
        (not is_guard)
        and driving_dunk >= 42.0
        and (dunks_share >= 0.040 or dunk_count >= 50)
        and drive_creation_signal >= 45.0
    )
    if (not is_guard) and (not high_athletic_non_guard_slasher):
        flashy_dunk = min(flashy_dunk, 25.0)

    # Rim-running bigs tend to finish efficiently without many flashy self-created dunks.
    if is_big and (1.0 - assisted2) < 0.40 and pullup_freq < 0.08:
        flashy_dunk *= 0.72

    flashy_dunk_style_power = clamp(
        (
            0.15 * soft_cap_power
            + 0.85
            * clamp(
                (
                    0.15 * scale_0_100(dunks_share, 0.02, 0.18)
                    + 0.30 * scale_0_100(dunk_count, 20, 100)
                    + 0.30 * scale_0_100(driving_dunk / 100.0, 0.30, 0.85)
                    + 0.25 * scale_0_100(1.0 - assisted2, 0.20, 0.80)
                    - 20.0
                )
                / 65.0,
                0.0,
                1.0,
            )
        ),
        0.0,
        1.0,
    )
    if is_big and drive_creation_signal < 45.0:
        flashy_dunk_style_power *= 0.65
    if (is_guard or "SF" in position) and driving_dunk >= 40.0 and dunks_share >= 0.045:
        flashy_dunk_style_power = max(flashy_dunk_style_power, 0.55)
    if is_big and assisted2 > 0.60 and pullup_freq < 0.08:
        flashy_dunk = min(flashy_dunk, 22.0)
    alley_oop = (
        0.40 * scale_0_100(dunk_count, 0, 180)
        + 0.20 * scale_0_100(dunks_share, 0.01, 0.20)
        + 0.15 * (75.0 if is_big else 35.0)
        + 0.15 * scale_0_100(scoring_pct_pts_paint, 0.15, 0.70)
        + 0.10 * scale_0_100(1.0 - assisted2, 0.20, 0.80)
    )
    if dunks_share < 0.015:
        alley_oop = min(alley_oop, 10.0)
    elif dunks_share < 0.03:
        alley_oop = min(alley_oop, 15.0)
    if (is_guard or "SF" in position) and dunks_share >= 0.06 and drive >= 45.0:
        alley_oop = max(alley_oop, 40.0)
    putback = (
        0.50 * scale_0_100(orb_pct, 2.0, 16.0)
        + 0.30 * scale_0_100(dunks_share, 0.00, 0.25)
        + 0.20 * scale_0_100(misc_pts_2nd_chance_pg, 0.5, 5.0)
    )
    if dunks_share < 0.015:
        putback = min(putback, 15.0)
    crash_0_100 = (
        0.45 * contact_finish_signal
        + 0.20 * scale_0_100(orb_pct, 2.0, 16.0)
        + 0.20 * size_bump_signal
        + 0.15 * scale_0_100(dunks_share, 0.01, 0.20)
    )
    post_bump_signal = (
        0.50 * scale_0_100(post_fta, 1.5, 12.0)
        + 0.30 * scale_0_100(hook_freq + fade_freq, 0.01, 0.22)
        + 0.20 * scale_0_100(1.0 - assisted2, 0.10, 0.80)
    )
    messy_finish_signal = (
        0.40 * scale_0_100(1.0 - assisted2, 0.10, 0.85)
        + 0.28 * post_bump_signal
        + 0.20 * scale_0_100(fta36, 1.0, 10.0)
        + 0.12 * scale_0_100(dunks_share, 0.01, 0.20)
    )
    crash = 0.35 * crash_0_100

    if is_guard:
        crash *= 0.35 + 0.35 * (contact_finish_signal / 100.0)
        if player_weight_lb > 0 and player_weight_lb <= 195.0:
            crash *= 0.80
        if fta36 < 4.0:
            crash = min(crash, 10.0)
    elif "SF" in position:
        crash *= 0.72 + 0.18 * (contact_finish_signal / 100.0)
        crash = min(crash, 22.0)
    else:
        crash *= 0.86 + 0.14 * (contact_finish_signal / 100.0)

    true_bumper = (
        contact_finish_signal >= 70.0
        and size_bump_signal >= 72.0
        and (
            (
                is_big
                and player_weight_lb >= 235.0
                and rim_share >= 0.42
                and fta36 >= 6.0
            )
            or (
                ("SF" in position or "PF" in position)
                and player_weight_lb >= 220.0
                and rim_share >= 0.40
                and fta36 >= 5.8
            )
        )
    )
    zion_style_bumper = (
        ("PF" in position or "SF" in position)
        and player_weight_lb >= 245.0
        and rim_share >= 0.45
        and fta36 >= 7.5
    )
    true_bumper = true_bumper or zion_style_bumper

    crafty_non_guard = (
        (not is_guard)
        and (not true_bumper)
        and contact_finish_signal >= 50.0
        and drive_creation_signal >= 42.0
        and usg >= 20.0
    )
    if crafty_non_guard:
        crash = max(crash, 20.0)

    # Crafty physical wings can still trigger crash during attack sequences.
    crafty_wing_contact = (
        ("SF" in position or "PF" in position)
        and usg >= 20.0
        and drive >= 38.0
        and (post_bump_signal >= 48.0 or contact_finish_signal >= 56.0)
    )
    if crafty_wing_contact:
        crash = max(crash, 20.0)
        if fta36 >= 5.5 or post_bump_signal >= 62.0:
            crash = max(crash, 25.0)

    # Physical two-way wings should not collapse to very low crash values.
    physical_two_way_wing = (
        ("SF" in position or "PF" in position)
        and player_weight_lb >= 215.0
        and (stl_pct >= 1.5 or orb_pct >= 3.5)
    )
    if physical_two_way_wing:
        crash = max(crash, 15.0)

    # Mid-contact but physical crafty wings (Kawhi archetype) should not fall to 10-15.
    physical_crafty_wing = (
        ("SF" in position or "PF" in position)
        and player_weight_lb >= 220.0
        and fta36 >= 4.0
        and (post_bump_signal >= 40.0 or contact_finish_signal >= 38.0)
    )
    if physical_crafty_wing:
        crash = max(crash, 20.0)

    # Guard buckets: avoid zeros for contact-taking guards, but keep tiny guards low.
    if is_guard:
        crash = max(crash, 5.0)

        crafty_guard_contact = (
            usg >= 24.0
            and drive >= 35.0
            and (scale_0_100(1.0 - assisted2, 0.10, 0.85) >= 52.0 or fta36 >= 4.2)
        )
        if crafty_guard_contact:
            crash = max(crash, 10.0)

        big_guard_contact = (
            player_weight_lb >= 205.0
            and drive >= 45.0
            and usg >= 22.0
            and (fta36 >= 5.0 or rim_share >= 0.20)
        )
        if big_guard_contact:
            crash = max(crash, 20.0)
            if contact_finish_signal >= 62.0 or fta36 >= 6.5:
                crash = max(crash, 25.0)

        # Light guards should generally remain in the 5-10 range.
        if player_weight_lb > 0 and player_weight_lb <= 195.0:
            crash = min(crash, 10.0)

        # Non-explosive creator guards should live closer to 20 than 25.
        if (
            player_weight_lb >= 200.0
            and usg >= 24.0
            and dunks_share < 0.035
            and fta36 < 6.8
        ):
            crash = min(crash, 20.0)

        # Heavy high-FTA creators with low rim/dunk profile (Luka archetype) cap at 20.
        if (
            player_weight_lb >= 215.0
            and usg >= 28.0
            and rim_share < 0.16
            and dunks_share < 0.035
        ):
            crash = min(crash, 20.0)

        # Strong off-ball SGs should never fall to zero-style crash behavior.
        if "SG" in position and player_weight_lb >= 200.0:
            crash = max(crash, 10.0)

    # Explosive slashers/wings that attack through contact should live in 20-25.
    explosive_slasher = (
        (is_guard or "SG" in position or "SF" in position or "PF" in position)
        and drive >= 45.0
        and dunks_share >= 0.040
        and (driving_dunk >= 40.0 or fta36 >= 5.0)
    )
    if explosive_slasher:
        crash = max(crash, 20.0)
        if dunks_share >= 0.070 or driving_dunk >= 50.0:
            crash = max(crash, 25.0)

    # Power bigs should be 25-30 unless they are true max bumpers (35).
    power_big = (
        is_big and player_weight_lb >= 245.0 and (fta36 >= 5.0 or rim_share >= 0.30)
    )
    if power_big:
        crash = max(crash, 25.0)
        if player_weight_lb >= 255.0 and fta36 >= 7.0 and rim_share >= 0.40:
            crash = max(crash, 30.0)

    # Post-craft bigs/wings (Jokic/Embiid/Sabonis archetype) should reach 30.
    post_bump_big = (
        ("C" in position and "PF" not in position)
        and player_weight_lb >= 230.0
        and post_bump_signal >= 58.0
        and (post_fta >= 5.0 or hook_freq + fade_freq >= 0.10)
    )
    if post_bump_big:
        crash = max(crash, 30.0)

    # Centers who finish through traffic with craft/strength stay in the 30 lane.
    strong_messy_center = (
        ("C" in position and "PF" not in position)
        and player_weight_lb >= 235.0
        and messy_finish_signal >= 56.0
        and (post_bump_signal >= 52.0 or fta36 >= 5.2)
    )
    if strong_messy_center:
        crash = max(crash, 30.0)

    # Post hubs that attack through contact from the interior should be 30.
    center_contact_hub = (
        ("C" in position and "PF" not in position)
        and player_weight_lb >= 235.0
        and orb_pct >= 8.0
        and fta36 >= 5.0
        and (rim_share >= 0.30 or fta36 >= 5.6)
        and rim_share <= 0.55
        and contact_finish_signal <= 50.0
    )
    if center_contact_hub:
        crash = max(crash, 30.0)

    # Center floor rail: true non-stretch centers should be 30 minimum.
    is_true_center = "C" in position and "PF" not in position
    stretch_center_profile = (
        is_true_center and three_share >= 0.25 and rim_share <= 0.30 and orb_pct <= 9.0
    )
    if is_true_center:
        if stretch_center_profile:
            # Stretch centers can be lower than bruisers, but not very low.
            crash = max(crash, 20.0)
            if post_bump_signal >= 48.0 or fta36 >= 4.5:
                crash = max(crash, 25.0)
        else:
            crash = max(crash, 30.0)

    # Upright rim-runner bigs (Gobert archetype) should be 20-25, not 30+.
    upright_rim_runner_center = (
        ("C" in position and "PF" not in position)
        and assisted2 >= 0.62
        and rim_share >= 0.45
        and post_bump_signal < 50.0
        and messy_finish_signal < 56.0
    )
    if upright_rim_runner_center:
        crash = min(crash, 25.0)
        crash = max(crash, 20.0)

    # Never allow perimeter/wing players to collapse to zero crash.
    if not is_big:
        crash = max(crash, 5.0)

    # Slender scoring forwards with lower bump profile should not sit in the 20s.
    finesse_forward = (
        ("SF" in position or "PF" in position)
        and (not true_bumper)
        and player_weight_lb < 245.0
        and rim_share < 0.22
        and fta36 < 4.8
        and orb_pct < 4.0
        and post_bump_signal < 60.0
        and contact_finish_signal < 52.0
    )
    if finesse_forward:
        crash = min(crash, 15.0)

    # Very low-rim, low-boards finesse forwards (Durant archetype) should stay around 15.
    finesse_scoring_forward = (
        ("SF" in position or "PF" in position)
        and (not true_bumper)
        and rim_share < 0.15
        and fta36 < 6.0
        and orb_pct < 3.0
        and contact_finish_signal < 50.0
    )
    if finesse_scoring_forward:
        crash = min(crash, 15.0)

    if is_big and not true_bumper:
        crash = min(crash, 30.0)

    # Keep a strict 35-tier only for true forward bump monsters (Giannis/Zion archetype).
    if true_bumper:
        if "C" in position and "PF" not in position:
            crash = max(crash, 30.0)
        else:
            crash = max(crash, 35.0)

    crash = clamp(crash, 0.0, 35.0)
    drive_right = clamp(50.0 + (side_bias * 20.0), 0.0, 100.0)
    triple_pump_fake = (
        0.42 * scale_0_100(usg, 10, 35)
        + 0.33 * scale_0_100(1.0 - assisted2, 0.05, 0.75)
        + 0.25 * scale_0_100(mid_share + long_mid_share, 0.02, 0.45)
    )
    triple_jab = (
        0.45 * scale_0_100(usg, 10, 35)
        + 0.35 * scale_0_100(mid_share + long_mid_share, 0.02, 0.45)
        + 0.20 * scale_0_100(1.0 - assisted2, 0.05, 0.75)
    )

    low_usage_offball_signal = 0.55 * scale_0_100(
        1.0 - (usg / 35.0), 0.25, 0.75
    ) + 0.45 * scale_0_100(assisted2, 0.30, 0.90)
    # Triple Threat Idle: stars hold the ball longer to read the defense or take
    # their own shot; role players pass immediately to keep the ball moving.
    # Driven by USG + self-creation signal; AST% suppresses idle for pass-first players.
    tt_idle_star_signal = clamp(
        0.50 * scale_0_100(usg, 12.0, 36.0)
        + 0.30 * scale_0_100(1.0 - assisted2, 0.10, 0.85)
        + 0.20 * scale_0_100(stepback_freq + pullup_freq, 0.01, 0.25),
        0.0,
        100.0,
    )
    tt_idle_pass_suppressor = clamp(scale_0_100(ast_pct, 8.0, 40.0), 0.0, 100.0)
    triple_idle = clamp(
        remap(tt_idle_star_signal, 0.0, 100.0, 8.0, 38.0)
        - remap(tt_idle_pass_suppressor, 0.0, 100.0, 0.0, 8.0),
        5.0,
        40.0,
    )

    high_on_ball_creator_signal = clamp(
        0.45 * scale_0_100(usg, 20.0, 36.0)
        + 0.30 * scale_0_100(1.0 - assisted2, 0.15, 0.85)
        + 0.25 * scale_0_100(stepback_freq + pullup_freq, 0.02, 0.30),
        0.0,
        100.0,
    )

    # Triple Threat Shoot: how often a player shoots out of triple threat.
    # Driven purely by perimeter shooting ability — 3pt rate and spot-up frequency.
    # Non-shooters (bigs with no 3pt game) should be near-zero.
    tt_shoot_signal = clamp(
        0.45 * scale_0_100(spot_up_3 / 100.0, 0.05, 0.75)  # catch-and-shoot frequency
        + 0.35 * scale_0_100(fg3ar, 0.02, 0.55)  # overall 3pt attempt rate
        + 0.20 * scale_0_100(shot_3 / 100.0, 0.05, 0.75),  # pull-up 3 frequency
        0.0,
        100.0,
    )
    triple_shoot = remap(tt_shoot_signal, 0.0, 100.0, 3.0, 55.0)
    triple_shoot = clamp(triple_shoot, 3.0, 55.0)
    position_handle_bonus = (
        12.0 if is_guard else (6.0 if "SF" in position else (-4.0 if is_big else 0.0))
    )
    role_suppression = scale_0_100(usg, 8, 20)
    dribble_creativity = (
        0.25 * scale_0_100(pt_ball_handler_poss, 0.02, 0.25)
        + 0.22 * scale_0_100(1.0 - assisted3, 0.02, 0.75)
        + 0.20 * scale_0_100(stepback_freq + pullup_freq, 0.01, 0.30)
        + 0.18 * scale_0_100(tracking_avg_drib_per_touch, 1.0, 6.0)
        + 0.15 * scale_0_100(usg, 10, 35)
    )
    perimeter_creation_signal = (
        0.25 * scale_0_100(pt_ball_handler_poss, 0.02, 0.25)
        + 0.25 * scale_0_100(stepback_freq + pullup_freq, 0.02, 0.30)
        + 0.20 * scale_0_100(fg3a36, 1.0, 11.5)
        + 0.18 * scale_0_100(1.0 - assisted3, 0.05, 0.75)
        + 0.12 * scale_0_100(usg, 10.0, 35.0)
    )
    handle_control = (
        0.45 * scale_0_100(drive / 100.0, 0.25, 0.85)
        + 0.25 * scale_0_100(ast_pct, 5, 35)
        + 0.20 * scale_0_100(1.0 - tov_pct / 25.0, 0.10, 1.0)
        + 0.10 * scale_0_100(fta36, 1.0, 10.0)
    )

    setup_sizeup = clamp(
        0.48 * dribble_creativity
        + 0.25 * scale_0_100(1.0 - assisted3, 0.02, 0.75)
        + 0.17 * (50.0 + position_handle_bonus)
        + 0.10 * perimeter_creation_signal,
        0.0,
        100.0,
    )
    setup_hesi = clamp(
        0.40 * dribble_creativity
        + 0.35 * scale_0_100(ast_pct, 5, 35)
        + 0.25 * scale_0_100(pullup_freq, 0.01, 0.22),
        0.0,
        100.0,
    )
    no_setup_dribble = clamp(
        95.0
        - (0.55 * setup_sizeup + 0.45 * setup_hesi)
        + (10.0 * (1.0 - role_suppression / 100.0)),
        0.0,
        100.0,
    )

    drive_handle_base = clamp(
        0.55 * handle_control
        + 0.30 * dribble_creativity
        + 0.15 * (50.0 + position_handle_bonus),
        0.0,
        100.0,
    )
    drive_crossover = clamp(
        0.60 * drive_handle_base
        + 0.25 * scale_0_100(1.0 - assisted3, 0.02, 0.75)
        + 0.15 * perimeter_creation_signal,
        0.0,
        100.0,
    )
    drive_double_crossover = clamp(
        0.50 * scale_0_100(drive_crossover / 100.0, 0.25, 0.85)
        + 0.50 * scale_0_100(dribble_creativity / 100.0, 0.20, 0.85),
        0.0,
        100.0,
    )
    drive_spin = (
        0.34 * scale_0_100(spin_layup / 100.0, 0.45, 0.95)
        + 0.22 * scale_0_100(post_fta, 3.0, 12.0)
        + 0.24 * scale_0_100(drive / 100.0, 0.45, 0.95)
        + 0.20 * scale_0_100(1.0 - assisted2, 0.25, 0.85)
    )
    drive_spin *= 0.28 if is_guard else 0.22
    drive_half_spin = (
        0.42 * scale_0_100(drive_spin / 100.0, 0.08, 0.35)
        + 0.28 * scale_0_100(stepback_freq + pullup_freq, 0.03, 0.25)
        + 0.30 * scale_0_100(1.0 - assisted2, 0.25, 0.85)
    )
    drive_half_spin *= 0.24 if is_guard else 0.18
    if usg < 20.0 or drive < 35.0:
        drive_spin = min(drive_spin, 8.0)
        drive_half_spin = min(drive_half_spin, 5.0)
    drive_step_back = (
        0.40 * scale_0_100(stepback_freq, 0.00, 0.22)
        + 0.25 * scale_0_100(1.0 - assisted3, 0.02, 0.65)
        + 0.20 * scale_0_100(fg3a36, 0.5, 12.0)
        + 0.15 * scale_0_100(drive / 100.0, 0.25, 0.80)
    ) * 0.62
    drive_behind_back = (
        0.42 * scale_0_100(drive_crossover / 100.0, 0.25, 0.85)
        + 0.24 * scale_0_100(dribble_creativity / 100.0, 0.20, 0.85)
        + 0.14 * scale_0_100(usg, 10, 35)
        + 0.20 * (62.0 if is_guard else 25.0)
    )
    drive_hesitation = (
        0.35 * scale_0_100(setup_hesi / 100.0, 0.25, 0.85)
        + 0.25 * scale_0_100(handle_control / 100.0, 0.20, 0.85)
        + 0.25 * scale_0_100(pullup_freq, 0.01, 0.22)
        + 0.15 * (65.0 if is_guard else 38.0)
    )
    drive_in_out = (
        0.30 * scale_0_100(drive_hesitation / 100.0, 0.25, 0.85)
        + 0.30 * scale_0_100(ast_pct, 7, 35)
        + 0.25 * scale_0_100(1.0 - assisted3, 0.02, 0.75)
        + 0.15 * (65.0 if is_guard else 32.0)
    )

    low_creation_big_profile = (
        is_big and usg < 20.0 and ast_pct < 18.0 and (1.0 - assisted2) < 0.55
    )
    low_creation_role_profile = (
        (not is_guard) and usg < 19.0 and ast_pct < 18.0 and (1.0 - assisted2) < 0.55
    )
    if low_creation_big_profile:
        setup_sizeup = min(setup_sizeup, 20.0)
        setup_hesi = min(setup_hesi, 25.0)
        drive_crossover = min(drive_crossover, 20.0)
        drive_double_crossover = min(drive_double_crossover, 10.0)
        drive_behind_back = min(drive_behind_back, 15.0)
        drive_hesitation = min(drive_hesitation, 15.0)
        drive_in_out = min(drive_in_out, 10.0)
    elif low_creation_role_profile:
        setup_sizeup = min(setup_sizeup, 30.0)
        setup_hesi = min(setup_hesi, 35.0)
        drive_crossover = min(drive_crossover, 30.0)
        drive_double_crossover = min(drive_double_crossover, 20.0)
        drive_behind_back = min(drive_behind_back, 20.0)
        drive_hesitation = min(drive_hesitation, 25.0)
        drive_in_out = min(drive_in_out, 20.0)

    no_drive_dribble_move = clamp(
        45.0
        - 0.22 * (
            0.23 * drive_crossover
            + 0.18 * drive_double_crossover
            + 0.21 * drive_behind_back
            + 0.20 * drive_hesitation
            + 0.18 * drive_in_out
        )
        + (8.0 * (1.0 - role_suppression / 100.0)),
        20.0,
        50.0,
    )

    elite_dribble_creator = (
        (is_guard or "SF" in position)
        and usg >= 24.0
        and (dribble_creativity >= 62.0 or perimeter_creation_signal >= 64.0)
    )
    if elite_dribble_creator:
        setup_sizeup = max(setup_sizeup, 38.0)
        drive_crossover = max(drive_crossover, 35.0)
        no_setup_dribble = min(no_setup_dribble, 35.0)
        no_drive_dribble_move = min(no_drive_dribble_move, 35.0)

    if low_creation_big_profile:
        no_drive_dribble_move = max(no_drive_dribble_move, 40.0)
    attack_strong_drive = (
        0.35 * contact_finish_signal
        + 0.20 * scale_0_100(player_weight_lb, 185.0, 270.0)
        + 0.15 * scale_0_100(dunks_share, 0.02, 0.20)
        + 0.15 * scale_0_100(drive_creation_signal, 15.0, 75.0)
        + 0.05 * scale_0_100(1.0 - pullup_freq, 0.50, 0.95)
        + 0.10 * scale_0_100(scoring_pct_pts_paint, 0.15, 0.65)
    )
    if is_guard and pullup_freq > 0.15 and contact_finish_signal < 45.0:
        attack_strong_drive = max(attack_strong_drive, 25.0)
        attack_strong_drive = min(attack_strong_drive, 32.0)
    if low_creation_big_profile or (is_big and pt_post_up_poss > 0.15):
        attack_strong_drive = min(attack_strong_drive, 35.0)
    if is_big and contact_finish_signal > 50.0 and dunks_share > 0.08:
        attack_strong_drive = max(attack_strong_drive, 50.0)
    if contact_finish_signal > 55.0 and drive_creation_signal > 50.0:
        attack_strong_drive = max(attack_strong_drive, 48.0)
    if drive_creation_signal > 55.0 and usg >= 28.0:
        attack_strong_drive = max(attack_strong_drive, 38.0)
    pass_creation_signal = (
        0.40 * scale_0_100(ast_pct, 5.0, 40.0)
        + 0.25 * scale_0_100(ast100, 2.5, 14.0)
        + 0.20 * scale_0_100(1.0 - assisted2, 0.15, 0.80)
        + 0.15 * scale_0_100(usg, 10.0, 35.0)
    )
    dish = (
        0.30 * scale_0_100(ast_pct, 4, 45)
        + 0.25 * scale_0_100(tracking_drive_pass_rate, 0.10, 0.65)
        + 0.20 * scale_0_100(ast100, 2, 14)
        + 0.15 * pass_creation_signal
        + 0.10 * scale_0_100(tracking_drives_pg, 2.0, 20.0)
    )
    if ast_pct >= 40.0:
        dish = max(dish, 45.0)
    elif ast_pct >= 34.0:
        dish = max(dish, 40.0)
    elif ast_pct >= 28.0:
        dish = max(dish, 35.0)
    if is_big and ast_pct < 35.0 and pass_creation_signal < 66.0:
        dish = min(dish, 40.0)
    if is_big and ast_pct >= 5.0:
        dish = max(dish, 5.0)
    dish_soft_cap_power = max(
        soft_cap_power, 0.18 + 0.55 * (pass_creation_signal / 100.0)
    )

    flashy_pass = (
        0.30 * scale_0_100(ast_pct, 8.0, 38.0)
        + 0.20 * scale_0_100(tracking_drive_pass_rate, 0.10, 0.65)
        + 0.15 * scale_0_100(ast100, 3.0, 13.0)
        + 0.15 * scale_0_100(pt_ball_handler_poss, 0.05, 0.40)
        + 0.10 * scale_0_100(1.0 - assisted2, 0.15, 0.80)
        + 0.10 * scale_0_100(usg, 10.0, 35.0)
    )
    if ast_pct < 14.0 and ast100 < 5.0:
        flashy_pass = min(flashy_pass, 20.0)
    if is_big and ast_pct < 18.0 and pass_creation_signal < 48.0:
        flashy_pass = min(flashy_pass, 15.0)
    if ast_pct >= 30.0:
        flashy_pass = max(flashy_pass, 30.0)
    elif ast_pct >= 25.0:
        flashy_pass = max(flashy_pass, 22.0)

    alley_oop_pass = (
        0.30 * scale_0_100(ast_pct, 5.0, 38.0)
        + 0.18 * scale_0_100(ast100, 2.0, 14.0)
        + 0.15 * scale_0_100(tracking_drives_pg, 2.0, 20.0)
        + 0.12 * scale_0_100(tracking_drive_pass_rate, 0.10, 0.65)
        + 0.15 * pass_creation_signal
        + 0.10 * scale_0_100(pt_ball_handler_poss, 0.05, 0.40)
    )
    if ast_pct < 12.0:
        alley_oop_pass = min(alley_oop_pass, 10.0)
    elif ast_pct < 18.0:
        alley_oop_pass = min(alley_oop_pass, 15.0)
    elif ast_pct < 24.0:
        alley_oop_pass = min(alley_oop_pass, 20.0)
    if is_big and ast_pct < 22.0 and pass_creation_signal < 55.0:
        alley_oop_pass = min(alley_oop_pass, 15.0)
    if ast_pct >= 30.0:
        alley_oop_pass = max(alley_oop_pass, 35.0)
    elif ast_pct >= 25.0:
        alley_oop_pass = max(alley_oop_pass, 28.0)

    # Dependency rule: only players with real passing intent (Dish >= 15)
    # can use flashy or alley-oop passing tendencies.
    if dish < 15.0:
        flashy_pass = 0.0
        alley_oop_pass = 0.0
    # Lower values = pop tendency, higher values = roll tendency.
    # Roll indicators: paint activity, rim finishing, P&R roll usage.
    # Pop indicators: 3PT rate, spot-up usage, face-up play.
    roll_man_signal = scale_0_100(pt_roll_man_poss, 0.01, 0.30)
    paint_signal = scale_0_100(tracking_paint_touches_pg, 1.0, 12.0)
    rim_signal = scale_0_100(rim_share, 0.08, 0.65)
    dunk_signal = scale_0_100(dunks_share, 0.01, 0.25)
    close_signal = scale_0_100(close_share, 0.05, 0.35)
    paint_scoring_signal = scale_0_100(scoring_pct_pts_paint, 0.15, 0.70)
    # Pop penalty: only meaningful for bigs with high 3PT rate AND low paint activity.
    # Paint-dominant bigs (Bam, AD) shouldn't be penalized for occasional threes.
    # Pure stretch bigs (fg3ar > 0.50) get heavy penalty regardless.
    pop_signal = scale_0_100(fg3ar, 0.02, 0.70)
    pop_penalty = 0.0
    # Paint dominance requires sustained paint involvement, not just dunking ability.
    is_paint_dominant = (tracking_paint_touches_pg >= 6.0) or (close_share >= 0.25)
    if fg3ar >= 0.50:
        # Pure stretch bigs: heavy penalty even with some paint presence
        pop_penalty = 0.28 * pop_signal
    elif fg3ar >= 0.35 and not is_paint_dominant:
        pop_penalty = 0.24 * pop_signal
    elif fg3ar >= 0.25 and not is_paint_dominant:
        pop_penalty = 0.16 * pop_signal
    elif fg3ar >= 0.15 and not is_paint_dominant:
        pop_penalty = 0.08 * pop_signal
    # Face-up/hub bigs (moderate 3PT + mid-range, not elite rim attackers) lean pop.
    # Detected by: moderate fg3ar + low rim share. But NOT for true rim attackers.
    face_up_penalty = 0.0
    is_rim_attacker = (rim_share >= 0.40) or (close_share >= 0.25 and tracking_paint_touches_pg >= 4.0)
    if is_big and fg3ar >= 0.20 and rim_share < 0.35 and not is_rim_attacker:
        face_up_penalty = 0.22 * scale_0_100(fg3ar + as_float(row, "shooting_percent_fga_from_x10_16_range", 0.0) + as_float(row, "shooting_percent_fga_from_x16_3p_range", 0.0), 0.30, 0.70)
    # Hub bigs: high paint touches from post/short-roll play, not rim-running.
    # Detected by: high paint touches + low rim share + low dunk share.
    hub_penalty = 0.0
    if is_big and tracking_paint_touches_pg >= 5.0 and rim_share < 0.40 and dunks_share < 0.20:
        hub_penalty = 0.20 * scale_0_100(tracking_paint_touches_pg, 5.0, 10.0)
    # Reduce rim_signal weight for stretch bigs who aren't actually rim attackers.
    rim_signal_weight = 0.10
    if is_big and fg3ar >= 0.25 and rim_share < 0.50:
        rim_signal_weight = 0.04
    # Increase pop penalty for stretch bigs with moderate 3PT rate.
    # These players pop more than their paint touches suggest.
    if is_big and fg3ar >= 0.25 and fg3ar < 0.35 and not is_paint_dominant:
        pop_penalty = max(pop_penalty, 0.22 * pop_signal)
    spot_up_signal = scale_0_100(pt_spot_up_poss, 0.02, 0.30)
    roll_vs_pop_signal = clamp(
        0.12 * roll_man_signal
        + 0.18 * paint_signal
        + rim_signal_weight * rim_signal
        + 0.08 * dunk_signal
        + 0.14 * close_signal
        + 0.08 * paint_scoring_signal
        - pop_penalty
        - face_up_penalty
        - hub_penalty
        - 0.04 * spot_up_signal
        + 0.15 * (65.0 if is_big else 30.0)
        + 5.0,
        0.0,
        100.0,
    )
    # Floor: all bigs get at least some roll tendency (they roll sometimes in P&R).
    # Even pure stretch bigs roll occasionally.
    if is_big and roll_vs_pop_signal < 20.0:
        roll_vs_pop_signal = 20.0 + 0.5 * (roll_vs_pop_signal / 20.0) * 10.0
    # Floor for paint-dominant rollers: bigs with high close+dunk share should
    # roll at least moderately even if paint_touches are understated.
    # But NOT for hub bigs who get hub_penalty.
    if is_big and close_share >= 0.25 and dunks_share >= 0.08 and roll_vs_pop_signal < 45.0 and hub_penalty < 5.0:
        roll_vs_pop_signal = 45.0 + 0.5 * (roll_vs_pop_signal - 25.0)
    # Custom gameplay ladder for Roll vs Pop:
    # 0-10 strong pop, 15-25 strong pop bias, 30-40 balanced lean-pop,
    # 45-55 balanced lean-roll, 60-65 strong roll.
    if roll_vs_pop_signal <= 15.0:
        roll_vs_pop = remap(roll_vs_pop_signal, 0.0, 15.0, 0.0, 10.0)
    elif roll_vs_pop_signal <= 30.0:
        roll_vs_pop = remap(roll_vs_pop_signal, 15.0, 30.0, 15.0, 25.0)
    elif roll_vs_pop_signal <= 45.0:
        roll_vs_pop = remap(roll_vs_pop_signal, 30.0, 45.0, 30.0, 45.0)
    elif roll_vs_pop_signal <= 60.0:
        roll_vs_pop = remap(roll_vs_pop_signal, 45.0, 60.0, 50.0, 60.0)
    else:
        roll_vs_pop = remap(roll_vs_pop_signal, 60.0, 100.0, 60.0, 65.0)
    # Spot vs Cut: higher = more spot-up, lower = more cutting.
    cut_direct_signal = scale_0_100(pt_cut_poss, 0.02, 0.20)
    spot_vs_cut = clamp(
        50.0
        + (scale_0_100(fg3ar, 0.02, 0.70) - 50.0) * 0.55
        - (cut_direct_signal - 50.0) * 0.35
        - (scale_0_100(rim_share, 0.05, 0.75) - 50.0) * 0.30,
        0.0,
        100.0,
    )
    iso_creation = (
        0.25 * scale_0_100(pt_iso_poss, 0.01, 0.18)
        + 0.20 * scale_0_100(1.0 - assisted2, 0.10, 0.80)
        + 0.18 * scale_0_100(1.0 - assisted3, 0.02, 0.65)
        + 0.17 * scale_0_100(stepback_freq + pullup_freq, 0.02, 0.30)
        + 0.12 * scale_0_100(usg, 10, 35)
        + 0.08 * scale_0_100(drive / 100.0, 0.25, 0.80)
    )
    iso_playmaker_penalty = 0.35 * scale_0_100(ast_pct, 8, 40)
    iso_size_penalty = 10.0 if is_big else (4.0 if "SF" in position else 0.0)
    iso_base = clamp(
        iso_creation - iso_playmaker_penalty - iso_size_penalty, 0.0, 100.0
    )

    iso_vs_elite = iso_base * 0.38
    iso_vs_good = iso_base * 0.48
    iso_vs_average = iso_base * 0.54
    iso_vs_poor = iso_base * 0.58

    # Superstar-aware floors keep elite creators active in ISO without over-forcing poor-matchup spam.
    superstar_score = (
        0.45 * scale_0_100(usg, 14, 36)
        + 0.25 * scale_0_100(1.0 - assisted2, 0.10, 0.80)
        + 0.20 * scale_0_100(stepback_freq + pullup_freq, 0.02, 0.30)
        + 0.10 * scale_0_100(drive / 100.0, 0.25, 0.85)
    )
    # Keep centers in a slightly lower band than perimeter/wing superstars.
    iso_superstar_lane = (
        ("C" not in position) and superstar_score >= 65 and iso_creation >= 35
    )
    if iso_superstar_lane:
        iso_floors = (25.0, 35.0, 45.0, 50.0)
    elif superstar_score >= 65:
        iso_floors = (15.0, 25.0, 35.0, 45.0)
    elif superstar_score >= 50:
        iso_floors = (10.0, 20.0, 30.0, 40.0)
    else:
        iso_floors = (5.0, 10.0, 15.0, 20.0)

    # Low-creation bigs should still occasionally ISO poor defenders out of post seals.
    low_creation_big = (
        is_big
        and usg < 22.0
        and fg3ar < 0.15
        and (("C" in position) or (iso_creation < 35.0))
    )
    if low_creation_big:
        iso_floors = (
            max(iso_floors[0], 5.0),
            max(iso_floors[1], 10.0),
            max(iso_floors[2], 15.0),
            max(iso_floors[3], 25.0),
        )

    iso_vs_elite = max(iso_vs_elite, iso_floors[0])
    iso_vs_good = max(iso_vs_good, iso_floors[1])
    iso_vs_average = max(iso_vs_average, iso_floors[2])
    iso_vs_poor = max(iso_vs_poor, iso_floors[3])
    ast_to_tov = ast100 / max(tov_pct * 0.1, 0.1)
    play_discipline = clamp(
        0.35 * scale_0_100(1.0 - tov_pct / 25.0, 0.05, 0.90)
        + 0.25 * scale_0_100(ast_to_tov, 1.0, 5.0)
        + 0.15 * scale_0_100(ast_pct, 5, 40)
        + 0.15 * scale_0_100(pt_spot_up_poss + pt_cut_poss, 0.05, 0.40)
        + 0.10 * (55.0 - scale_0_100(usg, 10, 35) * 0.3),
        0.0,
        100.0,
    )
    if usg >= 31.0 and ast_pct >= 24.0 and tov_pct <= 17.0:
        play_discipline = max(play_discipline, 35.0)
    play_discipline_power = clamp(
        0.50 * scale_0_100(ast_to_tov, 2.0, 14.0) / 100.0
        + 0.30 * scale_0_100(1.0 - tov_pct / 25.0, 0.50, 0.95) / 100.0
        + 0.20 * scale_0_100(ast_pct, 5, 45) / 100.0,
        0.0,
        1.0,
    )

    post_anchor = (
        0.30 * scale_0_100(pt_post_up_poss, 0.01, 0.18)
        + 0.25 * scale_0_100(post_fta, 1.5, 12.0)
        + 0.20 * scale_0_100(1.0 - fg3ar, 0.20, 1.00)
        + 0.15 * scale_0_100(hook_freq, 0.00, 0.12)
        + 0.10 * (70.0 if is_big else 35.0)
    )
    post_craft = (
        0.24 * scale_0_100(fade_freq, 0.00, 0.18)
        + 0.22 * scale_0_100(mid_share + long_mid_share, 0.03, 0.45)
        + 0.19 * scale_0_100(pt_post_up_fg, 0.30, 0.55)
        + 0.13 * scale_0_100(1.0 - assisted2, 0.08, 0.80)
        + 0.12 * scale_0_100(elbow_touches_pg, 0.5, 6.0)
        + 0.10 * scale_0_100(usg, 10, 35)
    )
    post_power = (
        0.45 * scale_0_100(post_fta, 1.5, 12.0)
        + 0.25 * scale_0_100(rim_share, 0.10, 0.75)
        + 0.15 * scale_0_100(dunks_share, 0.00, 0.22)
        + 0.15 * (75.0 if is_big else 30.0)
    )

    post_profile = 0.62 * post_anchor + 0.38 * post_craft
    if is_guard:
        guard_true_post_signal = (
            0.35 * scale_0_100(hook_freq, 0.00, 0.12)
            + 0.25 * scale_0_100(fade_freq, 0.00, 0.18)
            + 0.25 * scale_0_100(1.0 - assisted2, 0.08, 0.80)
            + 0.15 * scale_0_100(post_fta, 1.5, 11.0)
        )
        guard_post_factor = (
            0.18
            + 0.34 * (guard_true_post_signal / 100.0)
            + 0.22 * (scale_0_100(usg, 18.0, 36.0) / 100.0)
            + 0.26 * (scale_0_100(1.0 - fg3ar, 0.20, 0.95) / 100.0)
        )
        if ("PG" in position) and post_fta < 6.0:
            guard_post_factor *= 0.88
        if ("PG" in position) and guard_true_post_signal < 38.0:
            guard_post_factor *= 0.82
        post_profile *= guard_post_factor

        # Differentiate true guard post craft (hooks) from pure foul-draw post touches.
        post_profile += 8.0 * (scale_0_100(hook_freq, 0.01, 0.08) / 100.0)
        if hook_freq < 0.02 and post_fta > 7.5 and usg < 34.0:
            post_profile *= 0.88
        if (
            ("PG" in position)
            and usg >= 35.0
            and post_fta >= 10.0
            and (1.0 - assisted2) >= 0.80
        ):
            post_profile += 5.0
    elif ("SF" in position) and post_fta < 5.0 and hook_freq < 0.02:
        post_profile *= 0.78
    post_hook_left = clamp(
        0.40 * scale_0_100(hook_freq, 0.00, 0.12)
        + 0.15 * scale_0_100(pt_post_up_poss, 0.01, 0.18)
        + 0.15 * scale_0_100(tracking_paint_touches_pg, 2.0, 14.0)
        + 0.10 * scale_0_100(post_fta, 1.5, 10.0)
        + 0.10 * scale_0_100(0.5 + side_bias * 0.5, 0.0, 1.0)
        + 0.10 * (55.0 if is_big else 30.0),
        0.0,
        100.0,
    )
    post_hook_right = clamp(
        0.40 * scale_0_100(hook_freq, 0.00, 0.12)
        + 0.15 * scale_0_100(pt_post_up_poss, 0.01, 0.18)
        + 0.15 * scale_0_100(tracking_paint_touches_pg, 2.0, 14.0)
        + 0.10 * scale_0_100(post_fta, 1.5, 10.0)
        + 0.10 * scale_0_100(0.5 - side_bias * 0.5, 0.0, 1.0)
        + 0.10 * (55.0 if is_big else 30.0),
        0.0,
        100.0,
    )
    if (not is_big) and hook_freq < 0.04:
        post_hook_left *= 0.65
        post_hook_right *= 0.65
    if is_guard:
        if hook_freq < 0.03:
            post_hook_left = min(post_hook_left, 25.0)
            post_hook_right = min(post_hook_right, 25.0)
        else:
            post_hook_left = min(post_hook_left, 35.0)
            post_hook_right = min(post_hook_right, 35.0)
    post_back_down = 0.62 * scale_0_100(post_power / 100.0, 0.20, 0.90) + 0.38 * (
        72.0 if is_big else 25.0
    )
    post_aggressive_back_down = clamp(
        0.30 * scale_0_100(post_fta, 1.5, 12.0)
        + 0.20 * scale_0_100(rim_share, 0.10, 0.75)
        + 0.20 * scale_0_100(tracking_paint_touches_pg, 2.0, 14.0)
        + 0.15 * scale_0_100(pt_post_up_fg, 0.30, 0.55)
        + 0.15 * scale_0_100(dunks_share, 0.00, 0.22),
        0.0,
        100.0,
    )
    post_face_up = (
        0.55 * post_craft
        + 0.25 * scale_0_100(usg, 10, 35)
        + 0.20 * (35.0 if is_big else 50.0)
    )
    post_spin = (
        0.45 * scale_0_100(hook_freq + fade_freq, 0.00, 0.22)
        + 0.30 * scale_0_100(post_anchor / 100.0, 0.20, 0.90)
        + 0.25 * scale_0_100(post_craft / 100.0, 0.20, 0.90)
    )
    post_drive = (
        0.45 * scale_0_100(drive / 100.0, 0.25, 0.90)
        + 0.35 * scale_0_100(post_face_up / 100.0, 0.20, 0.90)
        + 0.20 * (35.0 if is_big else 55.0)
    )
    post_drop_step = clamp(
        0.30 * scale_0_100(rim_share, 0.10, 0.75)
        + 0.20 * scale_0_100(dunks_share, 0.00, 0.22)
        + 0.20 * scale_0_100(pt_post_up_poss, 0.01, 0.18)
        + 0.15 * scale_0_100(tracking_paint_touches_pg, 2.0, 14.0)
        + 0.15 * scale_0_100(post_fta, 1.5, 12.0),
        0.0,
        100.0,
    )
    shoot_from_post = (
        0.45 * scale_0_100(post_face_up / 100.0, 0.20, 0.90)
        + 0.35 * scale_0_100(mid_share + long_mid_share, 0.03, 0.45)
        + 0.20 * scale_0_100(elbow_touch_fg_pct, 0.35, 0.55)
    )
    post_fade_left = clamp(
        0.40 * scale_0_100(fade_freq, 0.00, 0.18)
        + 0.20 * scale_0_100(post_craft / 100.0, 0.20, 0.90)
        + 0.15 * scale_0_100(elbow_touches_pg, 0.5, 6.0)
        + 0.15 * scale_0_100(mid_share + long_mid_share, 0.03, 0.45)
        + 0.10 * scale_0_100(0.5 + side_bias * 0.5, 0.0, 1.0),
        0.0,
        100.0,
    )
    if is_guard:
        post_fade_left = max(post_fade_left, min(40.0, post_hook_left + 10.0))
    post_fade_right = clamp(
        0.40 * scale_0_100(fade_freq, 0.00, 0.18)
        + 0.20 * scale_0_100(post_craft / 100.0, 0.20, 0.90)
        + 0.15 * scale_0_100(elbow_touches_pg, 0.5, 6.0)
        + 0.15 * scale_0_100(mid_share + long_mid_share, 0.03, 0.45)
        + 0.10 * scale_0_100(0.5 - side_bias * 0.5, 0.0, 1.0),
        0.0,
        100.0,
    )
    post_shimmy = clamp(
        0.25 * scale_0_100(usg, 10, 35)
        + 0.20 * scale_0_100(pt_post_up_fg, 0.30, 0.55)
        + 0.20 * scale_0_100(fade_freq, 0.00, 0.18)
        + 0.15 * scale_0_100(stepback_freq, 0.00, 0.18)
        + 0.10 * scale_0_100(tracking_paint_touches_pg, 2.0, 14.0)
        + 0.10 * (50.0 if is_big else 30.0),
        0.0,
        100.0,
    )
    post_hop_shot = clamp(
        0.25 * scale_0_100(post_fade_left / 100.0, 0.20, 0.90)
        + 0.25 * scale_0_100(stepback_freq, 0.00, 0.18)
        + 0.20 * scale_0_100(mid_share + long_mid_share, 0.03, 0.45)
        + 0.15 * scale_0_100(elbow_touch_fg_pct, 0.35, 0.55)
        + 0.15 * scale_0_100(tracking_paint_touches_pg, 2.0, 14.0),
        0.0,
        100.0,
    )
    post_step_back = (
        0.40 * scale_0_100(stepback_freq, 0.00, 0.18)
        + 0.35 * scale_0_100(post_face_up / 100.0, 0.20, 0.90)
        + 0.25 * scale_0_100(1.0 - assisted2, 0.08, 0.80)
    )
    post_up_under = (
        0.45 * scale_0_100(post_spin / 100.0, 0.20, 0.90)
        + 0.35 * scale_0_100(post_drive / 100.0, 0.20, 0.90)
        + 0.20 * scale_0_100(hook_freq + fade_freq, 0.00, 0.22)
    )

    low_post_craft = (hook_freq + fade_freq) < 0.05 and post_fta < 4.5
    if low_post_craft:
        shoot_from_post *= 0.75
        post_fade_left *= 0.70
        post_fade_right *= 0.70
        post_shimmy *= 0.65
        post_hop_shot *= 0.68
        post_step_back *= 0.70

    if is_guard and low_post_craft:
        post_hop_shot = min(post_hop_shot, 25.0)
        post_step_back = min(post_step_back, 25.0)

    if is_big and hook_freq < 0.02 and fade_freq < 0.04 and post_fta < 5.5:
        post_face_up *= 0.80
        post_hop_shot *= 0.70
        post_step_back *= 0.65

    true_post_craft_star = (
        fade_freq >= 0.08 and post_fta >= 6.0 and (mid_share + long_mid_share) >= 0.12
    )
    if true_post_craft_star:
        post_fade_left = max(post_fade_left, 38.0)
        post_fade_right = max(post_fade_right, 38.0)

    low_post_role = (
        post_fta < 3.2 and hook_freq < 0.015 and fade_freq < 0.03 and usg < 22.0
    )
    if low_post_role:
        suppression = 0.60 if is_big else 0.50
        post_profile *= suppression
        post_hook_left *= suppression
        post_hook_right *= suppression
        post_back_down *= suppression
        post_aggressive_back_down *= suppression
        post_spin *= suppression
        post_drop_step *= suppression
        post_up_under *= suppression
        post_drive *= 0.75
    pf100 = as_float(row, "per_100_pf_per_100_poss")
    stl100 = as_float(row, "per_100_stl_per_100_poss")
    blk100 = as_float(row, "per_100_blk_per_100_poss")
    lost_ball_forced = as_float(row, "play_by_play_lost_ball_turnover")
    minutes = as_float(row, "totals_mp")

    defense_involvement = scale_0_100(minutes, 350, 2900)
    perimeter_defense = (
        0.30 * scale_0_100(stl_pct, 0.3, 3.8)
        + 0.22 * scale_0_100(stl100, 0.5, 4.2)
        + 0.20 * scale_0_100(defense_dash_3pt_stop, -0.05, 0.08)
        + 0.15 * scale_0_100(hustle_contested_3pt_pg, 0.5, 5.0)
        + 0.13 * scale_0_100(lost_ball_forced, 0, 95)
    )
    rim_defense = (
        0.30 * scale_0_100(blk_pct, 0.2, 10.0)
        + 0.25 * scale_0_100(defense_dash_lt6_stop, -0.05, 0.10)
        + 0.20 * scale_0_100(hustle_contested_2pt_pg, 1.0, 10.0)
        + 0.15 * scale_0_100(blk100, 0.2, 5.2)
        + 0.10 * scale_0_100(contest_proxy, 2, 130)
    )

    foul = clamp(
        scale_0_100(pf100, 1.5, 6.3) * 0.45
        + scale_0_100(hustle_contested_shots_pg, 1.0, 14.0) * 0.15
        + scale_0_100(deflections_pg, 0.5, 4.5) * 0.10
        + scale_0_100(defense_involvement, 5.0, 100.0) * 0.10
        + (50.0 if is_big else 35.0) * 0.10
        + 10.0,
        10.0,
        100.0,
    )
    hard_foul = clamp(
        scale_0_100(hard_foul_proxy, 0.3, 3.0) * 0.35
        + scale_0_100(lost_ball_forced, 0, 95) * 0.20
        + scale_0_100(stl_pct, 0.3, 3.8) * 0.15
        + scale_0_100(blk_pct, 0.3, 5.0) * 0.15
        + scale_0_100(defense_involvement, 5.0, 100.0) * 0.10
        + (55.0 if is_big else 30.0) * 0.05
        + 5.0,
        5.0,
        100.0,
    )

    charge_iq = (
        0.60 * scale_0_100(charges_drawn_pg, 0.00, 0.35)
        + 0.18 * scale_0_100(1.0 - (pf100 / 7.0), 0.15, 1.0)
        + 0.14 * scale_0_100(stl_pct, 0.3, 3.8)
        + 0.08 * (65.0 if is_big else 45.0)
    )
    take_charge = clamp(charge_iq, 0.0, 100.0)
    if charges_drawn_pg < 0.03:
        take_charge = min(take_charge, 30.0)
    elif charges_drawn_pg < 0.08:
        take_charge = min(take_charge, 35.0)
    elif charges_drawn_pg < 0.15:
        take_charge = min(take_charge, 40.0)
    if (not is_big) and usg >= 28.0 and ast_pct >= 24.0 and charges_drawn_pg < 0.10:
        take_charge = min(take_charge, 35.0)

    pass_interception = clamp(
        0.44 * scale_0_100(stl_pct, 0.5, 3.2)
        + 0.28 * scale_0_100(deflections_pg, 0.4, 3.8)
        + 0.16 * scale_0_100(stl100, 0.5, 4.2)
        + 0.12 * scale_0_100(1.0 - (pf100 / 7.0), 0.15, 1.0),
        0.0,
        100.0,
    )
    on_ball_steal = clamp(
        0.70 * perimeter_defense
        + 0.20 * scale_0_100(lost_ball_forced, 0, 95)
        + 0.10 * scale_0_100(usg, 10, 35),
        0.0,
        100.0,
    )
    block = clamp(0.76 * rim_defense + 0.24 * (70.0 if is_big else 20.0), 0.0, 100.0)
    contest_shot = clamp(
        0.30 * scale_0_100(hustle_contested_shots_pg, 2.0, 14.0)
        + 0.25 * rim_defense
        + 0.20 * scale_0_100(defense_dash_overall_stop, -0.03, 0.08)
        + 0.15 * perimeter_defense
        + 0.10 * scale_0_100(defense_involvement, 20.0, 100.0),
        0.0,
        100.0,
    )

    if not is_big:
        non_big_block_cap = remap(blk_pct, 0.3, 2.2, 18.0, 36.0)
        block = min(block, non_big_block_cap)
        if blk_pct < 1.1:
            contest_shot = min(contest_shot, 35.0)
        else:
            contest_shot = min(contest_shot, remap(blk_pct, 1.1, 2.5, 30.0, 42.0))

    if stl_pct < 1.4 and deflections_pg < 1.5:
        pass_interception = min(pass_interception, 35.0)
    elif stl_pct < 2.0 and deflections_pg < 2.2:
        pass_interception = min(pass_interception, 40.0)

    disruption_signal = (0.62 * stl_pct) + (0.38 * deflections_pg)
    pass_interception = min(
        pass_interception, remap(disruption_signal, 1.0, 4.6, 28.0, 50.0)
    )

    if (
        (not is_big)
        and usg >= 28.0
        and ast_pct >= 24.0
        and stl_pct < 2.5
        and deflections_pg < 2.8
    ):
        pass_interception = min(pass_interception, 40.0)

    # Heliocentric perimeter creators are usually not high block/contest spam profiles
    # unless they post clear disruption signals.
    heliocentric_perimeter_creator = (not is_big) and (
        (usg >= 28.0 and ast_pct >= 24.0) or usg >= 32.0
    )
    if heliocentric_perimeter_creator:
        creator_block_cap = remap(blk_pct, 0.4, 2.2, 15.0, 35.0)
        creator_contest_cap = remap(
            (0.60 * contest_proxy) + (0.40 * blk100), 2.0, 55.0, 25.0, 45.0
        )
        if blk_pct < 1.2:
            creator_block_cap = min(creator_block_cap, 25.0)
            creator_contest_cap = min(creator_contest_cap, 40.0)
        block = min(block, creator_block_cap)
        contest_shot = min(contest_shot, creator_contest_cap)

    # Preserve baseline interior disruption for proven high-block players.
    if blk_pct >= 4.0 and blk100 >= 2.0:
        block = max(block, 40.0)
        contest_shot = max(contest_shot, 35.0)

    low_defense_role = defense_involvement < 28.0 and stl_pct < 1.2 and blk_pct < 1.0
    if low_defense_role:
        pass_interception *= 0.72
        on_ball_steal *= 0.72
        block *= 0.72
        contest_shot *= 0.72
        take_charge *= 0.80

    # Even weak defenders usually register some contest activity over a season.
    if minutes >= 1600:
        contest_floor = 15.0
    elif minutes >= 900:
        contest_floor = 10.0
    elif minutes >= 350:
        contest_floor = 5.0
    else:
        contest_floor = 0.0
    contest_shot = max(contest_shot, contest_floor)

    # Touch-specific soft_cap_power: driven primarily by tracking_touches_pg so that
    # true ball-handlers (Brunson, Maxey, Luka) break past the generic recommended cap.
    touch_soft_cap_power = max(
        soft_cap_power,
        clamp(
            0.10 + 0.75 * (scale_0_100(tracking_touches_pg, 25.0, 90.0) / 100.0),
            0.0,
            1.0,
        ),
    )

    core_results = [
        by_rule(
            "Shot",
            shot,
            {
                "advanced_usg_percent": usg,
                "per_36_fga_per_36_min": fga36,
                "shot_creation_signal": round(shot_creation_signal, 1),
            },
            soft_cap_power_override=shot_soft_cap_power,
        ),
        by_rule(
            "Touches",
            touch,
            {
                "advanced_ast_percent": ast_pct,
                "advanced_usg_percent": usg,
                "per_100_ast_per_100_poss": ast100,
                "tracking_touches_pg": tracking_touches_pg,
            },
            soft_cap_power_override=touch_soft_cap_power,
        ),
        by_rule(
            "Shot Close",
            shot_close,
            {
                "shooting_percent_fga_from_x3_10_range": close_share,
                "per_36_fga_per_36_min": fga36,
            },
        ),
        by_rule(
            "Shot Under",
            shot_under,
            {
                "shooting_percent_fga_from_x0_3_range": rim_share,
                "shooting_percent_dunks_of_fga": dunks_share,
            },
        ),
        by_rule(
            "Shot Mid",
            shot_mid,
            {"advanced_x3p_ar": fg3ar, "shooting_avg_dist_fga": avg_dist},
        ),
        by_rule(
            "Spot-Up Mid",
            spot_up_mid,
            {
                "shooting_percent_fga_from_x10_16_range": mid_share,
                "shooting_percent_fga_from_x16_3p_range": long_mid_share,
                "shooting_percent_assisted_x2p_fg": assisted2,
            },
        ),
        by_rule(
            "Off-Screen Mid",
            off_screen_mid,
            {
                "shooting_percent_fga_from_x10_16_range": mid_share,
                "pbp_features_stepback_freq": stepback_freq,
                "pbp_features_fadeaway_freq": fade_freq,
            },
        ),
        by_rule(
            "Shot 3",
            shot_3,
            {
                "per_36_x3pa_per_36_min": fg3a36,
                "advanced_x3p_ar": fg3ar,
                "per_36_x3p_percent": three_pct,
            },
            soft_cap_power_override=shot_3_soft_cap_power,
        ),
        by_rule(
            "Spot-Up 3",
            spot_up_3,
            {"shooting_percent_assisted_x3p_fg": assisted3, "advanced_x3p_ar": fg3ar},
        ),
        by_rule(
            "Off-Screen 3",
            off_screen_3,
            {
                "pbp_features_stepback_freq": stepback_freq,
                "pbp_features_pullup_freq": pullup_freq,
                "per_36_x3pa_per_36_min": fg3a36,
            },
        ),
        by_rule(
            "Contested Mid",
            contested_mid,
            {
                "shooting_percent_assisted_x2p_fg": assisted2,
                "advanced_usg_percent": usg,
            },
        ),
        by_rule(
            "Contested 3",
            contested_3,
            {
                "shooting_percent_assisted_x3p_fg": assisted3,
                "advanced_usg_percent": usg,
            },
        ),
        by_rule(
            "Step-Back Mid",
            step_back_mid,
            {
                "pbp_features_stepback_freq": stepback_freq,
                "shooting_percent_assisted_x2p_fg": assisted2,
            },
        ),
        by_rule(
            "Step-Back 3",
            step_back_3,
            {
                "pbp_features_stepback_freq": stepback_freq,
                "shooting_percent_assisted_x3p_fg": assisted3,
            },
        ),
        by_rule(
            "Spin Jumper",
            spin_jumper,
            {
                "pbp_features_fadeaway_freq": fade_freq,
                "shooting_percent_fga_from_x10_16_range": mid_share,
            },
        ),
        by_rule(
            "Transition Pull-Up 3",
            transition_pullup_3,
            {
                "pbp_features_pullup_3_freq": pullup3_freq,
                "per_36_x3pa_per_36_min": fg3a36,
            },
        ),
        by_rule(
            "Dribble Pull-Up Mid",
            dribble_pullup_mid,
            {
                "pbp_features_pullup_freq": pullup_freq,
                "pbp_features_fadeaway_freq": fade_freq,
                "mid_total_share": mid_share + long_mid_share,
            },
        ),
        by_rule(
            "Dribble Pull-Up 3",
            dribble_pullup_3,
            {
                "pbp_features_pullup_3_freq_raw": pullup3_freq,
                "pbp_features_pullup_3p_pct_raw": pullup3_pct,
                "used_pullup_3_freq": round(used_pullup3_freq, 5),
                "used_pullup_3p_pct": round(used_pullup3_pct, 5),
                "used_fallback": used_pullup3_fallback,
                "unassisted_3_share": round(unassisted3_share, 4),
                "per_36_x3p_percent": three_pct,
            },
        ),
        by_rule(
            "Drive",
            drive,
            {
                "per_36_fta_per_36_min": fta36,
                "shooting_percent_fga_from_x0_3_range": rim_share,
                "advanced_usg_percent": usg,
            },
        ),
        by_rule(
            "Spot-Up Drive",
            spot_up_drive,
            {"Drive": round(drive, 1), "shooting_percent_assisted_x2p_fg": assisted2},
        ),
        by_rule(
            "Off-Screen Drive",
            off_screen_drive,
            {"Drive": round(drive, 1), "Off-Screen 3": round(off_screen_3, 1)},
        ),
        by_rule(
            "Use Glass",
            use_glass,
            {"shooting_percent_fga_from_x0_3_range": rim_share, "position": position},
        ),
        by_rule(
            "Step Through",
            step_through,
            {"per_100_fta_per_100_poss": post_fta, "position": position},
        ),
        by_rule(
            "Spin Layup",
            spin_layup,
            {"shooting_percent_assisted_x2p_fg": assisted2, "Drive": round(drive, 1)},
        ),
        by_rule("Eurostep", eurostep, {"Drive": round(drive, 1), "position": position}),
        by_rule(
            "Hop Step",
            hop_step,
            {"Drive": round(drive, 1), "per_100_fta_per_100_poss": post_fta},
        ),
        by_rule(
            "Floater",
            floater,
            {
                "shooting_percent_fga_from_x3_10_range": close_share,
                "position": position,
            },
        ),
        by_rule(
            "Standing Dunk",
            standing_dunk,
            {"shooting_percent_dunks_of_fga": dunks_share, "position": position},
        ),
        by_rule(
            "Driving Dunk",
            driving_dunk,
            {"shooting_percent_dunks_of_fga": dunks_share, "Drive": round(drive, 1)},
        ),
        by_rule(
            "Flashy Dunk",
            flashy_dunk,
            {
                "Driving Dunk": round(driving_dunk, 1),
                "advanced_usg_percent": usg,
                "drive_creation_signal": round(drive_creation_signal, 1),
                "shooting_percent_dunks_of_fga": round(dunks_share, 4),
            },
            soft_cap_power_override=flashy_dunk_style_power,
        ),
        by_rule(
            "Alley-Oop",
            alley_oop,
            {"shooting_num_of_dunks": dunk_count, "position": position},
        ),
        by_rule(
            "Putback",
            putback,
            {
                "advanced_orb_percent": orb_pct,
                "shooting_percent_dunks_of_fga": dunks_share,
            },
        ),
        by_rule(
            "Crash",
            crash,
            {
                "advanced_orb_percent": orb_pct,
                "position": position,
                "per_36_fta_per_36_min": fta36,
                "shooting_percent_fga_from_x0_3_range": rim_share,
                "player_weight_lb": round(player_weight_lb, 1),
                "contact_finish_signal": round(contact_finish_signal, 1),
                "true_bumper": bool(true_bumper),
            },
        ),
        by_rule("Drive Right", drive_right, {"side_bias": round(side_bias, 3)}),
        by_rule(
            "Triple Threat Pump Fake",
            triple_pump_fake,
            {
                "advanced_usg_percent": usg,
                "shooting_percent_assisted_x2p_fg": assisted2,
            },
        ),
        by_rule(
            "Triple Threat Jab Step",
            triple_jab,
            {
                "advanced_usg_percent": usg,
                "mid_total_share": mid_share + long_mid_share,
            },
        ),
        by_rule(
            "Triple Threat Idle",
            triple_idle,
            {"advanced_ast_percent": ast_pct, "position": position},
        ),
        by_rule(
            "Triple Threat Shoot",
            triple_shoot,
            {"Shot 3": round(shot_3, 1), "Spot-Up 3": round(spot_up_3, 1)},
        ),
        by_rule(
            "Set Up Size-Up",
            setup_sizeup,
            {
                "advanced_usg_percent": usg,
                "shooting_percent_assisted_x3p_fg": assisted3,
            },
        ),
        by_rule(
            "Set Up Hesitation",
            setup_hesi,
            {"advanced_usg_percent": usg, "advanced_ast_percent": ast_pct},
        ),
        by_rule(
            "No Setup Dribble",
            no_setup_dribble,
            {
                "Set Up Size-Up": round(setup_sizeup, 1),
                "Set Up Hesitation": round(setup_hesi, 1),
            },
        ),
        by_rule(
            "Drive Crossover",
            drive_crossover,
            {"Drive": round(drive, 1), "position": position},
        ),
        by_rule(
            "Drive Double Crossover",
            drive_double_crossover,
            {"Drive Crossover": round(drive_crossover, 1), "advanced_usg_percent": usg},
        ),
        by_rule(
            "Drive Spin",
            drive_spin,
            {"Spin Layup": round(spin_layup, 1), "per_100_fta_per_100_poss": post_fta},
        ),
        by_rule(
            "Drive Half Spin",
            drive_half_spin,
            {"Drive Spin": round(drive_spin, 1), "advanced_usg_percent": usg},
        ),
        by_rule(
            "Drive Step Back",
            drive_step_back,
            {
                "Step-Back Mid": round(step_back_mid, 1),
                "Step-Back 3": round(step_back_3, 1),
            },
        ),
        by_rule(
            "Drive Behind Back",
            drive_behind_back,
            {"Drive Crossover": round(drive_crossover, 1), "advanced_usg_percent": usg},
        ),
        by_rule(
            "Drive Hesitation",
            drive_hesitation,
            {"Set Up Hesitation": round(setup_hesi, 1), "Drive": round(drive, 1)},
        ),
        by_rule(
            "Drive In & Out",
            drive_in_out,
            {
                "Drive Hesitation": round(drive_hesitation, 1),
                "advanced_ast_percent": ast_pct,
            },
        ),
        by_rule(
            "No Drive Dribble Move",
            no_drive_dribble_move,
            {
                "Drive Crossover": round(drive_crossover, 1),
                "Drive Behind Back": round(drive_behind_back, 1),
                "Drive Hesitation": round(drive_hesitation, 1),
            },
        ),
        by_rule(
            "Attack Strong Drive",
            attack_strong_drive,
            {
                "contact_finish_signal": round(contact_finish_signal, 1),
                "player_weight_lb": player_weight_lb,
                "dunks_share": dunks_share,
                "drive_creation_signal": round(drive_creation_signal, 1),
                "pullup_freq": round(pullup_freq, 3),
                "scoring_pct_pts_paint": scoring_pct_pts_paint,
            },
        ),
        by_rule(
            "Dish",
            dish,
            {
                "advanced_ast_percent": ast_pct,
                "per_100_ast_per_100_poss": ast100,
                "pass_creation_signal": round(pass_creation_signal, 1),
            },
            soft_cap_power_override=dish_soft_cap_power,
        ),
        by_rule(
            "Flashy Pass",
            flashy_pass,
            {"advanced_ast_percent": ast_pct, "advanced_tov_percent": tov_pct},
        ),
        by_rule(
            "Alley-Oop Pass",
            alley_oop_pass,
            {"advanced_ast_percent": ast_pct, "shooting_num_of_dunks": dunk_count},
        ),
        by_rule(
            "Roll vs Pop",
            roll_vs_pop,
            {
                "advanced_x3p_ar": fg3ar,
                "position": position,
                "roll_vs_pop_signal": round(roll_vs_pop_signal, 1),
                "roll_man_signal": round(roll_man_signal, 1),
                "paint_signal": round(paint_signal, 1),
                "pop_signal": round(pop_signal, 1),
            },
            apply_recommended_cap=False,
        ),
        by_rule(
            "Spot vs Cut",
            spot_vs_cut,
            {
                "advanced_x3p_ar": fg3ar,
                "shooting_percent_fga_from_x0_3_range": rim_share,
            },
        ),
        by_rule("ISO vs Elite", iso_vs_elite, {"iso_base": round(iso_base, 1)}),
        by_rule("ISO vs Good", iso_vs_good, {"iso_base": round(iso_base, 1)}),
        by_rule(
            "ISO vs Average",
            iso_vs_average,
            {"iso_base": round(iso_base, 1), "iso_superstar_lane": iso_superstar_lane},
            apply_recommended_cap=not iso_superstar_lane,
        ),
        by_rule(
            "ISO vs Poor",
            iso_vs_poor,
            {"iso_base": round(iso_base, 1), "iso_superstar_lane": iso_superstar_lane},
            apply_recommended_cap=not iso_superstar_lane,
        ),
        by_rule(
            "Play Discipline",
            play_discipline,
            {"advanced_usg_percent": usg, "advanced_ast_percent": ast_pct},
            soft_cap_power_override=play_discipline_power,
        ),
        by_rule(
            "Post Up",
            post_profile,
            {
                "advanced_x3p_ar": fg3ar,
                "pbp_features_hook_freq": hook_freq,
                "per_100_fta_per_100_poss": post_fta,
                "position": position,
            },
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Back Down",
            post_back_down,
            {"per_100_fta_per_100_poss": post_fta, "position": position},
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Aggressive Back Down",
            post_aggressive_back_down,
            {"Post Back Down": round(post_back_down, 1), "position": position},
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Face Up",
            post_face_up,
            {
                "mid_total_share": mid_share + long_mid_share,
                "advanced_usg_percent": usg,
            },
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Spin",
            post_spin,
            {
                "pbp_features_hook_freq": hook_freq,
                "pbp_features_fadeaway_freq": fade_freq,
            },
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Drive",
            post_drive,
            {"Drive": round(drive, 1), "Post Face Up": round(post_face_up, 1)},
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Drop Step",
            post_drop_step,
            {"Post Back Down": round(post_back_down, 1), "position": position},
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Shoot From Post",
            shoot_from_post,
            {
                "Post Face Up": round(post_face_up, 1),
                "mid_total_share": mid_share + long_mid_share,
            },
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Hook Left",
            post_hook_left,
            {"pbp_features_hook_freq": hook_freq, "per_100_fta_per_100_poss": post_fta},
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Hook Right",
            post_hook_right,
            {"pbp_features_hook_freq": hook_freq, "per_100_fta_per_100_poss": post_fta},
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Fade Left",
            post_fade_left,
            {
                "pbp_features_fadeaway_freq": fade_freq,
                "mid_total_share": mid_share + long_mid_share,
            },
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Fade Right",
            post_fade_right,
            {
                "pbp_features_fadeaway_freq": fade_freq,
                "mid_total_share": mid_share + long_mid_share,
            },
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Shimmy",
            post_shimmy,
            {"Post Fade Left": round(post_fade_left, 1), "advanced_usg_percent": usg},
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Hop Shot",
            post_hop_shot,
            {
                "Post Fade Left": round(post_fade_left, 1),
                "Step-Back Mid": round(step_back_mid, 1),
            },
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Step Back",
            post_step_back,
            {
                "Step-Back Mid": round(step_back_mid, 1),
                "Post Face Up": round(post_face_up, 1),
            },
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Post Up & Under",
            post_up_under,
            {"Post Spin": round(post_spin, 1), "Post Drive": round(post_drive, 1)},
            soft_cap_power_override=post_soft_cap_power,
        ),
        by_rule(
            "Take Charge",
            take_charge,
            {"advanced_stl_percent": stl_pct, "Foul": round(foul, 1)},
        ),
        by_rule(
            "Foul",
            foul,
            {
                "play_by_play_shooting_foul_committed": hard_foul_proxy,
                "per_100_pf_per_100_poss": as_float(row, "per_100_pf_per_100_poss"),
            },
        ),
        by_rule(
            "Hard Foul",
            hard_foul,
            {
                "play_by_play_shooting_foul_committed": hard_foul_proxy,
                "per_100_pf_per_100_poss": as_float(row, "per_100_pf_per_100_poss"),
            },
        ),
        by_rule(
            "Pass Interception",
            pass_interception,
            {
                "advanced_stl_percent": stl_pct,
                "per_100_stl_per_100_poss": as_float(row, "per_100_stl_per_100_poss"),
            },
        ),
        by_rule(
            "On-Ball Steal",
            on_ball_steal,
            {
                "advanced_stl_percent": stl_pct,
                "play_by_play_lost_ball_turnover": as_float(
                    row, "play_by_play_lost_ball_turnover"
                ),
            },
        ),
        by_rule(
            "Block",
            block,
            {
                "advanced_blk_percent": blk_pct,
                "per_100_blk_per_100_poss": as_float(row, "per_100_blk_per_100_poss"),
            },
        ),
        by_rule(
            "Contest Shot",
            contest_shot,
            {
                "advanced_blk_percent": blk_pct,
                "play_by_play_fga_blocked": contest_proxy,
            },
        ),
    ]

    by_name = {r.name: r for r in core_results}

    close_zone_names = [
        "Shot Close Left",
        "Shot Close Middle",
        "Shot Close Right",
    ]
    # Restricted area FGA dominates the middle; paint non-RA splits left/right via side_bias.
    close_zone_weights = [
        0.7 + (0.5 * zone_paint_share) + (0.4 * (1.0 - side_bias)),
        1.2 + (1.5 * zone_restricted_share),
        0.7 + (0.5 * zone_paint_share) + (0.4 * (1.0 + side_bias)),
    ]

    mid_zone_names = [
        "Shot Mid Center",
        "Shot Mid Left",
        "Shot Mid Left Center",
        "Shot Mid Right",
        "Shot Mid Right Center",
    ]
    # Use actual zone_mid_share_pct to weight center vs wings; long_mid_share lifts wings.
    mid_zone_weights = [
        0.6 + (1.2 * zone_mid_share_pct) + (0.6 * pullup_freq),
        0.6 + (0.4 * (1.0 - side_bias)),
        0.8
        + (1.0 * long_mid_share)
        + (0.6 * zone_mid_share_pct)
        + (0.3 * (1.0 - side_bias)),
        0.6 + (0.4 * (1.0 + side_bias)),
        0.8
        + (1.0 * long_mid_share)
        + (0.6 * zone_mid_share_pct)
        + (0.3 * (1.0 + side_bias)),
    ]

    three_zone_names = [
        "Shot Three Center",
        "Shot Three Left",
        "Shot Three Left Center",
        "Shot Three Right",
        "Shot Three Right Center",
    ]
    # Use actual zone FGA breakdowns for 3-point sub-zones.
    total_3pt_zone_fga = (
        zone_left_corner_3_fga + zone_right_corner_3_fga + zone_above_break_3_fga
    )
    if total_3pt_zone_fga > 0:
        left_corner_prop = zone_left_corner_3_fga / total_3pt_zone_fga
        right_corner_prop = zone_right_corner_3_fga / total_3pt_zone_fga
        above_break_prop = zone_above_break_3_fga / total_3pt_zone_fga
    else:
        left_corner_prop = 0.15
        right_corner_prop = 0.15
        above_break_prop = 0.70
    # Above-break splits into center (pull-up heavy) and wings (catch-and-shoot heavy).
    pullup_center_factor = 0.35 + 0.30 * clamp(pullup3_freq / 0.15, 0.0, 1.0)
    wing_each = (1.0 - pullup_center_factor) / 2.0
    three_zone_weights = [
        0.5 + (2.5 * above_break_prop * pullup_center_factor) + (0.8 * pullup3_freq),
        0.5 + (2.5 * left_corner_prop),
        0.5 + (2.5 * above_break_prop * wing_each) + (0.3 * (1.0 - side_bias)),
        0.5 + (2.5 * right_corner_prop),
        0.5 + (2.5 * above_break_prop * wing_each) + (0.3 * (1.0 + side_bias)),
    ]

    close_zone_results = build_zone_family_results(
        "Shot Close Locations",
        close_zone_names,
        close_zone_weights,
        by_name["Shot Close"],
        {
            "zone_restricted_share": round(zone_restricted_share, 3),
            "zone_paint_share": round(zone_paint_share, 3),
            "side_bias": round(side_bias, 3),
        },
    )

    mid_zone_results = build_zone_family_results(
        "Shot Mid Locations",
        mid_zone_names,
        mid_zone_weights,
        by_name["Shot Mid"],
        {
            "zone_mid_share_pct": round(zone_mid_share_pct, 3),
            "long_mid_share": round(long_mid_share, 3),
            "pullup_freq": round(pullup_freq, 3),
            "side_bias": round(side_bias, 3),
        },
    )

    three_zone_results = build_zone_family_results(
        "Shot Three Locations",
        three_zone_names,
        three_zone_weights,
        by_name["Shot 3"],
        {
            "left_corner_prop": round(left_corner_prop, 3),
            "right_corner_prop": round(right_corner_prop, 3),
            "above_break_prop": round(above_break_prop, 3),
            "pullup3_freq": round(pullup3_freq, 3),
            "side_bias": round(side_bias, 3),
        },
    )

    results = core_results + close_zone_results + mid_zone_results + three_zone_results

    return results


def apply_role_redundancy_and_contradictions(roles: List[str]) -> List[str]:
    cleaned: List[str] = []
    for role in roles:
        if role not in cleaned:
            cleaned.append(role)

    for group in ROLE_REDUNDANCY_GROUPS:
        seen = [r for r in cleaned if r in group]
        if len(seen) <= 1:
            continue
        keeper = seen[0]
        cleaned = [r for r in cleaned if (r not in group) or (r == keeper)]

    for pair in ROLE_CONTRADICTIONS:
        seen = [r for r in cleaned if r in pair]
        if len(seen) <= 1:
            continue
        keeper = seen[0]
        cleaned = [r for r in cleaned if (r not in pair) or (r == keeper)]

    return cleaned


def select_player_roles(
    row: Dict[str, Any], by_name: Dict[str, TendencyResult]
) -> List[str]:
    usg = as_float(row, "advanced_usg_percent")
    ast_pct = as_float(row, "advanced_ast_percent")
    fga36 = as_float(row, "per_36_fga_per_36_min")
    fg3a36 = as_float(row, "per_36_x3pa_per_36_min")
    fg3a_pg = as_float(row, "per_game_x3pa_per_game")
    three_pct = as_float(
        row, "per_36_x3p_percent", as_float(row, "per_game_x3p_percent")
    )
    age = as_float(row, "age", 27.0)
    minutes = as_float(row, "totals_mp")
    tov_pct = as_float(row, "advanced_tov_percent")
    position = str(row.get("position", ""))
    is_big = ("C" in position) or ("PF" in position)

    roles: List[str] = []

    # 1) Team touch role.
    if usg >= 29.0 and ast_pct >= 24.0:
        roles.append("T1")
    elif usg >= 22.0 and ast_pct >= 17.0:
        roles.append("T2")
    elif ast_pct >= 14.0 or usg >= 18.0:
        roles.append("T3")

    # 2) Shot hierarchy when a scoring ladder exists.
    if usg >= 21.0 or fga36 >= 14.0:
        if usg >= 30.0 or fga36 >= 20.0:
            roles.append("S1")
        elif usg >= 25.0 or fga36 >= 17.0:
            roles.append("S2")
        else:
            roles.append("S3")

    # 3) Core role (mandatory).
    if minutes < 900.0 and usg >= 24.0:
        roles.append("MIC")
    elif minutes < 1000.0 and usg < 20.0:
        roles.append("BEN")
    elif age <= 23.0 and minutes < 1500.0:
        roles.append("DEV")
    elif ast_pct >= 27.0:
        roles.append("CON")
    else:
        roles.append("ROL")

    # 4) Primary scoring style (one only).
    drive = by_name["Drive"].final
    shot_3 = by_name["Shot 3"].final
    shot_mid = by_name["Shot Mid"].final
    post_up = by_name["Post Up"].final
    standing_dunk = by_name["Standing Dunk"].final
    if post_up >= 45 and (is_big or shot_mid >= 35):
        roles.append("PST")
    elif standing_dunk >= 40 and drive <= 40:
        roles.append("PNR")
    elif fg3a_pg >= 8.0 and three_pct >= 0.35 and drive >= 40:
        roles.append("3L")
    elif fg3a_pg >= 6.0 and three_pct >= 0.355:
        roles.append("SHO")
    elif drive >= 45 and by_name["Driving Dunk"].final >= 30:
        roles.append("SLH")
    elif shot_mid >= 45 and shot_3 < 40:
        roles.append("MID")
    elif (fg3a_pg >= 8.0 and three_pct >= 0.35 and drive >= 40) or (
        shot_3 >= 40 and shot_mid >= 40 and drive >= 40
    ):
        roles.append("3L")
    elif (
        (fg3a_pg >= 6.0 and three_pct >= 0.36)
        or (fg3a36 >= 8.5 and three_pct >= 0.35)
        or (shot_3 >= 45 and drive < 45)
    ):
        roles.append("SHO")
    else:
        roles.append("SHO")

    # 5) Defense identity or IQ fallback.
    if by_name["Block"].final >= 40 and by_name["Contest Shot"].final >= 40:
        roles.append("ANCH" if is_big else "RIMD")
    elif (
        by_name["On-Ball Steal"].final >= 40
        and by_name["Pass Interception"].final >= 35
    ):
        roles.append("POA")
    elif by_name["On-Ball Steal"].final >= 30 and by_name["Contest Shot"].final >= 30:
        roles.append("SWI")
    else:
        roles.append("CTL")

    # 6) Physical/playstyle edge.
    if by_name["Driving Dunk"].final >= 40:
        roles.append("HFL")
    elif by_name["Drive"].final >= 45:
        roles.append("BLW")
    elif by_name["Post Back Down"].final >= 40:
        roles.append("BUL")
    elif by_name["Attack Strong Drive"].final >= 40:
        roles.append("PHY")
    else:
        roles.append("CTL")

    # 7) IQ reinforcement if needed.
    if ast_pct >= 24.0 and tov_pct <= 14.0:
        roles.append("PSS")
    elif usg >= 28.0 and tov_pct <= 13.5:
        roles.append("CTL")

    roles = apply_role_redundancy_and_contradictions(roles)

    # Keep exactly 5 standard roles.
    fallback_roles = ["ROL", "ROT", "GLUE", "HUST", "DISCIP"]
    for role in fallback_roles:
        if len(roles) >= 5:
            break
        if role not in roles:
            roles.append(role)
    roles = roles[:5]

    # Unicorn role for truly exceptional players.
    unicorn_role: Optional[str] = None
    if usg >= 31.0 and ast_pct >= 28.0 and by_name["ISO vs Poor"].final >= 50:
        unicorn_role = "SCE"
    elif (
        ast_pct >= 34.0 and by_name["Dish"].final >= 45 and by_name["Crash"].final >= 35
    ):
        unicorn_role = "TDH"
    elif (
        by_name["Block"].final >= 45
        and by_name["Pass Interception"].final >= 40
        and by_name["Contest Shot"].final >= 45
    ):
        unicorn_role = "DSC"
    if unicorn_role and unicorn_role not in roles:
        roles.append(unicorn_role)

    return roles


def select_player_roles_from_stats(
    row: Dict[str, Any], role_catalog: Optional[Dict[str, List[str]]] = None
) -> List[str]:
    if role_catalog is None:
        role_catalog = {}

    def n(value: float, lo: float, hi: float) -> float:
        return remap(value, lo, hi, 0.0, 1.0)

    usg = as_float(row, "advanced_usg_percent")
    ast_pct = as_float(row, "advanced_ast_percent")
    tov_pct = as_float(row, "advanced_tov_percent")
    ts_pct = as_float(row, "advanced_ts_percent")
    ft_pct = as_float(row, "per_36_ft_percent", as_float(row, "per_game_ft_percent"))
    fg3a_pg = as_float(row, "per_game_x3pa_per_game")
    fg3a36 = as_float(row, "per_36_x3pa_per_36_min")
    three_pct = as_float(
        row, "per_36_x3p_percent", as_float(row, "per_game_x3p_percent")
    )
    two_pct = as_float(row, "per_36_x2p_percent", as_float(row, "per_game_x2p_percent"))
    rim_share = as_float(row, "shooting_percent_fga_from_x0_3_range")
    close_share = as_float(row, "shooting_percent_fga_from_x3_10_range")
    mid_share = as_float(row, "shooting_percent_fga_from_x10_16_range")
    long_mid_share = as_float(row, "shooting_percent_fga_from_x16_3p_range")
    three_share = as_float(row, "shooting_percent_fga_from_x3p_range")
    assisted2 = as_float(row, "shooting_percent_assisted_x2p_fg")
    assisted3 = as_float(row, "shooting_percent_assisted_x3p_fg")
    dunks_share = as_float(row, "shooting_percent_dunks_of_fga")
    dunks = as_float(row, "shooting_num_of_dunks")
    stl_pct = as_float(row, "advanced_stl_percent")
    blk_pct = as_float(row, "advanced_blk_percent")
    orb_pct = as_float(row, "advanced_orb_percent")
    drb_pct = as_float(row, "advanced_drb_percent")
    minutes = as_float(row, "totals_mp")
    age = as_float(row, "age", 27.0)
    position = str(row.get("position", ""))
    player_key = str(row.get("player_id", row.get("player_name", "unknown")))

    is_big = 1.0 if (("C" in position) or ("PF" in position)) else 0.0
    is_guard = 1.0 if (("PG" in position) or ("SG" in position)) else 0.0
    usage = n(usg, 12.0, 35.0)
    passing = n(ast_pct, 5.0, 42.0)
    shooting = (
        0.45 * n(three_pct, 0.30, 0.41)
        + 0.35 * n(fg3a_pg, 0.5, 8.0)
        + 0.20 * n(fg3a36, 0.4, 13.0)
    )
    mid_touch = (
        0.45 * n(ft_pct, 0.58, 0.93)
        + 0.30 * n(two_pct, 0.46, 0.67)
        + 0.25 * n(mid_share + long_mid_share, 0.06, 0.45)
    )
    rim_pressure = (
        0.45 * n(rim_share + close_share, 0.18, 0.72)
        + 0.35 * n(dunks_share, 0.00, 0.14)
        + 0.20 * n(dunks, 0.0, 250.0)
    )
    defense = (
        0.45 * n(stl_pct, 0.3, 3.5)
        + 0.35 * n(blk_pct, 0.2, 10.0)
        + 0.20 * n(orb_pct + drb_pct, 10.0, 48.0)
    )
    iq = (
        0.45 * n(ts_pct, 0.48, 0.68)
        + 0.35 * n(1.0 - n(tov_pct, 8.0, 20.0), 0.0, 1.0)
        + 0.20 * passing
    )
    workload = n(minutes, 350.0, 3000.0)
    age_curve = n(1.0 - n(age, 19.0, 37.0), 0.0, 1.0)
    off_creation = 0.55 * usage + 0.45 * (1.0 - n(assisted2, 0.10, 0.85))
    shot_creation = 0.55 * usage + 0.45 * (1.0 - n(assisted3, 0.10, 0.85))
    balance = 1.0 - min(1.0, abs(shooting - rim_pressure))

    section_targets: Dict[str, float] = {
        # HIERARCHY list is ordered T1→S3 (best creator first). High usage+passing
        # should map to the BEGINNING of the list (phase 0 = T1), so the signal
        # must be INVERTED: 1 - combined → LeBron 0.177 → T1, role player 0.93 → S3.
        "HIERARCHY": clamp(1.0 - (0.58 * usage + 0.42 * passing), 0.0, 1.0),
        # CORE ROLES: use workload+iq instead of age_curve so veteran high-IQ players
        # don't get artificially randomized into GLUE/ENG by age_curve=0.
        "CORE ROLES": clamp(0.45 * workload + 0.55 * iq, 0.0, 1.0),
        "SCORING STYLES": clamp(
            0.45 * shooting + 0.30 * rim_pressure + 0.25 * shot_creation, 0.0, 1.0
        ),
        "DRIVE / ATTACK": clamp(
            0.45 * rim_pressure + 0.30 * off_creation + 0.25 * usage, 0.0, 1.0
        ),
        "DEFENSE": clamp(0.60 * defense + 0.25 * workload + 0.15 * is_big, 0.0, 1.0),
        "IQ / CONTROL": clamp(0.45 * iq + 0.35 * passing + 0.20 * usage, 0.0, 1.0),
        "UTILITY": clamp(
            0.40 * balance + 0.30 * workload + 0.30 * (1.0 - abs(is_big - is_guard)),
            0.0,
            1.0,
        ),
        "SPECIALIST": clamp(
            0.40 * max(shooting, rim_pressure)
            + 0.30 * usage
            + 0.30 * max(defense, passing),
            0.0,
            1.0,
        ),
        "UNICORN ROLES": clamp(
            0.35 * usage + 0.25 * passing + 0.20 * shooting + 0.20 * defense, 0.0, 1.0
        ),
    }

    section_intensity: Dict[str, float] = {
        "HIERARCHY": clamp(0.7 * usage + 0.3 * passing, 0.0, 1.0),
        # CORE intensity: use workload+iq (not age_curve) to keep jitter tight for vets.
        "CORE ROLES": clamp(0.6 * workload + 0.4 * iq, 0.0, 1.0),
        "SCORING STYLES": clamp(0.6 * usage + 0.4 * shooting, 0.0, 1.0),
        "DRIVE / ATTACK": clamp(0.6 * rim_pressure + 0.4 * off_creation, 0.0, 1.0),
        "DEFENSE": clamp(0.7 * defense + 0.3 * workload, 0.0, 1.0),
        "IQ / CONTROL": clamp(0.7 * iq + 0.3 * passing, 0.0, 1.0),
        "UTILITY": clamp(0.6 * balance + 0.4 * workload, 0.0, 1.0),
        "SPECIALIST": clamp(
            0.5 * max(shooting, rim_pressure) + 0.5 * max(defense, passing), 0.0, 1.0
        ),
        "UNICORN ROLES": clamp(0.8 * max(usage, passing) + 0.2 * defense, 0.0, 1.0),
    }

    def pick_role(section: str) -> Optional[str]:
        codes = role_catalog.get(section, [])
        if not codes:
            return None
        allowed = allowed_codes.get(section)
        if allowed is not None:
            codes = [c for c in codes if c in allowed]
            if not codes:
                codes = role_catalog.get(section, [])
        if len(codes) == 1:
            return codes[0]
        base_target = section_targets.get(section, 0.5)
        intensity = section_intensity.get(section, 0.5)
        spread = 0.32 + (0.18 * (1.0 - intensity))
        jitter = stable_side_bias(f"{player_key}:{section}:jitter") * spread
        target = clamp(base_target + jitter, 0.0, 1.0)
        best_code: Optional[str] = None
        best_score = -1e9
        count = float(len(codes) - 1)
        for idx, code in enumerate(codes):
            phase = idx / count if count > 0 else 0.0
            proximity = 1.0 - abs(target - phase)
            role_noise = stable_side_bias(f"{player_key}:{section}:{code}")
            score = (100.0 * proximity) + (20.0 * intensity) + (10.0 * role_noise)
            if score > best_score:
                best_score = score
                best_code = code
        return best_code

    # ------------------------------------------------------------------
    # Stat-gated role pickers for the three identity-defining sections.
    # Each returns a single role code matched to what the stats say.
    # ------------------------------------------------------------------

    def pick_scoring_role() -> str:
        """Choose the scoring style that best matches this player's shot diet."""
        available = set(role_catalog.get("SCORING STYLES", []))

        # ---- 3-point specialists / volume shooters ----
        high3a = fg3a_pg >= 6.0
        good3a = fg3a_pg >= 3.5
        elite3pct = three_pct >= 0.38
        good3pct = three_pct >= 0.34

        if high3a and elite3pct and three_share >= 0.50:
            if "SHO" in available:
                return "SHO"  # pure shooter (Curry, Klay)
        if high3a and good3pct and "3L" in available:
            return "3L"  # 3-level scorer
        if good3a and elite3pct and "ARC" in available:
            return "ARC"  # arc shooter (Beal, Booker from 3)
        if good3a and assisted3 >= 0.70 and "C&S" in available:
            return "C&S"  # catch-and-shoot specialist
        if good3a and "MOV" in available and three_share >= 0.35:
            return "MOV"  # movement shooter

        # ---- Rim / interior ----
        elite_rim = (rim_share + close_share) >= 0.55
        if elite_rim and dunks_share >= 0.12 and "RR" in available:
            return "RR"  # rim runner / dunker
        if elite_rim and is_big >= 0.5 and "PNR" in available:
            return "PNR"  # pick and roll scorer
        if elite_rim and "FIN" in available:
            return "FIN"  # finisher at rim

        # ---- Post game ----
        mid_vol = mid_share + long_mid_share
        if is_big >= 0.5 and mid_vol >= 0.28 and two_pct >= 0.52:
            if ft_pct >= 0.80 and "PST" in available:
                return "PST"  # post scorer (KAT, KD low block)
            if "FAC" in available:
                return "FAC"  # face-up / mid-post

        # ---- Mid-range / pull-up ----
        if mid_vol >= 0.25 and two_pct >= 0.50:
            if n(usg, 12.0, 35.0) >= 0.65 and "MID" in available:
                return "MID"  # elite mid-range (KD, kawhi)
            if assisted2 <= 0.55 and "PULL" in available:
                return "PULL"  # pull-up mid
            if "STB" in available:
                return "STB"  # spot-up balanced shooter

        # ---- Versatile / balanced ----
        if usage >= 0.45 and (passing >= 0.35 or iq >= 0.55):
            if "SHH" in available:
                return "SHH"  # shot-heavy but efficient
        if balance >= 0.65 and "WING" in available:
            return "WING"  # all-court wing scorer
        if usage >= 0.40 and rim_pressure <= 0.40 and "ISO3" in available:
            return "ISO3"  # isolation 3-point threat

        # ---- Fallback: proximity pick from remaining ----
        return _proximity_pick("SCORING STYLES", available)

    def pick_defense_role() -> str:
        """Choose defense role based on actual stl/blk/position profile."""
        available = set(role_catalog.get("DEFENSE", []))

        # Position-based exclusions first
        if is_big >= 0.5:
            available -= {"POA", "PRESS", "DENY", "SCRN"}
        else:
            available -= {"ANCH", "DROP", "WEAK", "POSTD"}

        high_stl = stl_pct >= 2.0
        good_stl = stl_pct >= 1.4
        high_blk = blk_pct >= 2.5
        good_blk = blk_pct >= 1.5
        high_reb = (orb_pct + drb_pct) >= 22.0

        # ---- Perimeter stoppers ----
        if not is_big:
            if high_stl and n(usg, 12.0, 35.0) >= 0.40 and "POA" in available:
                return "POA"  # on-ball pressure specialist
            if high_stl and "LOCK" in available:
                return "LOCK"  # lockdown defender (Kawhi, Jrue)
            if good_stl and passing >= 0.40 and "BHW" in available:
                return "BHW"  # ball hawk / gambler
            if "GLS" in available and high_reb:
                return "GLS"  # glass-eater / rebounding guard

        # ---- Big men / rim protectors ----
        if is_big:
            if high_blk and high_reb and "ANCH" in available:
                return "ANCH"  # anchor / rim protector
            if high_blk and "RIMD" in available:
                return "RIMD"  # rim deterrent
            if good_blk and "SWI" in available:
                return "SWI"  # switchable big
            if high_reb and "GLS" in available:
                return "GLS"  # glass-dominant big
            if good_stl and "BHW" in available:
                return "BHW"  # physical/ball-hawk wing big
            if "HELP" in available:
                return "HELP"  # help-side team defender (default for PF wings)

        # ---- Versatile / switchable ----
        if "SWI" in available and (good_stl or good_blk):
            return "SWI"
        if "HELP" in available and workload >= 0.55:
            return "HELP"  # help-side / team defender
        if "INT" in available:
            return "INT"  # team-oriented interior

        return _proximity_pick("DEFENSE", available)

    def pick_drive_role() -> str:
        """Choose drive/attack style based on rim pressure and creation."""
        available = set(role_catalog.get("DRIVE / ATTACK", []))

        if is_big >= 0.5:
            available -= {
                "BLW",
                "SHIFT",
                "BURST",
                "SPLT",
                "HES",
                "SPN",
                "SNAK",
                "SIDE",
                "BACK",
            }
        else:
            available -= {"BUL", "BODY", "GRIND"}

        elite_creator = off_creation >= 0.70
        strong_creator = off_creation >= 0.50
        elite_rim_p = rim_pressure >= 0.60

        if not is_big:
            if elite_creator and elite_rim_p and "BLW" in available:
                return "BLW"  # blow-by athlete (Zion, Ja)
            if elite_creator and "HES" in available:
                return "HES"  # hesitation / crossover
            if strong_creator and shooting >= 0.45 and "SPN" in available:
                return "SPN"  # spin move creator
            if strong_creator and "CTL" in available:
                return "CTL"  # controlled drive
            if elite_rim_p and dunks_share >= 0.10 and "HFL" in available:
                return "HFL"  # high-flier
            if "PHY" in available and rim_pressure >= 0.40:
                return "PHY"  # physical driver
            if "TRN" in available:
                return "TRN"  # turn-drive baseline

        if is_big:
            if "BUL" in available and rim_pressure >= 0.50:
                return "BUL"  # bull / power drive
            if "GRIND" in available and workload >= 0.55:
                return "GRIND"  # grind / hard cut big
            if "CTL" in available:
                return "CTL"

        return _proximity_pick("DRIVE / ATTACK", available)

    def pick_core_role() -> str:
        """Choose core role based on player usage/workload/IQ profile."""
        available = set(role_catalog.get("CORE ROLES", []))

        # Age-gate
        if age < 33.0:
            available.discard("VET")
        if age >= 22.0 or workload >= 0.30:
            available.discard("DEV")
        # Gate bench/fringe roles away from featured players
        if workload >= 0.50 or usage >= 0.40:
            available -= {"EMG", "BEN", "FILL", "ROT"}

        # Stat-gated picks — order matters (most specific first)
        if (
            "ISO" in available
            and usage >= 0.65
            and (1.0 - n(assisted2, 0.10, 0.85)) >= 0.55
        ):
            return "ISO"  # isolation-heavy scorer
        if "CLO" in available and usage >= 0.55 and iq >= 0.55:
            return "CLO"  # closer / end-of-game option
        if "MIC" in available and usage >= 0.45 and workload <= 0.45:
            return "MIC"  # microwave scorer off bench
        if "CON" in available and passing >= 0.55 and usage >= 0.40:
            return "CON"  # conductor / offense facilitator
        if "STBLY" in available and age >= 28.0 and iq >= 0.55 and workload >= 0.55:
            return "STBLY"  # stability piece (consistent vet)
        if (
            "SPT" in available
            and shooting >= 0.55
            and off_creation <= 0.30
            and usage <= 0.40
        ):
            return "SPT"  # spot-up only
        if "GLUE" in available and defense >= 0.35 and iq >= 0.45 and usage <= 0.42:
            return "GLUE"  # glue guy
        if "ENG" in available and defense >= 0.35 and workload <= 0.50:
            return "ENG"  # energy role

        return _proximity_pick("CORE ROLES", available)

    def pick_specialist_role() -> str:
        """Choose specialist role via stat gates — prevents nonsensical assignments."""
        available = set(role_catalog.get("SPECIALIST", []))

        # Gate aerial/rim roles away from perimeter players
        if is_guard or (not is_big and rim_pressure < 0.45):
            available -= {"LOB2", "ROLL", "TIPD"}
        # Gate off-ball movement roles away from primary creators
        if usage >= 0.55:
            available -= {"BACKCUT", "HAMMER", "GHOST", "FLARE", "PIN", "RELOC"}
        if is_big:
            available -= {"FLARE", "BACKCUT"}
        else:
            available -= {"POSTHUB", "STACKPNR", "SPAIN", "ELBOW"}

        # Stat-gated picks — most specific first
        if "CLM" in available and usage >= 0.55 and iq >= 0.50:
            return "CLM"  # clutch scorer
        if "PNH" in available and ast_pct >= 28.0 and usage >= 0.50:
            return "PNH"  # PnR ball handler
        if "GRAV" in available and usage >= 0.70 and shooting >= 0.45:
            return "GRAV"  # gravity creator
        if "KICK" in available and off_creation >= 0.55 and passing >= 0.40:
            return "KICK"  # drive and kick
        if "DHO" in available and ast_pct >= 25.0 and usage >= 0.45:
            return "DHO"  # DHO operator
        if "SCO" in available and usage >= 0.40 and off_creation >= 0.45:
            return "SCO"  # secondary creator
        if "DEC" in available and usage >= 0.55 and shooting >= 0.50:
            return "DEC"  # decoy / floor spacer who draws attention
        if "PIN" in available and shooting >= 0.55 and off_creation <= 0.30:
            return "PIN"  # pin-down shooter
        if "FLARE" in available and shooting >= 0.45 and not is_big:
            return "FLARE"  # flare shooter
        if "SCREENIQ" in available and is_big and iq >= 0.50:
            return "SCREENIQ"  # screen IQ big
        if "SHORT" in available and is_big and passing >= 0.35:
            return "SHORT"  # short roll passer big

        return _proximity_pick("SPECIALIST", available)

    def _proximity_pick(section: str, available: set) -> str:
        """Fallback: proximity pick against section_targets from whatever is available."""
        codes = [c for c in role_catalog.get(section, []) if c in available]
        if not codes:
            codes = role_catalog.get(section, [])
        if not codes:
            return ""
        if len(codes) == 1:
            return codes[0]
        base_target = section_targets.get(section, 0.5)
        intensity = section_intensity.get(section, 0.5)
        spread = 0.32 + (0.18 * (1.0 - intensity))
        jitter = stable_side_bias(f"{player_key}:{section}:jitter") * spread
        target = clamp(base_target + jitter, 0.0, 1.0)
        best_code: Optional[str] = None
        best_score = -1e9
        count = float(len(codes) - 1)
        for idx, code in enumerate(codes):
            phase = idx / count if count > 0 else 0.0
            proximity = 1.0 - abs(target - phase)
            role_noise = stable_side_bias(f"{player_key}:{section}:{code}")
            score = (100.0 * proximity) + (20.0 * intensity) + (10.0 * role_noise)
            if score > best_score:
                best_score = score
                best_code = code
        return best_code or codes[0]

    # allowed_codes kept for pick_role() which handles remaining sections
    allowed_codes: Dict[str, set] = {}

    roles: List[str] = []
    base_sections = ["HIERARCHY", "CORE ROLES", "SCORING STYLES", "DEFENSE"]
    alt_sections = ["DRIVE / ATTACK", "IQ / CONTROL", "UTILITY", "SPECIALIST"]

    # HIERARCHY: use direct threshold assignment — the T/S tiers are categorical, not a
    # continuous spectrum. T-tiers = playmaking-led creation; S-tiers = score-first role.
    _hier_catalog = role_catalog.get("HIERARCHY", ["T1", "T2", "T3", "S1", "S2", "S3"])

    def _pick_hier() -> str:
        if passing >= 0.70 and usage >= 0.55:
            return "T1"  # elite creator (LeBron, Jokic, Harden)
        if passing >= 0.55 and usage >= 0.45:
            return "T2"  # strong initiator (Giannis, SGA)
        if passing >= 0.45 and usage >= 0.45:
            return "T3"  # connector (Curry, Tatum — real passing + volume)
        if usage >= 0.48 and workload >= 0.15:
            return "S1"  # primary scorer (Booker, Kawhi, Brown)
        if passing >= 0.40:
            return "T3"  # low-usage but genuine distributor
        if usage >= 0.35 and workload >= 0.10:
            return "S2"  # secondary scorer (needs ~600+ min)
        return "S3"  # third-option / role player / low minutes

    _hier_role = _pick_hier()
    if _hier_role not in _hier_catalog:
        _hier_role = pick_role("HIERARCHY") or "S3"
    roles.append(_hier_role)

    # T1 scorers with dominant usage are also the primary offensive option — add S1 tag.
    if (
        _hier_role == "T1"
        and usage >= 0.80
        and "S1" in role_catalog.get("HIERARCHY", [])
    ):
        roles.append("S1")

    for section in base_sections[1:]:  # skip HIERARCHY — handled above
        if section == "CORE ROLES" and age >= 36.0 and workload >= 0.50 and iq >= 0.55:
            # Veterans 36+ with meaningful minutes and high IQ should always get VET.
            _vet_available = "VET" in role_catalog.get("CORE ROLES", [])
            if _vet_available:
                roles.append("VET")
                continue
        if section == "CORE ROLES":
            code = pick_core_role()
        elif section == "SCORING STYLES":
            code = pick_scoring_role()
        elif section == "DEFENSE":
            code = pick_defense_role()
        else:
            code = pick_role(section)
        if code:
            roles.append(code)

    if role_catalog:
        alt_ranked = sorted(
            alt_sections, key=lambda s: section_intensity.get(s, 0.0), reverse=True
        )
        for section in alt_ranked:
            if len(roles) >= 5:
                break
            if section == "DRIVE / ATTACK":
                code = pick_drive_role()
            elif section == "SCORING STYLES":
                code = pick_scoring_role()
            elif section == "DEFENSE":
                code = pick_defense_role()
            elif section == "SPECIALIST":
                code = pick_specialist_role()
            else:
                code = pick_role(section)
            if code and code not in roles:
                roles.append(code)

    roles = apply_role_redundancy_and_contradictions(roles)
    fallback_roles = ["ROL", "ROT", "GLUE", "HUST", "DISCIP"]
    for role in fallback_roles:
        if len(roles) >= 5:
            break
        if role not in roles:
            roles.append(role)
    roles = roles[:5]

    unicorn_codes = role_catalog.get("UNICORN ROLES", [])

    def choose_unicorn_code() -> Optional[str]:
        if not unicorn_codes:
            return None
        profile_scores = {
            "TDH": 0.48 * passing
            + 0.22 * usage
            + 0.15 * workload
            + 0.15 * n(orb_pct + drb_pct, 10.0, 48.0),
            "PCE": 0.42 * iq + 0.28 * passing + 0.18 * usage + 0.12 * workload,
            "GRV+": 0.56 * shooting + 0.24 * shot_creation + 0.20 * usage,
            "DSC": 0.66 * defense
            + 0.20 * workload
            + 0.14 * (1.0 if is_big >= 0.5 else 0.0),
            "MME": 0.38 * usage
            + 0.34 * shot_creation
            + 0.16 * mid_touch
            + 0.12 * passing,
            "SCE": 0.42 * usage + 0.36 * shot_creation + 0.22 * shooting,
            "OFF+": 0.38 * usage + 0.30 * iq + 0.20 * passing + 0.12 * shooting,
            "3LV+": 0.40 * shooting + 0.30 * mid_touch + 0.30 * rim_pressure,
            "CLX": 0.42 * usage + 0.34 * iq + 0.24 * n(ft_pct, 0.58, 0.93),
            "VRE": 0.34 * usage + 0.22 * passing + 0.22 * shooting + 0.22 * defense,
        }
        # Minimum score each unicorn type requires to be awarded.
        # These are calibrated so only the truly elite in that dimension qualify.
        min_thresholds = {
            "TDH": 0.62,  # triple-double hub: needs elite passing AND usage AND rebounds
            "PCE": 0.60,  # pace/IQ engine: elite IQ + strong passing
            "GRV+": 0.58,  # gravity: elite shooter with high volume
            "DSC": 0.58,  # defensive specialist: elite defense composite
            "MME": 0.58,  # mismatch engine: high usage + creation + shot-making
            "SCE": 0.60,  # scoring engine: high usage + self-creation + efficiency
            "OFF+": 0.56,  # offensive + : elite usage + IQ + decision-making
            "3LV+": 0.58,  # 3-level versatility: balance of 3pt + mid + rim
            "CLX": 0.58,  # clutch: usage + IQ + FT proficiency
            "VRE": 0.52,  # versatile: balanced across all four dimensions (easiest)
        }
        best_code: Optional[str] = None
        best_score = -1e9
        for code in unicorn_codes:
            base = profile_scores.get(
                code, 0.35 * usage + 0.25 * passing + 0.20 * shooting + 0.20 * defense
            )
            tie_break = stable_side_bias(f"{player_key}:UNICORN:{code}") * 0.01
            score = base + tie_break
            threshold = min_thresholds.get(code, 0.56)
            if score >= threshold and score > best_score:
                best_score = score
                best_code = code
        return best_code

    unicorn_code = choose_unicorn_code()
    elite_primary_creator = usage >= 0.74 and passing >= 0.58 and iq >= 0.62
    elite_primary_scorer = usage >= 0.72 and shooting >= 0.66 and iq >= 0.62
    elite_two_way_star = (
        usage >= 0.66 and defense >= 0.64 and (shooting >= 0.58 or passing >= 0.58)
    )
    all_time_engine = usage >= 0.82 and (passing >= 0.55 or shooting >= 0.62)
    elite_two_way_scorer = (
        shooting >= 0.70 and defense >= 0.40 and iq >= 0.70 and usage >= 0.60
    )
    unicorn_intensity = section_intensity.get("UNICORN ROLES", 0.0)
    creator_lane = elite_primary_creator and unicorn_intensity >= 0.74
    scorer_lane = (
        elite_primary_scorer and unicorn_intensity >= 0.63 and minutes >= 1700.0
    )
    two_way_lane = elite_two_way_star and unicorn_intensity >= 0.68
    legend_lane = all_time_engine and unicorn_intensity >= 0.68
    elite_two_way_scorer_lane = (
        elite_two_way_scorer and unicorn_intensity >= 0.58 and minutes >= 1700.0
    )
    unicorn_eligibility = (minutes >= 1100.0) and (
        creator_lane
        or scorer_lane
        or two_way_lane
        or legend_lane
        or elite_two_way_scorer_lane
    )
    if unicorn_code and unicorn_eligibility and unicorn_code not in roles:
        roles.append(unicorn_code)

    return roles


def to_attr(value_0_100: float) -> int:
    value = clamp(value_0_100, 0.0, 100.0)
    mapped = 25.0 + (0.72 * value)
    if value >= 70.0:
        mapped += 0.15 * (value - 70.0)
    return int(round(clamp(mapped, ATTRIBUTE_MIN, ATTRIBUTE_MAX)))


def build_role_modifier_deltas(
    role_catalog: Dict[str, List[str]],
) -> Dict[str, Dict[str, int]]:
    section_defaults: Dict[str, Dict[str, int]] = {
        "HIERARCHY": {"Offensive Consistency": 1},
        "CORE ROLES": {"Offensive Consistency": 1},
        "SCORING STYLES": {
            "Three-Point Shot": 1,
            "Mid-Range Shot": 1,
            "Driving Layup": 1,
        },
        "DRIVE / ATTACK": {"Speed with Ball": 1, "Driving Layup": 1, "Ball Handle": 1},
        "DEFENSE": {
            "Perimeter Defense": 1,
            "Interior Defense": 1,
            "Help Defense IQ": 1,
            "Defensive Consistency": 1,
        },
        "IQ / CONTROL": {"Pass IQ": 1, "Offensive Consistency": 1},
        "UTILITY": {"Hustle": 1, "Defensive Consistency": 1},
        "SPECIALIST": {"Pass IQ": 1, "Offensive Consistency": 1},
        "UNICORN ROLES": {
            "Ball Handle": 2,
            "Pass Vision": 2,
            "Offensive Consistency": 2,
        },
    }

    deltas: Dict[str, Dict[str, int]] = {}
    for section_name, role_codes in role_catalog.items():
        base_delta = section_defaults.get(section_name.upper(), {})
        for role_code in role_codes:
            if role_code not in deltas:
                deltas[role_code] = dict(base_delta)

    overrides: Dict[str, Dict[str, int]] = {
        "T1": {"Ball Handle": 4, "Pass Accuracy": 4, "Pass IQ": 5, "Pass Vision": 5},
        "T2": {"Ball Handle": 3, "Pass Accuracy": 3, "Pass IQ": 3, "Pass Vision": 3},
        "T3": {
            "Pass Accuracy": 2,
            "Pass IQ": 2,
            "Pass Vision": 2,
            "Offensive Consistency": 1,
        },
        "S1": {"Offensive Consistency": 4},
        "S2": {"Offensive Consistency": 2},
        "S3": {"Offensive Consistency": 1},
        "CON": {"Pass Accuracy": 3, "Pass IQ": 3, "Pass Vision": 3},
        "ISO": {"Ball Handle": 4, "Speed with Ball": 3},
        "SPT": {"Three-Point Shot": 3},
        "CLO": {"Offensive Consistency": 3},
        "SLH": {"Driving Layup": 4, "Draw Foul": 4, "Speed with Ball": 2},
        "3L": {"Three-Point Shot": 4, "Mid-Range Shot": 4, "Driving Layup": 2},
        "SHO": {"Three-Point Shot": 12, "Mid-Range Shot": 2},
        "SHH": {"Offensive Consistency": 2},
        "MOV": {"Three-Point Shot": 4, "Agility": 2},
        "MID": {"Mid-Range Shot": 5, "Post Fade": 2},
        "RR": {"Standing Dunk": 3, "Driving Dunk": 4, "Close Shot": 2},
        "FIN": {"Driving Layup": 3, "Close Shot": 2, "Draw Foul": 2},
        "PBF": {"Offensive Rebound": 3, "Close Shot": 2, "Hands": 2},
        "STB": {"Three-Point Shot": 3, "Mid-Range Shot": 2, "Post Control": 1},
        "POP": {"Three-Point Shot": 3, "Mid-Range Shot": 2},
        "FAC": {"Mid-Range Shot": 3, "Post Control": 2, "Ball Handle": 1},
        "LOB": {"Driving Dunk": 3, "Vertical": 3, "Hands": 2},
        "PNR": {"Standing Dunk": 5, "Hands": 3, "Close Shot": 2},
        "ISO3": {"Three-Point Shot": 3, "Ball Handle": 2, "Speed with Ball": 2},
        "PST": {"Post Hook": 4, "Post Fade": 4, "Post Control": 5, "Strength": 2},
        "CUT": {"Driving Layup": 3, "Close Shot": 2, "Hustle": 1},
        "REL": {"Three-Point Shot": 3, "Agility": 2},
        "FLO": {"Driving Layup": 2, "Close Shot": 2},
        "ARC": {"Three-Point Shot": 4},
        "DUNK": {"Driving Dunk": 4, "Vertical": 2, "Draw Foul": 1},
        "PULL": {"Three-Point Shot": 3, "Mid-Range Shot": 2, "Ball Handle": 1},
        "C&S": {"Three-Point Shot": 4},
        "STEP": {"Three-Point Shot": 2, "Mid-Range Shot": 2, "Ball Handle": 2},
        "POA": {"Perimeter Defense": 4, "Steal": 2, "Defensive Consistency": 3},
        "LOCK": {"Perimeter Defense": 4, "Steal": 3, "Help Defense IQ": 2},
        "BHW": {"Steal": 3, "Pass Perception": 3, "Perimeter Defense": 2},
        "ANCH": {
            "Interior Defense": 4,
            "Block": 7,
            "Help Defense IQ": 3,
            "Defensive Rebound": 4,
        },
        "RIMD": {
            "Interior Defense": 3,
            "Block": 6,
            "Help Defense IQ": 2,
            "Defensive Rebound": 2,
        },
        "SWI": {"Perimeter Defense": 2, "Interior Defense": 2, "Help Defense IQ": 2},
        "GLS": {"Defensive Rebound": 4, "Offensive Rebound": 3, "Strength": 2},
        "BLW": {"Speed": 3, "Agility": 3, "Speed with Ball": 3},
        "BUL": {"Strength": 4, "Post Control": 2, "Driving Layup": 1},
        "HFL": {"Vertical": 5, "Driving Dunk": 3, "Block": 2},
        "PHY": {"Draw Foul": 4, "Strength": 2, "Offensive Consistency": 1},
        "CTL": {"Pass IQ": 3, "Offensive Consistency": 2},
        "PSS": {"Pass Accuracy": 5, "Pass IQ": 5, "Pass Vision": 6},
        "ORCH": {"Pass Accuracy": 4, "Pass IQ": 4, "Pass Vision": 5},
        "VISION": {"Pass Vision": 5, "Pass IQ": 3},
        "SETUP": {"Pass Accuracy": 3, "Pass Vision": 4},
        "MIC": {"Three-Point Shot": 2},
        "SCE": {"Ball Handle": 4, "Offensive Consistency": 5, "Pass Vision": 2},
        "TDH": {
            "Pass Vision": 5,
            "Pass IQ": 4,
            "Defensive Rebound": 3,
            "Offensive Rebound": 2,
        },
        "DSC": {"Block": 4, "Help Defense IQ": 4, "Pass Perception": 3},
        "PCE": {"Pass IQ": 3, "Stamina": 2},
        "MME": {"Ball Handle": 3, "Post Control": 3},
        "OFF+": {"Offensive Consistency": 4, "Pass Vision": 2},
        "3LV+": {"Three-Point Shot": 4, "Mid-Range Shot": 3, "Driving Layup": 2},
        "CLX": {"Offensive Consistency": 4},
        "VRE": {
            "Perimeter Defense": 2,
            "Interior Defense": 2,
            "Pass IQ": 2,
            "Offensive Consistency": 2,
        },
    }

    for role_code, override_delta in overrides.items():
        deltas.setdefault(role_code, {})
        for attr_name, delta in override_delta.items():
            deltas[role_code][attr_name] = deltas[role_code].get(attr_name, 0) + delta

    return deltas


def apply_role_modifiers(
    attribute_values: Dict[str, int],
    roles: List[str],
    role_catalog: Dict[str, List[str]],
) -> Dict[str, int]:
    deltas = build_role_modifier_deltas(role_catalog)
    out = dict(attribute_values)
    for role in roles:
        for attr_name, delta in deltas.get(role, {}).items():
            if delta <= 0:
                # Project rule: role tags should not reduce attributes.
                continue
            headroom = ATTRIBUTE_MAX - out[attr_name]
            boost_scale = remap(headroom, 0.0, 30.0, 0.0, 1.0)
            # Global role tuning: strengthen all positive boosts by +1.
            boosted_delta = delta + 1
            applied_delta = int(round(boosted_delta * boost_scale))
            if applied_delta <= 0 and headroom > 0:
                applied_delta = 1
            out[attr_name] = int(
                clamp(out[attr_name] + applied_delta, ATTRIBUTE_MIN, ATTRIBUTE_MAX)
            )
    return out


def compute_attributes(
    row: Dict[str, Any],
    tendencies: List[TendencyResult],
    player_roles_dir: str,
    all_rows: Optional[List[Dict[str, Any]]] = None,
    badges_txt_path: str = "",
) -> Dict[str, Any]:
    blended_row = dict(row)

    role_catalog = load_role_catalog(player_roles_dir)
    attr_definitions = load_attribute_definitions(player_roles_dir)
    player_rows: List[Dict[str, Any]] = []

    durability_availability_score = 70.0
    ironman_seasons = 0
    defense_peak_signal = 0.0
    dunk_positional_score = 0.0
    same_season: List[Dict[str, Any]] = []
    same_bucket: List[Dict[str, Any]] = []
    season_max_games = 82.0
    heavy_minute_pool: List[Dict[str, Any]] = []
    heavy_mpg_threshold = 30.0

    if all_rows:
        season_label = str(row.get("season_label", "")).strip()
        season_ctx = _build_season_context(all_rows, season_label)
        player_ctx = _build_player_context(row, all_rows, season_ctx)

        player_rows = player_ctx["player_rows"]
        durability_availability_score = player_ctx["durability_availability_score"]
        ironman_seasons = player_ctx["ironman_seasons"]
        defense_peak_signal = player_ctx["defense_peak_signal"]
        dunk_positional_score = player_ctx["dunk_positional_score"]
        same_season = player_ctx["same_season"]
        same_bucket = player_ctx["bucket_rows"]
        season_max_games = player_ctx["season_max_games"]
        heavy_minute_pool = season_ctx["heavy_minute_pool"]
        heavy_mpg_threshold = season_ctx["heavy_mpg_threshold"]

    usg = as_float(blended_row, "advanced_usg_percent")
    ast_pct = as_float(blended_row, "advanced_ast_percent")
    ast100 = as_float(blended_row, "per_100_ast_per_100_poss")
    tov_pct = as_float(blended_row, "advanced_tov_percent")
    orb_pct = as_float(blended_row, "advanced_orb_percent")
    drb_pct = as_float(blended_row, "advanced_drb_percent")
    stl_pct = as_float(blended_row, "advanced_stl_percent")
    blk_pct = as_float(blended_row, "advanced_blk_percent")
    fta36 = as_float(blended_row, "per_36_fta_per_36_min")
    fg3a36 = as_float(blended_row, "per_36_x3pa_per_36_min")
    fg3a_pg = as_float(blended_row, "per_game_x3pa_per_game")
    fga36 = as_float(blended_row, "per_36_fga_per_36_min")
    three_pct = as_float(
        blended_row, "per_36_x3p_percent", as_float(blended_row, "per_game_x3p_percent")
    )
    two_pct = as_float(
        blended_row, "per_36_x2p_percent", as_float(blended_row, "per_game_x2p_percent")
    )
    efg_pct = as_float(
        blended_row,
        "per_36_e_fg_percent",
        as_float(blended_row, "per_game_e_fg_percent"),
    )
    ts_pct = as_float(blended_row, "advanced_ts_percent", efg_pct)
    ft_pct = as_float(
        blended_row, "per_36_ft_percent", as_float(blended_row, "per_game_ft_percent")
    )
    assisted2 = as_float(blended_row, "shooting_percent_assisted_x2p_fg")
    assisted3 = as_float(blended_row, "shooting_percent_assisted_x3p_fg")
    rim_share = as_float(blended_row, "shooting_percent_fga_from_x0_3_range")
    close_share = as_float(blended_row, "shooting_percent_fga_from_x3_10_range")
    mid_share = as_float(blended_row, "shooting_percent_fga_from_x10_16_range")
    long_mid_share = as_float(blended_row, "shooting_percent_fga_from_x16_3p_range")
    three_share = as_float(blended_row, "shooting_percent_fga_from_x3p_range")
    corner_three_share = as_float(blended_row, "shooting_percent_corner_3s_of_3pa")
    hook_freq = as_float(blended_row, "pbp_features_hook_freq")
    fade_freq = as_float(blended_row, "pbp_features_fadeaway_freq")
    tracking_passes_made_pg = as_float(blended_row, "tracking_passes_made_pg")
    tracking_potential_ast_pg = as_float(blended_row, "tracking_potential_ast_pg")
    tracking_ast_adj_pg = as_float(blended_row, "tracking_ast_adj_pg")
    tracking_secondary_ast_pg = as_float(blended_row, "tracking_secondary_ast_pg")
    tracking_ft_ast_pg = as_float(blended_row, "tracking_ft_ast_pg")
    tracking_ast_to_pass_pct = as_float(blended_row, "tracking_ast_to_pass_pct")
    tracking_ast_to_pass_pct_adj = as_float(
        blended_row, "tracking_ast_to_pass_pct_adj", tracking_ast_to_pass_pct
    )
    tracking_touches_pg = as_float(blended_row, "tracking_touches_pg")
    tracking_front_ct_touches_pg = as_float(blended_row, "tracking_front_ct_touches_pg")
    tracking_time_of_poss_pg = as_float(blended_row, "tracking_time_of_poss_pg")
    tracking_avg_sec_per_touch = as_float(blended_row, "tracking_avg_sec_per_touch")
    tracking_avg_drib_per_touch = as_float(blended_row, "tracking_avg_drib_per_touch")
    tracking_drives_pg = as_float(blended_row, "tracking_drives_pg")
    tracking_drive_passes_pg = as_float(blended_row, "tracking_drive_passes_pg")
    tracking_drive_ast_pg = as_float(blended_row, "tracking_drive_ast_pg")
    tracking_drive_pass_rate = as_float(blended_row, "tracking_drive_pass_rate")
    tracking_drive_ast_rate = as_float(blended_row, "tracking_drive_ast_rate")
    tracking_drive_fg_pct = as_float(blended_row, "tracking_drive_fg_pct")
    tracking_drive_tov_pct = as_float(blended_row, "tracking_drive_tov_pct")
    tracking_avg_speed = as_float(blended_row, "tracking_avg_speed")
    tracking_avg_speed_off = as_float(
        blended_row, "tracking_avg_speed_off", tracking_avg_speed
    )
    tracking_avg_speed_def = as_float(
        blended_row, "tracking_avg_speed_def", tracking_avg_speed
    )
    tracking_dist_miles_pg = as_float(blended_row, "tracking_dist_miles_pg")
    tracking_dist_miles_off_pg = as_float(blended_row, "tracking_dist_miles_off_pg")
    tracking_dist_miles_def_pg = as_float(blended_row, "tracking_dist_miles_def_pg")
    hustle_contested_shots_pg = as_float(blended_row, "hustle_contested_shots_pg")
    hustle_contested_2pt_pg = as_float(blended_row, "hustle_contested_2pt_pg")
    hustle_contested_3pt_pg = as_float(blended_row, "hustle_contested_3pt_pg")
    hustle_deflections_pg = as_float(blended_row, "hustle_deflections_pg")
    hustle_charges_drawn_pg = as_float(blended_row, "hustle_charges_drawn_pg")
    hustle_loose_balls_recovered_def_pg = as_float(
        blended_row, "hustle_loose_balls_recovered_def_pg"
    )
    defense_dash_overall_stop_delta = as_float(
        blended_row, "defense_dash_overall_stop_delta"
    )
    defense_dash_overall_plusminus = as_float(
        blended_row, "defense_dash_overall_plusminus"
    )
    defense_dash_3pt_stop_delta = as_float(blended_row, "defense_dash_3pt_stop_delta")
    defense_dash_3pt_plusminus = as_float(blended_row, "defense_dash_3pt_plusminus")
    defense_dash_2pt_stop_delta = as_float(blended_row, "defense_dash_2pt_stop_delta")
    defense_dash_2pt_plusminus = as_float(blended_row, "defense_dash_2pt_plusminus")
    defense_dash_lt6_stop_delta = as_float(blended_row, "defense_dash_lt6_stop_delta")
    defense_dash_lt6_plusminus = as_float(blended_row, "defense_dash_lt6_plusminus")
    dunks_share = as_float(blended_row, "shooting_percent_dunks_of_fga")
    dunks = as_float(blended_row, "shooting_num_of_dunks")
    minutes = as_float(blended_row, "totals_mp")
    mpg = as_float(blended_row, "per_game_mp_per_game")
    pf100 = as_float(blended_row, "per_100_pf_per_100_poss")
    dws = as_float(blended_row, "advanced_dws")
    dbpm = as_float(blended_row, "advanced_dbpm")
    age = as_float(blended_row, "age", 27.0)
    position = str(blended_row.get("position", ""))
    is_big_score = 100.0 if (("C" in position) or ("PF" in position)) else 0.0
    is_guard_score = 100.0 if (("PG" in position) or ("SG" in position)) else 0.0
    is_center_score = (
        100.0
        if (("C" in position) and ("PF" not in position))
        else (55.0 if ("C" in position) else 0.0)
    )
    is_wing_forward_score = 100.0 if (("SF" in position) or ("PF" in position)) else 0.0
    non_guard_score = remap(1.0 - is_guard_score / 100.0, 0.0, 1.0, 0.0, 100.0)
    is_guard = any(x in position for x in ("PG", "SG"))
    is_forward = any(x in position for x in ("SF", "PF"))

    # New CSV data loads.
    transition_poss_pct = as_float(blended_row, "playtype_transition_poss_pct")
    misc_pfd_pg = as_float(blended_row, "misc_pfd_pg")
    misc_pts_paint_pg = as_float(blended_row, "misc_pts_paint_pg")
    elbow_touches_pg = as_float(blended_row, "tracking_elbow_touches_pg")
    shot_dash_touch_lt2_efg = as_float(blended_row, "shot_dash_touch_lt2_efg")

    usage_score = remap(usg, 12.0, 35.0, 0.0, 100.0)
    creation_2_score = remap(1.0 - assisted2, 0.10, 0.85, 0.0, 100.0)
    creation_3_score = remap(1.0 - assisted3, 0.10, 0.85, 0.0, 100.0)
    efficiency_score = remap(ts_pct, 0.48, 0.68, 0.0, 100.0)
    touch_score = remap(ft_pct, 0.58, 0.93, 0.0, 100.0)
    turnover_control = remap(
        1.0 - remap(tov_pct, 8.0, 20.0, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0
    )
    workload_score = remap(minutes, 350.0, 3000.0, 0.0, 100.0)
    play_gravity_score = 0.60 * remap(three_pct, 0.30, 0.41, 0.0, 100.0) + 0.40 * remap(
        fg3a_pg, 0.5, 8.0, 0.0, 100.0
    )
    burst_score = 0.62 * remap(rim_share, 0.10, 0.55, 0.0, 100.0) + 0.38 * remap(
        dunks_share, 0.00, 0.14, 0.0, 100.0
    )
    handle_pace_score = (
        0.40 * creation_2_score
        + 0.28 * creation_3_score
        + 0.18 * turnover_control
        + 0.14 * burst_score
    )
    live_dribble_creation_score = (
        0.46 * creation_2_score + 0.34 * creation_3_score + 0.20 * turnover_control
    )
    downhill_pressure_score = (
        0.54 * remap(rim_share, 0.10, 0.55, 0.0, 100.0)
        + 0.30 * remap(fta36, 1.0, 12.0, 0.0, 100.0)
        + 0.16 * remap(mpg, 8.0, 38.0, 0.0, 100.0)
    )
    shot_discipline_score = (
        0.46 * remap(1.0 - remap(usg, 14.0, 34.0, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0)
        + 0.24 * remap(assisted2, 0.20, 0.90, 0.0, 100.0)
        + 0.18 * remap(assisted3, 0.20, 0.98, 0.0, 100.0)
        + 0.12 * turnover_control
    )
    shot_quality_score = (
        0.44 * remap(ts_pct, 0.52, 0.66, 0.0, 100.0)
        + 0.26 * remap(efg_pct, 0.48, 0.62, 0.0, 100.0)
        + 0.18 * remap(two_pct, 0.46, 0.67, 0.0, 100.0)
        + 0.12 * remap(ft_pct, 0.60, 0.90, 0.0, 100.0)
    )
    role_player_shot_selection_signal = (
        0.52 * remap(1.0 - remap(usg, 14.0, 30.0, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0)
        + 0.28 * remap(assisted2 + assisted3, 0.55, 1.70, 0.0, 100.0)
        + 0.20 * remap(ts_pct, 0.52, 0.66, 0.0, 100.0)
    )
    creator_shot_difficulty_signal = (
        0.50 * remap(usg, 20.0, 36.0, 0.0, 100.0)
        + 0.28 * creation_2_score
        + 0.22 * remap(1.0 - assisted2, 0.10, 0.85, 0.0, 100.0)
    )
    star_shotmaking_signal = (
        0.44 * shot_quality_score
        + 0.32 * creation_2_score
        + 0.14 * remap(ft_pct, 0.60, 0.90, 0.0, 100.0)
        + 0.10 * usage_score
    )
    offensive_load_score = remap((usg * ast_pct) / 100.0, 1.0, 12.0, 0.0, 100.0)
    defensive_focus_score = remap(
        1.0 - remap(usg, 14.0, 34.0, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0
    )
    load_penalty_scale = remap(is_guard_score + is_center_score, 0.0, 200.0, 0.35, 1.0)
    wing_guard_score = max(is_guard_score, is_wing_forward_score)
    age_explosiveness_score = remap(
        1.0 - remap(age, 21.0, 37.0, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0
    )
    dunk_volume_wing_guard_score = remap(dunks, 0.0, 80.0, 0.0, 100.0)
    dunk_share_wing_guard_score = remap(dunks_share, 0.01, 0.09, 0.0, 100.0)
    rim_pressure_score = 0.55 * remap(rim_share, 0.12, 0.60, 0.0, 100.0) + 0.45 * remap(
        fta36, 1.0, 12.0, 0.0, 100.0
    )
    wing_stopper_score = 0.65 * remap(stl_pct, 0.3, 3.5, 0.0, 100.0) + 0.35 * remap(
        blk_pct, 0.2, 4.0, 0.0, 100.0
    )
    poa_specialist_score = (
        0.52 * defensive_focus_score
        + 0.28 * is_guard_score
        + 0.20 * remap(stl_pct, 0.3, 3.5, 0.0, 100.0)
    )
    physical_explosiveness_score = (
        0.34 * remap(dunks_share, 0.00, 0.16, 0.0, 100.0)
        + 0.24 * remap(dunks, 0.0, 180.0, 0.0, 100.0)
        + 0.22 * remap(rim_share, 0.10, 0.60, 0.0, 100.0)
        + 0.20 * remap(fta36, 1.0, 12.0, 0.0, 100.0)
    )
    physical_mobility_score = (
        0.36 * remap(stl_pct, 0.3, 3.5, 0.0, 100.0)
        + 0.22 * remap(1.0 - remap(pf100, 1.0, 5.5, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0)
        + 0.22 * remap(mpg, 8.0, 38.0, 0.0, 100.0)
        + 0.20 * workload_score
    )
    guard_quickness_score = remap(
        is_guard_score
        * (
            0.34 * remap(stl_pct, 0.3, 3.5, 0.0, 100.0)
            + 0.24 * turnover_control
            + 0.22 * creation_2_score
            + 0.20 * remap(mpg, 8.0, 38.0, 0.0, 100.0)
        )
        / 100.0,
        0.0,
        100.0,
        0.0,
        100.0,
    )
    guard_downhill_speed_score = remap(
        is_guard_score
        * (
            0.15 * usage_score
            + 0.85
            * remap(1.0 - remap(ast_pct, 14.0, 36.0, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0)
        )
        / 100.0,
        0.0,
        100.0,
        0.0,
        100.0,
    )
    size_drag_score = remap(
        (0.70 * is_big_score) + (0.30 * remap(drb_pct, 8.0, 32.0, 0.0, 100.0)),
        0.0,
        100.0,
        0.0,
        100.0,
    )
    dunk_positional_score = dunk_positional_score  # Already computed from cache above

    guard_wing_explosive_score = remap(
        max(is_guard_score, is_wing_forward_score)
        * ((0.55 * dunk_positional_score) + (0.45 * physical_explosiveness_score))
        / 100.0,
        0.0,
        100.0,
        0.0,
        100.0,
    )

    raw: Dict[str, float] = {
        "Driving Layup": (
            0.24 * remap(rim_share, 0.12, 0.52, 0.0, 100.0)
            + 0.20 * remap(fta36, 1.0, 12.0, 0.0, 100.0)
            + 0.18 * remap(two_pct, 0.46, 0.67, 0.0, 100.0)
            + 0.14 * usage_score
            + 0.12 * creation_2_score
            + 0.08 * remap(mpg, 8.0, 38.0, 0.0, 100.0)
            + 0.04 * touch_score
        ),
        "Standing Dunk": (
            0.46 * remap(dunks_share, 0.00, 0.14, 0.0, 100.0)
            + 0.18 * remap(dunks, 0.0, 250.0, 0.0, 100.0)
            + 0.12 * remap(rim_share, 0.12, 0.60, 0.0, 100.0)
            + 0.20 * is_big_score
            + 0.08 * non_guard_score
            - 0.04 * is_guard_score
        ),
        "Driving Dunk": (
            0.24 * remap(dunks_share, 0.00, 0.14, 0.0, 100.0)
            + 0.18 * remap(dunks, 0.0, 250.0, 0.0, 100.0)
            + 0.16 * rim_pressure_score
            + 0.10
            * remap(usage_score * (1.0 - is_big_score / 100.0), 0.0, 100.0, 0.0, 100.0)
            + 0.22
            * remap(
                wing_guard_score * dunk_volume_wing_guard_score / 100.0,
                0.0,
                100.0,
                0.0,
                100.0,
            )
            + 0.10
            * remap(
                wing_guard_score * dunk_share_wing_guard_score / 100.0,
                0.0,
                100.0,
                0.0,
                100.0,
            )
            + 0.04
            * remap(
                wing_guard_score * age_explosiveness_score / 100.0,
                0.0,
                100.0,
                0.0,
                100.0,
            )
            + (0.12 + 0.12 * (is_guard_score / 100.0)) * dunk_positional_score
        ),
        "Close Shot": (
            0.34 * remap(close_share + rim_share, 0.18, 0.72, 0.0, 100.0)
            + 0.24 * remap(two_pct, 0.46, 0.67, 0.0, 100.0)
            + 0.20 * touch_score
            + 0.12 * remap(fta36, 1.0, 12.0, 0.0, 100.0)
            + 0.10 * usage_score
        ),
        "Mid-Range Shot": (
            0.34 * remap(ft_pct, 0.65, 0.92, 0.0, 100.0)
            + 0.30 * usage_score
            + 0.24 * remap(mid_share + long_mid_share, 0.06, 0.45, 0.0, 100.0)
            + 0.12 * remap(two_pct, 0.46, 0.67, 0.0, 100.0)
        ),
        "Three-Point Shot": (
            0.34 * remap(three_pct, 0.30, 0.41, 0.0, 100.0)
            + 0.26 * remap(fg3a_pg, 0.5, 8.0, 0.0, 100.0)
            + 0.14 * remap(fg3a36, 0.4, 13.0, 0.0, 100.0)
            + 0.14 * creation_3_score
            + 0.12
            * max(
                remap(corner_three_share, 0.10, 0.40, 0.0, 100.0),
                creation_3_score
                * 0.65,  # pull-up creators shouldn't be penalized for skipping corner 3s
            )
        ),
        "Free Throw": (
            0.90 * remap(ft_pct, 0.58, 0.93, 0.0, 100.0)
            + 0.10 * remap(fta36, 0.8, 12.0, 0.0, 100.0)
        ),
        "Post Hook": (
            0.32 * is_big_score
            + 0.28 * remap(close_share, 0.05, 0.35, 0.0, 100.0)
            + 0.24 * touch_score
            + 0.16 * remap(two_pct, 0.46, 0.67, 0.0, 100.0)
        ),
        "Post Fade": (
            0.36 * remap(mid_share + long_mid_share, 0.06, 0.45, 0.0, 100.0)
            + 0.34 * touch_score
            + 0.18 * usage_score
            + 0.12 * is_big_score
        ),
        "Post Control": (
            0.34 * is_big_score
            + 0.24 * remap(rim_share + close_share, 0.18, 0.72, 0.0, 100.0)
            + 0.22 * usage_score
            + 0.20 * remap(fta36, 1.0, 12.0, 0.0, 100.0)
        ),
        "Draw Foul": (
            0.42 * remap(fta36, 1.0, 12.0, 0.0, 100.0)
            + 0.22 * usage_score
            + 0.18 * remap(rim_share, 0.12, 0.52, 0.0, 100.0)
            + 0.18 * creation_2_score
        ),
        "Shot IQ": (0.62 * shot_discipline_score + 0.38 * shot_quality_score),
        "Ball Handle": (
            0.38 * live_dribble_creation_score
            + 0.22 * turnover_control
            + 0.16 * usage_score
            + 0.14 * remap(ast_pct, 4.0, 40.0, 0.0, 100.0)
            + 0.10 * handle_pace_score
        ),
        "Speed with Ball": (
            0.18 * downhill_pressure_score
            + 0.18 * burst_score
            + 0.24 * handle_pace_score
            + 0.16 * creation_2_score
            + 0.14 * creation_3_score
            + 0.06 * is_guard_score
            + 0.04 * turnover_control
        ),
        "Hands": (
            0.24 * remap(close_share + rim_share, 0.18, 0.72, 0.0, 100.0)
            + 0.12 * remap(dunks_share, 0.00, 0.14, 0.0, 100.0)
            + 0.16 * remap(two_pct, 0.46, 0.67, 0.0, 100.0)
            + 0.22 * workload_score
            + 0.16 * turnover_control
            + 0.10 * remap(ast_pct, 5.0, 42.0, 0.0, 100.0)
        ),
        "Pass Accuracy": (
            0.30 * remap(ast100, 2.0, 14.0, 0.0, 100.0)
            + 0.26 * remap(ast_pct, 5.0, 42.0, 0.0, 100.0)
            + 0.18 * turnover_control
            + 0.12
            * remap(
                usage_score * remap(ast_pct, 5.0, 42.0, 0.0, 1.0),
                0.0,
                100.0,
                0.0,
                100.0,
            )
            + 0.14 * play_gravity_score
        ),
        "Pass IQ": (
            0.24 * remap(ast_pct, 5.0, 42.0, 0.0, 100.0)
            + 0.24 * remap(ast100, 2.0, 14.0, 0.0, 100.0)
            + 0.20 * turnover_control
            + 0.18 * remap(usage_score, 0.0, 100.0, 0.0, 100.0)
            + 0.14 * efficiency_score
        ),
        "Pass Vision": (
            0.34 * remap(ast_pct, 5.0, 42.0, 0.0, 100.0)
            + 0.26 * remap(ast100, 2.0, 14.0, 0.0, 100.0)
            + 0.18 * usage_score
            + 0.12 * remap(1.0 - assisted2, 0.10, 0.85, 0.0, 100.0)
            + 0.10 * play_gravity_score
        ),
        "Offensive Consistency": (
            0.50 * usage_score
            + 0.30 * remap(ts_pct, 0.54, 0.68, 0.0, 100.0)
            + 0.20 * remap(efg_pct, 0.44, 0.64, 0.0, 100.0)
        ),
        "Interior Defense": (
            0.36 * remap(blk_pct, 0.2, 10.0, 0.0, 100.0)
            + 0.28 * remap(drb_pct, 8.0, 32.0, 0.0, 100.0)
            + 0.22 * is_big_score
            + 0.14 * remap(pf100, 1.0, 5.5, 0.0, 100.0)
        ),
        "Perimeter Defense": (
            0.14 * remap(stl_pct, 0.3, 3.5, 0.0, 100.0)
            + 0.24 * wing_stopper_score
            + 0.08 * remap(blk_pct, 0.2, 4.0, 0.0, 100.0)
            + 0.10 * remap(1.0 - is_big_score / 100.0, 0.0, 1.0, 0.0, 100.0)
            + 0.08 * is_guard_score
            + 0.12 * remap(minutes, 350.0, 3000.0, 0.0, 100.0)
            + 0.18 * defensive_focus_score
            + 0.14 * is_wing_forward_score
            + 0.12 * poa_specialist_score
            - 0.18 * offensive_load_score * load_penalty_scale
            - 0.16 * is_center_score
        ),
        "Steal": (
            0.74 * remap(stl_pct, 0.3, 3.5, 0.0, 100.0)
            + 0.12 * is_guard_score
            + 0.08 * remap(1.0 - is_big_score / 100.0, 0.0, 1.0, 0.0, 100.0)
            + 0.06 * workload_score
            - 0.08 * offensive_load_score
        ),
        "Block": (
            0.72 * remap(blk_pct, 0.2, 10.0, 0.0, 100.0)
            + 0.14 * is_big_score
            + 0.08 * remap(drb_pct, 8.0, 32.0, 0.0, 100.0)
            + 0.08 * non_guard_score
            + 0.06 * workload_score
            - 0.08 * is_guard_score
        ),
        "Offensive Rebound": (
            0.74 * remap(orb_pct, 1.0, 18.0, 0.0, 100.0)
            + 0.16 * is_big_score
            + 0.06 * remap(drb_pct, 8.0, 32.0, 0.0, 100.0)
            + 0.04 * workload_score
            + 0.08 * non_guard_score
            - 0.04 * is_guard_score
        ),
        "Defensive Rebound": (
            0.56 * remap(drb_pct, 8.0, 32.0, 0.0, 100.0)
            + 0.18 * is_big_score
            + 0.16 * workload_score
            + 0.10 * remap(orb_pct, 1.0, 10.0, 0.0, 100.0)
            + 0.10 * non_guard_score
        ),
        "Help Defense IQ": (
            0.24 * remap(blk_pct, 0.2, 10.0, 0.0, 100.0)
            + 0.16 * remap(stl_pct, 0.3, 3.5, 0.0, 100.0)
            + 0.16 * remap(drb_pct, 8.0, 32.0, 0.0, 100.0)
            + 0.12 * workload_score
            + 0.10 * is_big_score
            + 0.16 * wing_stopper_score
            + 0.12 * defensive_focus_score
            - 0.06 * offensive_load_score
        ),
        "Pass Perception": (
            0.62 * remap(stl_pct, 0.3, 3.5, 0.0, 100.0)
            + 0.16 * remap(blk_pct, 0.2, 4.0, 0.0, 100.0)
            + 0.12 * workload_score
            + 0.10 * is_guard_score
        ),
        "Defensive Consistency": (
            0.34 * remap(stl_pct + blk_pct, 0.5, 9.0, 0.0, 100.0)
            + 0.34 * workload_score
            + 0.18 * turnover_control
            + 0.14 * remap(drb_pct, 8.0, 32.0, 0.0, 100.0)
        ),
        "Speed": (
            0.20 * physical_mobility_score
            + 0.10 * physical_explosiveness_score
            + 0.10 * creation_2_score
            + 0.08 * is_guard_score
            + 0.12 * is_wing_forward_score
            + 0.10 * remap(1.0 - is_center_score / 100.0, 0.0, 1.0, 0.0, 100.0)
            + 0.04 * guard_wing_explosive_score
            + 0.16 * guard_quickness_score
            + 0.24 * guard_downhill_speed_score
            - 0.04 * size_drag_score
        ),
        "Agility": (
            0.30 * creation_2_score
            + 0.24 * physical_mobility_score
            + 0.16 * remap(stl_pct, 0.3, 3.5, 0.0, 100.0)
            + 0.10 * is_guard_score
            + 0.10 * is_wing_forward_score
            + 0.10 * remap(1.0 - is_center_score / 100.0, 0.0, 1.0, 0.0, 100.0)
        ),
        "Strength": (
            0.28 * is_big_score
            + 0.20 * non_guard_score
            + 0.22 * remap(drb_pct, 8.0, 32.0, 0.0, 100.0)
            + 0.14 * remap(fta36, 1.0, 12.0, 0.0, 100.0)
            + 0.10 * workload_score
            + 0.06 * remap(pf100, 1.0, 5.5, 0.0, 100.0)
        ),
        "Vertical": (
            0.26 * physical_explosiveness_score
            + 0.22 * remap(dunks_share, 0.00, 0.14, 0.0, 100.0)
            + 0.18 * remap(blk_pct, 0.2, 10.0, 0.0, 100.0)
            + 0.14 * remap(rim_share, 0.12, 0.60, 0.0, 100.0)
            + 0.12 * remap(1.0 - is_center_score / 100.0, 0.0, 1.0, 0.0, 100.0)
            + 0.08
            * remap(
                wing_guard_score * dunk_positional_score / 100.0, 0.0, 100.0, 0.0, 100.0
            )
            + 0.10 * guard_wing_explosive_score
        ),
        "Stamina": (
            0.52 * workload_score
            + 0.20 * remap(mpg, 8.0, 38.0, 0.0, 100.0)
            + 0.16 * usage_score
            + 0.12 * efficiency_score
        ),
        "Intangibles": (25.0),
        "Hustle": (
            0.28 * remap(orb_pct + drb_pct, 10.0, 48.0, 0.0, 100.0)
            + 0.20 * remap(stl_pct + blk_pct, 0.5, 9.0, 0.0, 100.0)
            + 0.16 * workload_score
            + 0.12 * remap(minutes, 350.0, 3000.0, 0.0, 100.0)
            + 0.10 * physical_mobility_score
            + 0.08 * defensive_focus_score
            + 0.06 * remap(pf100, 1.0, 5.5, 0.0, 100.0)
        ),
        "Overall Durability": (
            0.84 * durability_availability_score
            + 0.10 * remap(mpg, 8.0, 38.0, 0.0, 100.0)
            + 0.06 * remap(1.0 - remap(age, 19.0, 38.0, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0)
        ),
        "Potential": (
            0.56 * remap(1.0 - remap(age, 19.0, 34.0, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0)
            + 0.14 * creation_2_score
            + 0.08 * remap(ast_pct, 5.0, 42.0, 0.0, 100.0)
            + 0.08 * efficiency_score
            + 0.06 * defensive_focus_score
            + 0.05 * physical_mobility_score
            + 0.03 * usage_score
        ),
    }

    # Potential should capture both young upside and established superstar trajectory.
    potential_upside = raw["Potential"]
    established_star_signal = (
        0.40 * usage_score
        + 0.22 * efficiency_score
        + 0.18 * creation_2_score
        + 0.12 * remap(ast_pct, 5.0, 42.0, 0.0, 100.0)
        + 0.08 * workload_score
    )
    established_star_ceiling = remap(established_star_signal, 40.0, 85.0, 58.0, 92.0)
    young_star_age_signal = remap(
        1.0 - remap(age, 19.0, 29.0, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0
    )
    young_superstar_track = remap(
        0.50 * young_star_age_signal + 0.50 * established_star_signal,
        42.0,
        82.0,
        80.0,
        99.0,
    )
    if age >= 30.0:
        raw["Potential"] = max(potential_upside, established_star_ceiling)
    else:
        raw["Potential"] = max(
            potential_upside, 0.88 * established_star_ceiling, young_superstar_track
        )

    # Keep smooth composites on a healthy gameplay scale with no hard threshold jumps.
    raw["Mid-Range Shot"] = remap(raw["Mid-Range Shot"], 20.0, 90.0, 25.0, 100.0)
    raw["Three-Point Shot"] = remap(raw["Three-Point Shot"], 15.0, 90.0, 25.0, 100.0)
    raw["Shot IQ"] = remap(raw["Shot IQ"], 20.0, 90.0, 28.0, 100.0)
    raw["Offensive Consistency"] = remap(
        raw["Offensive Consistency"], 20.0, 90.0, 28.0, 100.0
    )
    raw["Driving Layup"] = remap(raw["Driving Layup"], 18.0, 84.0, 30.0, 98.0)
    raw["Perimeter Defense"] = remap(raw["Perimeter Defense"], 20.0, 84.0, 25.0, 100.0)
    raw["Driving Dunk"] = remap(raw["Driving Dunk"], 20.0, 84.0, 25.0, 100.0)
    raw["Speed"] = remap(raw["Speed"], 20.0, 88.0, 30.0, 96.0)
    raw["Agility"] = remap(raw["Agility"], 20.0, 88.0, 28.0, 96.0)
    raw["Vertical"] = remap(raw["Vertical"], 18.0, 88.0, 25.0, 98.0)
    raw["Ball Handle"] = remap(raw["Ball Handle"], 26.0, 93.0, 25.0, 98.0)
    raw["Speed with Ball"] = remap(raw["Speed with Ball"], 24.0, 92.0, 28.0, 96.0)
    raw["Pass Accuracy"] = remap(raw["Pass Accuracy"], 20.0, 90.0, 25.0, 100.0)
    raw["Pass IQ"] = remap(raw["Pass IQ"], 20.0, 90.0, 25.0, 100.0)
    raw["Pass Vision"] = remap(raw["Pass Vision"], 20.0, 90.0, 25.0, 100.0)

    roles = select_player_roles_from_stats(blended_row, role_catalog)

    def attr_clamp(value: float) -> int:
        return int(round(clamp(value, 25.0, 95.0)))

    games = max(
        as_float(blended_row, "per_game_g", as_float(blended_row, "totals_g", 0.0)), 1.0
    )
    ppg = as_float(blended_row, "per_game_pts_per_game")
    ast_pg = as_float(blended_row, "per_game_ast_per_game")
    stl_pg = as_float(blended_row, "per_game_stl_per_game")
    blk_pg = as_float(blended_row, "per_game_blk_per_game")
    height_in = as_float(
        blended_row, "player_info_ht_in_in", as_float(blended_row, "height_in", 78.0)
    )
    weight_lb = as_float(
        blended_row,
        "player_info_wt",
        as_float(blended_row, "weight_lbs", as_float(blended_row, "weight", 220.0)),
    )

    season_label = str(blended_row.get("season_label", "")).strip()

    def _build_percentile_lookup(
        rows: List[Dict[str, Any]], key: str
    ) -> Dict[float, float]:
        """Pre-compute percentile ranks for a stat key across all rows. O(n log n) once."""
        vals = [as_float(r, key) for r in rows]
        vals = [v for v in vals if not math.isnan(v) and not math.isinf(v)]
        if not vals:
            return {}
        sorted_vals = sorted(vals)
        n = float(len(sorted_vals))
        lookup: Dict[float, float] = {}
        for i, v in enumerate(sorted_vals):
            if v not in lookup:
                below = i
                j = i
                while j < len(sorted_vals) and sorted_vals[j] == v:
                    j += 1
                equal = j - i
                lookup[v] = ((below + (0.5 * equal)) / n) * 100.0
        return lookup

    def _lookup_percentile(lookup: Dict[float, float], val: float, default: float = 50.0) -> float:
        """O(1) percentile lookup with nearest-value fallback."""
        if val in lookup:
            return lookup[val]
        best_diff = float("inf")
        best_pct = default
        for k, v in lookup.items():
            d = abs(k - val)
            if d < best_diff:
                best_diff = d
                best_pct = v
        return best_pct

    if len(same_bucket) < 20:
        same_bucket = same_season

    _bucket_lookups: Dict[str, Dict[float, float]] = {}
    _season_lookups: Dict[str, Dict[float, float]] = {}

    def pct_key(key: str, current_val: float) -> float:
        if key not in _bucket_lookups:
            _bucket_lookups[key] = _build_percentile_lookup(same_bucket, key)
        return _lookup_percentile(_bucket_lookups[key], current_val)

    def pct_key_global(key: str, current_val: float) -> float:
        if key not in _season_lookups:
            _season_lookups[key] = _build_percentile_lookup(same_season, key)
        return _lookup_percentile(_season_lookups[key], current_val)

    p_usg = pct_key("advanced_usg_percent", usg)
    p_ast = pct_key("advanced_ast_percent", ast_pct)
    p_ast100 = pct_key("per_100_ast_per_100_poss", ast100)
    p_tov_ctrl = pct_key("advanced_tov_percent", -tov_pct)
    p_oreb = pct_key("advanced_orb_percent", orb_pct)
    p_dreb = pct_key("advanced_drb_percent", drb_pct)
    p_stl = pct_key("advanced_stl_percent", stl_pct)
    p_blk = pct_key("advanced_blk_percent", blk_pct)
    p_fta36 = pct_key("per_36_fta_per_36_min", fta36)
    p_3pa36 = pct_key("per_36_x3pa_per_36_min", fg3a36)
    p_3pt = pct_key("per_36_x3p_percent", three_pct)
    p_2pt = pct_key("per_36_x2p_percent", two_pct)
    p_ft = pct_key("per_36_ft_percent", ft_pct)
    p_ts = pct_key("advanced_ts_percent", ts_pct)
    p_efg = pct_key("per_36_e_fg_percent", efg_pct)
    p_rim_share = pct_key("shooting_percent_fga_from_x0_3_range", rim_share)
    p_close_share = pct_key("shooting_percent_fga_from_x3_10_range", close_share)
    p_mid_share = pct_key(
        "shooting_percent_fga_from_x10_16_range", mid_share + long_mid_share
    )
    p_3_share = pct_key("shooting_percent_fga_from_x3p_range", three_share)
    p_dunk_share = pct_key("shooting_percent_dunks_of_fga", dunks_share)
    p_dunks = pct_key("shooting_num_of_dunks", dunks)
    p_minutes = pct_key("totals_mp", minutes)
    p_mpg = pct_key("per_game_mp_per_game", mpg)
    p_pf_low = pct_key("per_100_pf_per_100_poss", -pf100)
    p_dws = pct_key("advanced_dws", dws)
    p_age_youth = pct_key("age", -age)
    p_passes_made_pg = pct_key("tracking_passes_made_pg", tracking_passes_made_pg)
    p_potential_ast_pg = pct_key("tracking_potential_ast_pg", tracking_potential_ast_pg)
    p_ast_adj_pg = pct_key("tracking_ast_adj_pg", tracking_ast_adj_pg)
    p_secondary_ast_pg = pct_key("tracking_secondary_ast_pg", tracking_secondary_ast_pg)
    p_ft_ast_pg = pct_key("tracking_ft_ast_pg", tracking_ft_ast_pg)
    p_ast_to_pass_pct_adj = pct_key(
        "tracking_ast_to_pass_pct_adj", tracking_ast_to_pass_pct_adj
    )
    p_touches_pg = pct_key("tracking_touches_pg", tracking_touches_pg)
    p_front_ct_touches_pg = pct_key(
        "tracking_front_ct_touches_pg", tracking_front_ct_touches_pg
    )
    p_time_of_poss_pg = pct_key("tracking_time_of_poss_pg", tracking_time_of_poss_pg)
    p_avg_drib_per_touch = pct_key(
        "tracking_avg_drib_per_touch", tracking_avg_drib_per_touch
    )
    p_drives_pg = pct_key("tracking_drives_pg", tracking_drives_pg)
    p_drive_passes_pg = pct_key("tracking_drive_passes_pg", tracking_drive_passes_pg)
    p_drive_ast_pg = pct_key("tracking_drive_ast_pg", tracking_drive_ast_pg)
    p_drive_pass_rate = pct_key("tracking_drive_pass_rate", tracking_drive_pass_rate)
    p_drive_ast_rate = pct_key("tracking_drive_ast_rate", tracking_drive_ast_rate)
    p_tracking_dist_miles_pg = pct_key("tracking_dist_miles_pg", tracking_dist_miles_pg)
    p_tracking_dist_miles_off_pg = pct_key(
        "tracking_dist_miles_off_pg", tracking_dist_miles_off_pg
    )
    p_tracking_dist_miles_def_pg = pct_key(
        "tracking_dist_miles_def_pg", tracking_dist_miles_def_pg
    )
    p_contested_shots_pg = pct_key(
        "hustle_contested_shots_pg", hustle_contested_shots_pg
    )
    p_contested_2pt_pg = pct_key("hustle_contested_2pt_pg", hustle_contested_2pt_pg)
    p_contested_3pt_pg = pct_key("hustle_contested_3pt_pg", hustle_contested_3pt_pg)
    p_deflections_pg = pct_key("hustle_deflections_pg", hustle_deflections_pg)
    p_charges_drawn_pg = pct_key("hustle_charges_drawn_pg", hustle_charges_drawn_pg)
    p_loose_balls_recovered_def_pg = pct_key(
        "hustle_loose_balls_recovered_def_pg", hustle_loose_balls_recovered_def_pg
    )
    p_dash_overall_stop_delta = pct_key(
        "defense_dash_overall_stop_delta", defense_dash_overall_stop_delta
    )
    p_dash_overall_plusminus_inv = pct_key(
        "defense_dash_overall_plusminus", -defense_dash_overall_plusminus
    )
    p_dash_3pt_stop_delta = pct_key(
        "defense_dash_3pt_stop_delta", defense_dash_3pt_stop_delta
    )
    p_dash_3pt_plusminus_inv = pct_key(
        "defense_dash_3pt_plusminus", -defense_dash_3pt_plusminus
    )
    p_dash_2pt_stop_delta = pct_key(
        "defense_dash_2pt_stop_delta", defense_dash_2pt_stop_delta
    )
    p_dash_2pt_plusminus_inv = pct_key(
        "defense_dash_2pt_plusminus", -defense_dash_2pt_plusminus
    )
    p_dash_lt6_stop_delta = pct_key(
        "defense_dash_lt6_stop_delta", defense_dash_lt6_stop_delta
    )
    p_dash_lt6_plusminus_inv = pct_key(
        "defense_dash_lt6_plusminus", -defense_dash_lt6_plusminus
    )

    g_usg = pct_key_global("advanced_usg_percent", usg)
    g_ast = pct_key_global("advanced_ast_percent", ast_pct)
    g_ast100 = pct_key_global("per_100_ast_per_100_poss", ast100)
    g_tov_ctrl = pct_key_global("advanced_tov_percent", -tov_pct)
    g_passes_made_pg = pct_key_global(
        "tracking_passes_made_pg", tracking_passes_made_pg
    )
    g_potential_ast_pg = pct_key_global(
        "tracking_potential_ast_pg", tracking_potential_ast_pg
    )
    g_ast_adj_pg = pct_key_global("tracking_ast_adj_pg", tracking_ast_adj_pg)
    g_secondary_ast_pg = pct_key_global(
        "tracking_secondary_ast_pg", tracking_secondary_ast_pg
    )
    g_ft_ast_pg = pct_key_global("tracking_ft_ast_pg", tracking_ft_ast_pg)
    g_ast_to_pass_pct_adj = pct_key_global(
        "tracking_ast_to_pass_pct_adj", tracking_ast_to_pass_pct_adj
    )
    g_touches_pg = pct_key_global("tracking_touches_pg", tracking_touches_pg)
    g_front_ct_touches_pg = pct_key_global(
        "tracking_front_ct_touches_pg", tracking_front_ct_touches_pg
    )
    g_time_of_poss_pg = pct_key_global(
        "tracking_time_of_poss_pg", tracking_time_of_poss_pg
    )
    g_avg_drib_per_touch = pct_key_global(
        "tracking_avg_drib_per_touch", tracking_avg_drib_per_touch
    )
    g_drives_pg = pct_key_global("tracking_drives_pg", tracking_drives_pg)
    g_drive_passes_pg = pct_key_global(
        "tracking_drive_passes_pg", tracking_drive_passes_pg
    )
    g_drive_ast_pg = pct_key_global("tracking_drive_ast_pg", tracking_drive_ast_pg)
    g_drive_pass_rate = pct_key_global(
        "tracking_drive_pass_rate", tracking_drive_pass_rate
    )
    g_drive_ast_rate = pct_key_global(
        "tracking_drive_ast_rate", tracking_drive_ast_rate
    )
    g_drive_fg_pct = pct_key_global("tracking_drive_fg_pct", tracking_drive_fg_pct)
    g_drive_tov_ctrl = pct_key_global("tracking_drive_tov_pct", -tracking_drive_tov_pct)
    g_avg_speed = pct_key_global("tracking_avg_speed", tracking_avg_speed)
    g_avg_speed_off = pct_key_global("tracking_avg_speed_off", tracking_avg_speed_off)
    g_avg_speed_def = pct_key_global("tracking_avg_speed_def", tracking_avg_speed_def)
    g_tracking_dist_miles_pg = pct_key_global(
        "tracking_dist_miles_pg", tracking_dist_miles_pg
    )
    g_tracking_dist_miles_off_pg = pct_key_global(
        "tracking_dist_miles_off_pg", tracking_dist_miles_off_pg
    )
    g_tracking_dist_miles_def_pg = pct_key_global(
        "tracking_dist_miles_def_pg", tracking_dist_miles_def_pg
    )

    is_guard = ("PG" in position.upper()) or ("SG" in position.upper())
    is_forward = ("SF" in position.upper()) or ("PF" in position.upper())
    is_center = "C" in position.upper()
    is_sf = (
        ("SF" in position.upper())
        and ("PF" not in position.upper())
        and ("C" not in position.upper())
    )
    is_guard_like = is_guard or (
        is_sf and height_in <= 80.0
    )  # SFs under 6'8 play like guards

    defense_peak_signal = defense_peak_signal  # Already computed from cache above

    size_signal = clamp(
        remap(height_in, 73.0, 84.0, 0.0, 100.0) * 0.55
        + remap(weight_lb, 175.0, 280.0, 0.0, 100.0) * 0.45,
        0.0,
        100.0,
    )
    athletic_signal = clamp(
        0.45 * p_dunk_share + 0.35 * p_dunks + 0.20 * p_rim_share, 0.0, 100.0
    )
    # Dunk-specific explosive signal: purely dunk production, no rim finishing noise.
    dunk_explosive_signal = clamp(0.55 * p_dunk_share + 0.45 * p_dunks, 0.0, 100.0)
    # Power build: weight-per-inch as proxy for explosive/muscular frame.
    _power_build = clamp(
        remap(weight_lb / max(height_in, 70.0), 2.30, 3.10, 0.0, 100.0), 0.0, 100.0
    )

    fresh: Dict[str, float] = {
        "Driving Layup": 25.0
        + 0.32 * p_rim_share
        + 0.22 * p_2pt
        + 0.20 * p_fta36
        + 0.16 * creation_2_score
        + 0.10 * p_usg,
        "Standing Dunk": 25.0
        + 0.38 * size_signal
        + 0.28 * p_dunks
        + 0.18 * p_dunk_share
        + 0.16 * p_rim_share,
        "Driving Dunk": 25.0
        + 0.26 * dunk_explosive_signal
        + 0.20 * p_dunks
        + 0.16 * p_dunk_share
        + 0.06 * p_age_youth,
        "Close Shot": 25.0
        + 0.34 * p_close_share
        + 0.30 * p_2pt
        + 0.20 * p_rim_share
        + 0.16 * p_ts,
        "Mid-Range Shot": 25.0
        + 0.34 * p_mid_share
        + 0.24 * p_2pt
        + 0.22 * p_ft
        + 0.20 * creation_2_score,
        "Three-Point Shot": 25.0
        + 0.38 * p_3pt
        + 0.28 * p_3pa36
        + 0.20 * p_3_share
        + 0.14 * p_ft,
        "Free Throw": 25.0 + 0.78 * p_ft + 0.12 * p_fta36 + 0.10 * p_ts,
        "Post Hook": 25.0
        + 0.38 * size_signal
        + 0.28 * p_close_share
        + 0.20 * p_2pt
        + 0.14 * p_fta36,
        "Post Fade": 25.0
        + 0.34 * p_mid_share
        + 0.28 * p_ft
        + 0.22 * p_usg
        + 0.16 * size_signal,
        "Post Control": 25.0
        + 0.38 * size_signal
        + 0.22 * p_fta36
        + 0.18 * p_close_share
        + 0.12 * p_usg
        + 0.10 * clamp(remap(elbow_touches_pg, 0.5, 8.0, 0.0, 100.0), 0.0, 100.0),
        "Draw Foul": 25.0
        + 0.40 * p_fta36
        + 0.20 * p_rim_share
        + 0.18 * p_usg
        + 0.10 * creation_2_score
        + 0.12 * clamp(remap(misc_pfd_pg, 1.0, 8.0, 0.0, 100.0), 0.0, 100.0),
        "Shot IQ": 25.0
        + 0.30 * p_ts
        + 0.24 * p_efg
        + 0.20 * p_tov_ctrl
        + 0.16 * shot_discipline_score
        + 0.10
        * clamp(remap(shot_dash_touch_lt2_efg, 0.38, 0.65, 0.0, 100.0), 0.0, 100.0),
        "Ball Handle": 25.0
        + 0.34 * creation_2_score
        + 0.24 * p_tov_ctrl
        + 0.22 * p_usg
        + 0.20 * p_ast,
        "Speed with Ball": 25.0
        + 0.30 * creation_2_score
        + 0.20 * athletic_signal
        + 0.18 * p_usg
        + 0.12 * p_tov_ctrl
        + 0.10 * (100.0 if is_guard else (55.0 if is_forward else 35.0))
        + 0.10 * clamp(remap(transition_poss_pct, 0.04, 0.25, 0.0, 100.0), 0.0, 100.0),
        "Hands": 25.0
        + 0.32 * p_tov_ctrl
        + 0.22 * p_2pt
        + 0.18 * p_ts
        + 0.14 * p_minutes
        + 0.14 * p_ast,
        "Pass Accuracy": 25.0
        + 0.36 * p_ast
        + 0.30 * p_ast100
        + 0.22 * p_tov_ctrl
        + 0.12 * p_usg,
        "Pass IQ": 25.0
        + 0.34 * p_ast
        + 0.26 * p_ast100
        + 0.24 * p_tov_ctrl
        + 0.16 * p_ts,
        "Pass Vision": 25.0
        + 0.40 * p_ast
        + 0.28 * p_ast100
        + 0.20 * p_usg
        + 0.12 * creation_2_score,
        "Offensive Consistency": 25.0
        + 0.34 * p_usg
        + 0.30 * p_ts
        + 0.20 * p_efg
        + 0.16 * p_minutes,
        "Interior Defense": 25.0
        + 0.36 * p_blk
        + 0.26 * p_dreb
        + 0.22 * size_signal
        + 0.16 * p_pf_low,
        "Perimeter Defense": 25.0
        + 0.34 * p_stl
        + 0.22 * p_blk
        + 0.18 * p_minutes
        + 0.14 * p_pf_low
        + 0.12 * (100.0 if (is_guard or is_forward) else 45.0),
        "Steal": 25.0
        + 0.62 * p_stl
        + 0.16 * p_pf_low
        + 0.12 * p_minutes
        + 0.10 * (100.0 if is_guard else (72.0 if is_forward else 48.0)),
        "Block": 25.0
        + 0.58 * p_blk
        + 0.22 * size_signal
        + 0.12 * p_dreb
        + 0.08 * p_minutes
        + 0.10 * (100.0 if is_center else (68.0 if is_forward else 32.0)),
        "Offensive Rebound": 25.0
        + 0.64 * p_oreb
        + 0.20 * size_signal
        + 0.16 * p_minutes,
        "Defensive Rebound": 25.0
        + 0.58 * p_dreb
        + 0.24 * size_signal
        + 0.18 * p_minutes,
        "Help Defense IQ": 25.0
        + 0.34 * p_blk
        + 0.24 * p_stl
        + 0.20 * p_dreb
        + 0.22 * p_minutes,
        "Pass Perception": 25.0
        + 0.56 * p_stl
        + 0.18 * p_blk
        + 0.16 * p_minutes
        + 0.10 * p_pf_low,
        "Defensive Consistency": 25.0
        + 0.34 * p_minutes
        + 0.28 * p_stl
        + 0.22 * p_blk
        + 0.16 * p_pf_low,
        "Speed": 25.0
        + 0.34 * athletic_signal
        + 0.20 * p_stl
        + 0.18 * p_age_youth
        + 0.16 * (100.0 if is_guard else (66.0 if is_forward else 40.0))
        + 0.12 * p_minutes,
        "Agility": 25.0
        + 0.32 * creation_2_score
        + 0.22 * p_stl
        + 0.18 * p_age_youth
        + 0.14 * p_tov_ctrl
        + 0.14 * (100.0 if is_guard else (72.0 if is_forward else 45.0)),
        "Strength": 25.0
        + 0.50 * size_signal
        + 0.18 * p_fta36
        + 0.16 * p_dreb
        + 0.16 * p_minutes,
        "Vertical": 25.0
        + 0.44 * athletic_signal
        + 0.20 * p_blk
        + 0.16 * p_rim_share
        + 0.12 * p_age_youth
        + 0.08 * (100.0 if (is_guard or is_forward) else 75.0),
        "Stamina": 25.0 + 0.46 * p_minutes + 0.28 * p_mpg + 0.16 * p_usg + 0.10 * p_ts,
        "Intangibles": 25.0,
        "Hustle": 25.0
        + 0.22 * p_oreb
        + 0.22 * p_dreb
        + 0.18 * p_stl
        + 0.14 * p_blk
        + 0.24 * p_minutes,
        "Overall Durability": 25.0
        + 0.52 * p_minutes
        + 0.20 * p_mpg
        + 0.16 * p_age_youth
        + 0.12 * p_pf_low,
        "Potential": 25.0
        + 0.52 * p_age_youth
        + 0.18 * p_usg
        + 0.12 * p_ts
        + 0.10 * p_stl
        + 0.08 * p_ast,
    }

    # Defense recalibration: blend box-score rates with contest quality and hustle events.
    # Weights prioritise impact metrics (stop_delta / plusminus) over volume (steals / deflections)
    # so high-minute gambling defenders do not receive inflated ratings.
    perimeter_def_signal = clamp(
        0.22 * p_dash_3pt_stop_delta
        + 0.18 * p_dash_overall_stop_delta
        + 0.18 * p_contested_3pt_pg
        + 0.14 * p_dash_3pt_plusminus_inv
        + 0.10 * p_stl
        + 0.10 * p_deflections_pg
        + 0.04 * p_pf_low
        + 0.04 * p_minutes,
        0.0,
        100.0,
    )
    interior_def_signal = clamp(
        0.22 * p_dash_lt6_stop_delta
        + 0.16 * p_dash_lt6_plusminus_inv
        + 0.18 * p_contested_2pt_pg
        + 0.16 * p_blk
        + 0.12 * p_contested_shots_pg
        + 0.10 * size_signal
        + 0.06 * p_dreb,
        0.0,
        100.0,
    )
    steal_signal = clamp(
        0.50 * p_stl
        + 0.24 * p_deflections_pg
        + 0.12 * p_loose_balls_recovered_def_pg
        + 0.08 * p_dash_overall_stop_delta
        + 0.06 * p_minutes,
        0.0,
        100.0,
    )
    block_signal = clamp(
        0.50 * p_blk
        + 0.20 * p_dash_lt6_stop_delta
        + 0.12 * p_dash_2pt_stop_delta
        + 0.10 * p_contested_2pt_pg
        + 0.08 * size_signal,
        0.0,
        100.0,
    )
    help_iq_signal = clamp(
        0.20 * p_dash_overall_stop_delta
        + 0.18 * p_contested_shots_pg
        + 0.16 * p_deflections_pg
        + 0.12 * p_charges_drawn_pg
        + 0.12 * p_dash_2pt_stop_delta
        + 0.10 * p_blk
        + 0.06 * p_stl
        + 0.06 * p_minutes,
        0.0,
        100.0,
    )
    pass_perception_signal = clamp(
        0.42 * p_stl
        + 0.28 * p_deflections_pg
        + 0.12 * p_loose_balls_recovered_def_pg
        + 0.10 * p_dash_3pt_stop_delta
        + 0.08 * p_dash_overall_plusminus_inv,
        0.0,
        100.0,
    )
    defensive_consistency_signal = clamp(
        0.22 * p_dash_overall_stop_delta
        + 0.16 * p_dash_overall_plusminus_inv
        + 0.16 * p_contested_shots_pg
        + 0.14 * p_dws
        + 0.12 * p_deflections_pg
        + 0.10 * p_minutes
        + 0.10 * p_pf_low,
        0.0,
        100.0,
    )

    if is_guard:
        perimeter_def_signal = min(100.0, perimeter_def_signal + 4.0)
        steal_signal = min(100.0, steal_signal + 5.0)
        block_signal = max(0.0, block_signal - 8.0)
    elif is_center:
        interior_def_signal = min(100.0, interior_def_signal + 5.0)
        block_signal = min(100.0, block_signal + 6.0)
        perimeter_def_signal = max(0.0, perimeter_def_signal - 4.0)
        steal_signal = max(0.0, steal_signal - 6.0)
        pass_perception_signal = max(0.0, pass_perception_signal - 4.0)

    fresh["Perimeter Defense"] = 0.32 * fresh["Perimeter Defense"] + 0.68 * (
        25.0 + 0.70 * perimeter_def_signal
    )
    fresh["Interior Defense"] = 0.32 * fresh["Interior Defense"] + 0.68 * (
        25.0 + 0.70 * interior_def_signal
    )
    fresh["Steal"] = 0.30 * fresh["Steal"] + 0.70 * (25.0 + 0.70 * steal_signal)
    fresh["Block"] = 0.30 * fresh["Block"] + 0.70 * (25.0 + 0.70 * block_signal)
    fresh["Help Defense IQ"] = 0.30 * fresh["Help Defense IQ"] + 0.70 * (
        25.0 + 0.70 * help_iq_signal
    )
    fresh["Pass Perception"] = 0.30 * fresh["Pass Perception"] + 0.70 * (
        25.0 + 0.70 * pass_perception_signal
    )
    fresh["Defensive Consistency"] = 0.30 * fresh["Defensive Consistency"] + 0.70 * (
        25.0 + 0.70 * defensive_consistency_signal
    )

    # Hard cap for players with net-negative overall defensive impact.
    # Opponents shooting BETTER when you defend them (stop_delta < 0)
    # means you should not receive elite perimeter/help defense ratings,
    # regardless of how good your volume stats (steals, deflections) look.
    # Two tiers: soft proportional reduction for barely-negative values,
    # hard cap for meaningfully negative ones.
    if defense_dash_overall_stop_delta < 0.0 and minutes >= 500.0:
        neg_severity = remap(defense_dash_overall_stop_delta, -0.06, 0.0, 1.0, 0.0)
        for _da in ["Perimeter Defense", "Help Defense IQ", "Defensive Consistency"]:
            if fresh[_da] > 55.0:
                _excess = fresh[_da] - 55.0
                fresh[_da] = 55.0 + _excess * (1.0 - 0.80 * neg_severity)
        # Hard cap for clearly negative overall impact (below -0.008).
        if defense_dash_overall_stop_delta < -0.008:
            _hard_cap = 60.0 + remap(
                defense_dash_overall_stop_delta, -0.06, -0.008, -18.0, 0.0
            )
            fresh["Perimeter Defense"] = min(fresh["Perimeter Defense"], _hard_cap)
            fresh["Help Defense IQ"] = min(fresh["Help Defense IQ"], _hard_cap + 4.0)
            fresh["Defensive Consistency"] = min(
                fresh["Defensive Consistency"], _hard_cap + 2.0
            )
    # Floor for elite positive-impact defenders (stop_delta ≥ 0.04).
    if defense_dash_overall_stop_delta >= 0.04 and minutes >= 800.0:
        elite_def_floor = remap(defense_dash_overall_stop_delta, 0.04, 0.12, 72.0, 90.0)
        fresh["Perimeter Defense"] = max(fresh["Perimeter Defense"], elite_def_floor)
        fresh["Interior Defense"] = max(
            fresh["Interior Defense"], elite_def_floor - 2.0
        )
        fresh["Help Defense IQ"] = max(fresh["Help Defense IQ"], elite_def_floor + 2.0)
    # Cap interior defense for non-bigs with negative near-rim impact.
    if defense_dash_lt6_stop_delta < 0.0 and not is_center and minutes >= 500.0:
        int_def_cap = 58.0 + remap(defense_dash_lt6_stop_delta, -0.08, 0.0, -14.0, 0.0)
        fresh["Interior Defense"] = min(fresh["Interior Defense"], int_def_cap)

    # Physical recalibration from tracking speed-distance profile.
    # NOTE: NBA tracking "average speed" measures walking/jogging speed over the
    # full game, NOT burst or game speed.  Ball-dominant creators and bigs conserve
    # energy between plays and rank very low on average speed despite being
    # explosive athletes.  We therefore reduce the tracking signal's weight for
    # non-guards and supplement it with a "game burst" proxy (drives, dunks, rim
    # attacks, transition) that better captures on-court athleticism.
    speed_distance_signal = clamp(
        0.40 * g_avg_speed
        + 0.22 * g_avg_speed_off
        + 0.12 * g_avg_speed_def
        + 0.16 * g_tracking_dist_miles_pg
        + 0.10 * g_tracking_dist_miles_off_pg,
        0.0,
        100.0,
    )
    agility_distance_signal = clamp(
        0.32 * g_avg_speed
        + 0.28 * g_avg_speed_off
        + 0.18 * g_avg_speed_def
        + 0.12 * g_tracking_dist_miles_def_pg
        + 0.10 * p_age_youth,
        0.0,
        100.0,
    )
    # Game burst proxy: drives, dunks, rim-share, and steal rate indicate burst
    # speed and explosiveness independent of average jogging speed.
    game_burst_signal = clamp(
        0.30 * remap(tracking_drives_pg, 2.0, 18.0, 0.0, 100.0)
        + 0.25 * athletic_signal
        + 0.20 * remap(p_stl, 15.0, 85.0, 0.0, 100.0)
        + 0.15 * remap(p_rim_share, 15.0, 85.0, 0.0, 100.0)
        + 0.10 * p_age_youth,
        0.0,
        100.0,
    )

    # Position-dependent blending: guards keep heavy tracking weight (their
    # avg-speed data does reflect quickness); forwards and centers get more
    # of the raw + burst signal and less of the tracking walking-speed data.
    if is_guard:
        _spd_trk_w = 0.52  # tracking weight for speed
        _agi_trk_w = 0.48  # tracking weight for agility
    elif is_forward:
        _spd_trk_w = 0.28
        _agi_trk_w = 0.24
    else:  # center
        _spd_trk_w = 0.22
        _agi_trk_w = 0.18

    _spd_raw_w = 1.0 - _spd_trk_w
    _agi_raw_w = 1.0 - _agi_trk_w

    # For non-guards, blend tracking signal with burst signal instead of using
    # tracking alone so that explosive forwards/bigs aren't penalised for
    # low average walking speed.
    if is_guard:
        spd_recal = 25.0 + 0.70 * speed_distance_signal
        agi_recal = 25.0 + 0.70 * agility_distance_signal
    else:
        blended_spd_sig = 0.45 * speed_distance_signal + 0.55 * game_burst_signal
        blended_agi_sig = 0.40 * agility_distance_signal + 0.60 * game_burst_signal
        spd_recal = 25.0 + 0.70 * blended_spd_sig
        agi_recal = 25.0 + 0.70 * blended_agi_sig

    fresh["Speed"] = _spd_raw_w * fresh["Speed"] + _spd_trk_w * spd_recal
    fresh["Agility"] = _agi_raw_w * fresh["Agility"] + _agi_trk_w * agi_recal

    # Strength/Vertical recalibration: separate core power from pure height,
    # and reward true explosive profiles for vertical pop.
    strength_size_signal = clamp(
        0.46 * remap(weight_lb, 180.0, 285.0, 0.0, 100.0)
        + 0.24 * remap(height_in, 72.0, 84.0, 0.0, 100.0)
        + 0.16 * remap(drb_pct, 7.0, 30.0, 0.0, 100.0)
        + 0.14 * remap(fta36, 1.0, 10.5, 0.0, 100.0),
        0.0,
        100.0,
    )
    vertical_explosive_signal = clamp(
        0.34 * remap(dunks_share, 0.01, 0.30, 0.0, 100.0)
        + 0.24 * remap(dunks, 2.0, 175.0, 0.0, 100.0)
        + 0.18 * remap(rim_share, 0.10, 0.55, 0.0, 100.0)
        + 0.14 * remap(blk_pct, 0.5, 6.5, 0.0, 100.0)
        + 0.10 * g_avg_speed_off,
        0.0,
        100.0,
    )

    fresh["Strength"] = 0.40 * fresh["Strength"] + 0.60 * (
        25.0 + 0.70 * strength_size_signal
    )
    fresh["Vertical"] = 0.36 * fresh["Vertical"] + 0.64 * (
        25.0 + 0.70 * vertical_explosive_signal
    )

    if is_center:
        center_strength_floor = 56.0 + 0.26 * remap(weight_lb, 220.0, 290.0, 0.0, 100.0)
        fresh["Strength"] = max(fresh["Strength"], center_strength_floor)
    elif is_guard:
        guard_strength_cap = 74.0 + remap(weight_lb, 175.0, 225.0, 0.0, 8.0)
        fresh["Strength"] = min(fresh["Strength"], guard_strength_cap)

    if is_guard and dunks_share >= 0.05 and rim_share >= 0.22:
        fresh["Vertical"] = max(
            fresh["Vertical"], 74.0 + 0.10 * remap(dunks, 10.0, 140.0, 0.0, 100.0)
        )
    if is_center and dunks_share < 0.10 and blk_pct < 3.0:
        fresh["Vertical"] = min(fresh["Vertical"], 76.0)
    if minutes < 700.0 or mpg < 16.0:
        fresh["Vertical"] = min(fresh["Vertical"], 82.0)

    # Driving Dunk power-build adjustment for guards/wings.
    # Muscular, explosive builds (high weight-per-inch) are better dunkers
    # than lean, finesse builds even with similar dunk volume stats.
    if (is_guard or is_forward) and minutes >= 600.0:
        _dunk_build_adj = remap(_power_build, 30.0, 80.0, -5.0, 5.0)
        fresh["Driving Dunk"] += _dunk_build_adj

    final_attributes = {
        name: attr_clamp(fresh.get(name, 50.0)) for name in ATTRIBUTE_ORDER
    }

    # Strength/Vertical final pass: keep realistic NBA spread after global compression.
    strength_target = (
        40.0
        + remap(weight_lb, 175.0, 285.0, 0.0, 22.0)
        + remap(height_in, 72.0, 84.0, 0.0, 8.0)
        + remap(drb_pct, 7.0, 30.0, 0.0, 8.0)
        + remap(fta36, 1.0, 11.0, 0.0, 5.0)
        + remap(rim_share, 0.10, 0.60, 0.0, 6.0)
        + remap(dunks_share, 0.01, 0.30, 0.0, 4.0)
    )
    if is_center:
        strength_target = max(
            strength_target, 62.0 + remap(weight_lb, 225.0, 290.0, 0.0, 12.0)
        )
        center_strength_cap = 92.0 + remap(weight_lb, 250.0, 300.0, 0.0, 3.0)
        strength_target = min(strength_target, center_strength_cap)
    elif is_guard:
        guard_strength_cap = 82.0
        if weight_lb < 190.0:
            guard_strength_cap = 76.0
        elif weight_lb < 205.0:
            guard_strength_cap = 79.0
        strength_target = min(strength_target, guard_strength_cap)
    else:
        strength_target = min(strength_target, 89.0)
    final_attributes["Strength"] = attr_clamp(clamp(strength_target, 25.0, 95.0))

    vertical_target = (
        40.0
        + remap(dunks_share, 0.01, 0.30, 0.0, 14.0)
        + remap(dunks, 2.0, 180.0, 0.0, 10.0)
        + remap(rim_share, 0.10, 0.55, 0.0, 8.0)
        + remap(blk_pct, 0.5, 6.5, 0.0, 8.0)
        + remap(tracking_avg_speed_off, 4.10, 5.10, 0.0, 5.0)
    )
    if is_guard and dunks_share >= 0.03 and rim_share >= 0.22:
        vertical_target = max(
            vertical_target, 78.0 + remap(dunks, 5.0, 120.0, 0.0, 10.0)
        )
    if is_center:
        center_vertical_cap = (
            82.0
            + remap(dunks_share, 0.05, 0.30, 0.0, 8.0)
            + remap(blk_pct, 1.5, 7.0, 0.0, 5.0)
        )
        vertical_target = min(vertical_target, clamp(center_vertical_cap, 80.0, 92.0))
        if blk_pct >= 5.0 and dunks >= 90.0:
            vertical_target = max(
                vertical_target, 76.0 + remap(dunks, 90.0, 190.0, 0.0, 6.0)
            )
        if dunks_share < 0.10 and blk_pct < 3.0:
            vertical_target = min(vertical_target, 78.0)
    elif is_guard:
        guard_vertical_cap = 90.0
        if dunks_share >= 0.10 and dunks >= 80.0:
            guard_vertical_cap = 93.0
        vertical_target = min(vertical_target, guard_vertical_cap)
    else:
        vertical_target = min(vertical_target, 91.0)
    if minutes < 700.0 or mpg < 16.0:
        vertical_target = min(vertical_target, 84.0)
    final_attributes["Vertical"] = attr_clamp(clamp(vertical_target, 25.0, 95.0))

    # Shooting recalibration: role-vs-star shot IQ lanes, volume/difficulty 3PT,
    # and FT% anchored free throw values.
    three_pct_abs = as_float(blended_row, "per_game_x3p_percent", three_pct)
    three_pa_pg = as_float(
        blended_row, "per_game_x3pa_per_game", max(0.0, fg3a36 * 0.74)
    )
    ft_pct_abs = as_float(blended_row, "per_game_ft_percent", ft_pct)
    fta_pg = as_float(blended_row, "per_game_fta_per_game", max(0.0, fta36 * 0.72))
    three_creation_signal = remap(1.0 - assisted3, 0.15, 0.80, 0.0, 100.0)
    catch_shoot_signal = remap(assisted3, 0.45, 0.92, 0.0, 100.0)
    # Tracking catch-and-shoot data for more precise shooting evaluation.
    trk_catch_shoot_fg3_pct = as_float(blended_row, "tracking_catch_shoot_fg3_pct")
    trk_catch_shoot_efg_pct = as_float(blended_row, "tracking_catch_shoot_efg_pct")
    trk_catch_shoot_fg3a_pg = as_float(blended_row, "tracking_catch_shoot_fg3a_pg")
    catch_shoot_bonus = remap(trk_catch_shoot_fg3_pct, 0.34, 0.44, 0.0, 4.0) + remap(
        trk_catch_shoot_fg3a_pg, 2.0, 7.0, 0.0, 3.0
    )

    three_point_target = (
        44.0
        + remap(three_pct_abs, 0.30, 0.44, 0.0, 28.0)
        + remap(three_pa_pg, 1.0, 12.0, 0.0, 15.0)
        + remap(three_creation_signal, 20.0, 75.0, 0.0, 4.0)
        + remap(catch_shoot_signal, 30.0, 90.0, 0.0, 4.0)
        + remap(ft_pct_abs, 0.72, 0.92, 0.0, 4.0)
        + catch_shoot_bonus
    )
    if three_pa_pg >= 8.0 and three_pct_abs >= 0.37:
        three_point_target += 3.0
    if three_pa_pg >= 10.0 and three_pct_abs >= 0.35:
        three_point_target += 3.0
    if assisted3 >= 0.68 and three_pct_abs >= 0.38 and three_pa_pg >= 5.0:
        three_point_target += 2.0
    # Elite off-the-dribble shooters (Curry, Lillard, Trae) need top-tier ratings.
    if three_pa_pg >= 7.0 and three_pct_abs >= 0.39 and three_creation_signal >= 55.0:
        three_point_target = max(three_point_target, 92.0)
    # Elite volume-efficiency combo: 7+ 3PA/g and 38%+ with good FT%.
    # FT% acts as a shooting touch filter — sub-80% FT% players are streaky, not elite.
    if three_pa_pg >= 7.0 and three_pct_abs >= 0.38:
        _vol_eff_boost = 88.0 + remap(three_pa_pg, 7.0, 12.0, 0.0, 6.0)
        if ft_pct_abs < 0.80:
            _vol_eff_boost = min(_vol_eff_boost, 86.0)
        three_point_target = max(three_point_target, _vol_eff_boost)
    # Elite catch-and-shoot specialists with volume.
    if trk_catch_shoot_fg3_pct >= 0.40 and trk_catch_shoot_fg3a_pg >= 3.5:
        three_point_target = max(three_point_target, 86.0)
    # Good efficiency shooters: 36%+ on decent volume deserve recognition.
    if three_pct_abs >= 0.36 and three_pa_pg >= 4.0:
        _eff_floor = (
            72.0
            + remap(three_pct_abs, 0.36, 0.44, 0.0, 12.0)
            + remap(three_pa_pg, 4.0, 10.0, 0.0, 6.0)
        )
        if ft_pct_abs < 0.78:
            _eff_floor = min(_eff_floor, 80.0)
        three_point_target = max(three_point_target, _eff_floor)
    # Veteran volume shooters: players who consistently take 3+ threes per game
    # get a floor proportional to volume + efficiency even if current % is mediocre.
    if three_pa_pg >= 3.0 and three_pct_abs >= 0.28 and mpg >= 24.0:
        vet_3pt_floor = (
            60.0
            + remap(three_pct_abs, 0.28, 0.40, 0.0, 14.0)
            + remap(three_pa_pg, 3.0, 8.0, 0.0, 6.0)
        )
        three_point_target = max(three_point_target, vet_3pt_floor)
    if is_center:
        three_point_target -= remap(max(0.0, 6.0 - three_pa_pg), 0.0, 6.0, 0.0, 8.0)
    # Non-shooters: don't let volume alone inflate bad shooters.
    if three_pct_abs < 0.29 and three_pa_pg >= 3.0:
        three_point_target = min(three_point_target, 68.0)
    # Volume gates: very low 3PA/g means % is unreliable — cap the rating.
    # Prevents fringe shooters (e.g. shot 75% on 1.6 3PA/g) from getting high ratings.
    if three_pa_pg < 1.0:
        three_point_target = min(three_point_target, 45.0)
    elif three_pa_pg < 2.0:
        three_point_target = min(three_point_target, 57.0)
    elif three_pa_pg < 3.0:
        three_point_target = min(three_point_target, 68.0)
    # High-volume shooters slightly below elite efficiency tier deserve recognition.
    # Covers players like Luka (36-37% on 10+ 3PA/g) who are legitimately elite.
    if three_pa_pg >= 8.0 and three_pct_abs >= 0.35 and three_pct_abs < 0.38:
        _high_vol_floor = 83.0 + remap(three_pa_pg, 8.0, 13.0, 0.0, 4.0)
        three_point_target = max(three_point_target, _high_vol_floor)
    # Pull-up creators at volume: unassisted 3PT shooting + high volume signals
    # higher effective shot difficulty that pure % doesn't fully capture.
    # Covers Luka (~87), Kyrie, step-back creators in the 36-39% range.
    if three_pa_pg >= 6.0 and three_pct_abs >= 0.36 and three_creation_signal >= 40.0:
        _pullup_creator_floor = 86.0 + remap(three_pct_abs, 0.36, 0.41, 0.0, 5.0)
        three_point_target = max(three_point_target, _pullup_creator_floor)
    final_attributes["Three-Point Shot"] = attr_clamp(
        clamp(three_point_target, 25.0, 95.0)
    )

    ft_pct_skill = remap(ft_pct_abs, 0.60, 0.92, 0.0, 100.0)
    free_throw_target = 50.0 + (0.42 * ft_pct_skill) + remap(fta_pg, 1.0, 9.0, 0.0, 7.0)
    if ft_pct_abs >= 0.87:
        free_throw_target = max(
            free_throw_target, remap(ft_pct_abs, 0.87, 0.94, 88.0, 97.0)
        )
    elif ft_pct_abs >= 0.84:
        free_throw_target = max(
            free_throw_target, remap(ft_pct_abs, 0.84, 0.93, 82.0, 94.0)
        )
    elif ft_pct_abs >= 0.78:
        free_throw_target = max(
            free_throw_target, remap(ft_pct_abs, 0.78, 0.84, 74.0, 82.0)
        )
    if ft_pct_abs <= 0.65:
        free_throw_target = min(free_throw_target, 65.0)
    if ft_pct_abs <= 0.55:
        free_throw_target = min(free_throw_target, 55.0)
    final_attributes["Free Throw"] = attr_clamp(clamp(free_throw_target, 25.0, 95.0))

    role_shot_selection_signal = clamp(
        0.55 * shot_discipline_score + 0.25 * p_tov_ctrl + 0.20 * p_ts,
        0.0,
        100.0,
    )
    star_load_signal = clamp(
        0.65 * p_usg + 0.20 * creation_2_score + 0.15 * p_ast, 0.0, 100.0
    )
    # Shot IQ: role players who stay within their role (low usage, high assisted
    # %) naturally have elite shot IQ (~88-92).  Stars carry heavier shot loads
    # and take tougher shots, so their IQ sits in the low-to-mid 80s.
    if star_load_signal >= 75.0:
        # High-usage stars force tough self-created shots → lower shot IQ: 75-84
        shot_iq_target = remap(role_shot_selection_signal, 30.0, 90.0, 75.0, 84.0)
    elif p_usg <= 40.0:
        # True role players only take smart assisted shots → elite shot IQ: 88-95
        shot_iq_target = remap(role_shot_selection_signal, 30.0, 90.0, 88.0, 95.0)
    elif p_usg <= 55.0:
        # Secondary options / efficient starters: 83-90
        shot_iq_target = remap(role_shot_selection_signal, 30.0, 90.0, 83.0, 90.0)
    else:
        # High-usage but below star-load tier: 79-87
        shot_iq_target = remap(role_shot_selection_signal, 30.0, 90.0, 79.0, 87.0)
    final_attributes["Shot IQ"] = attr_clamp(clamp(shot_iq_target, 60.0, 95.0))

    # Mid-range and offensive consistency recalibration: reward true shot profile
    # and efficient high-minute stability while damping small-sample spikes.
    mid_volume_signal = remap(mid_share + long_mid_share, 0.06, 0.42, 0.0, 100.0)
    mid_eff_signal = remap(two_pct, 0.46, 0.62, 0.0, 100.0)
    mid_touch_signal = remap(ft_pct, 0.64, 0.92, 0.0, 100.0)
    mid_creation_signal = remap(1.0 - assisted2, 0.20, 0.82, 0.0, 100.0)

    mid_range_target = (
        50.0
        + 0.13 * mid_volume_signal
        + 0.14 * mid_eff_signal
        + 0.10 * mid_touch_signal
        + 0.08 * mid_creation_signal
    )
    if usg >= 28.0 and (mid_share + long_mid_share) >= 0.22 and two_pct >= 0.53:
        mid_range_target += 2.0
    if (mid_share + long_mid_share) < 0.10:
        mid_range_target = min(mid_range_target, 76.0)
    elif (mid_share + long_mid_share) < 0.16 and usg < 22.0:
        mid_range_target = min(mid_range_target, 80.0)
    if minutes < 800.0 or mpg < 18.0:
        mid_range_target = min(mid_range_target, 78.0)

    if usg >= 27.0 and (mid_share + long_mid_share) >= 0.26 and two_pct >= 0.53:
        mid_range_target = max(
            mid_range_target, remap(mid_eff_signal, 50.0, 90.0, 84.0, 92.0)
        )

    elite_mid_creator = (
        usg >= 29.0
        and minutes >= 1600.0
        and (mid_share + long_mid_share) >= 0.30
        and two_pct >= 0.55
        and ft_pct >= 0.80
    )
    if elite_mid_creator:
        mid_range_target += 2.0
        mid_range_target = max(
            mid_range_target, remap(mid_eff_signal, 58.0, 95.0, 88.0, 95.0)
        )

    final_attributes["Mid-Range Shot"] = attr_clamp(clamp(mid_range_target, 25.0, 95.0))

    oc_eff_signal = clamp(
        0.48 * remap(ts_pct, 0.51, 0.66, 0.0, 100.0)
        + 0.20 * remap(efg_pct, 0.47, 0.62, 0.0, 100.0)
        + 0.16 * remap(ft_pct, 0.60, 0.90, 0.0, 100.0)
        + 0.16 * p_tov_ctrl,
        0.0,
        100.0,
    )
    oc_load_signal = clamp(
        0.56 * remap(usg, 16.0, 34.0, 0.0, 100.0)
        + 0.44 * remap(mpg, 16.0, 37.0, 0.0, 100.0),
        0.0,
        100.0,
    )
    offensive_consistency_target = 56.0 + 0.30 * oc_eff_signal + 0.24 * oc_load_signal

    if ts_pct >= 0.61 and usg >= 26.0 and mpg >= 30.0:
        offensive_consistency_target = max(
            offensive_consistency_target,
            remap(ts_pct, 0.61, 0.67, 84.0, 92.0),
        )

    if minutes < 900.0 or mpg < 18.0:
        offensive_consistency_target = min(offensive_consistency_target, 78.0)
    if ts_pct < 0.54 and usg >= 28.0:
        offensive_consistency_target = min(offensive_consistency_target, 82.0)

    final_attributes["Offensive Consistency"] = attr_clamp(
        clamp(offensive_consistency_target, 55.0, 95.0)
    )

    # Draw foul and hands recalibration: pressure creation and ball security.
    draw_foul_pressure_signal = clamp(
        0.42 * remap(fta36, 1.0, 11.0, 0.0, 100.0)
        + 0.22 * remap(rim_share, 0.08, 0.55, 0.0, 100.0)
        + 0.14 * p_usg
        + 0.12 * p_drives_pg
        + 0.10 * remap(ft_pct, 0.60, 0.90, 0.0, 100.0),
        0.0,
        100.0,
    )
    draw_foul_target = 38.0 + 0.56 * draw_foul_pressure_signal
    if fta36 >= 7.0 and usg >= 25.0 and rim_share >= 0.20:
        draw_foul_target += 2.0
    if fta36 < 2.0 and rim_share < 0.14:
        draw_foul_target = min(draw_foul_target, 66.0)
    if minutes < 850.0 or mpg < 18.0:
        draw_foul_target = min(draw_foul_target, 78.0)
    if fta36 >= 8.0 and usg >= 28.0 and minutes >= 1200.0:
        draw_foul_target = max(draw_foul_target, remap(fta36, 8.0, 12.5, 80.0, 90.0))

    final_attributes["Draw Foul"] = attr_clamp(clamp(draw_foul_target, 25.0, 95.0))

    hands_security_signal = clamp(
        0.46 * p_tov_ctrl
        + 0.18 * p_ast
        + 0.14 * remap(tracking_touches_pg, 20.0, 95.0, 0.0, 100.0)
        + 0.12 * remap(tracking_time_of_poss_pg, 1.0, 7.5, 0.0, 100.0)
        + 0.10 * p_minutes,
        0.0,
        100.0,
    )
    hands_target = 53.0 + 0.64 * hands_security_signal
    if p_tov_ctrl >= 78.0 and p_ast >= 60.0 and mpg >= 24.0:
        hands_target = max(
            hands_target, remap(hands_security_signal, 62.0, 95.0, 84.0, 95.0)
        )
    if tov_pct >= 17.0 and ast_pct < 18.0:
        hands_target = min(hands_target, 62.0)
    if minutes < 500.0 or mpg < 12.0:
        hands_target = min(hands_target, 74.0)

    final_attributes["Hands"] = attr_clamp(clamp(hands_target, 25.0, 95.0))

    # Stamina and hustle recalibration: separate real workload endurance from
    # low-minute noise, and map disruptive activity into visible hustle tiers.
    stamina_workload_signal = clamp(
        0.44 * remap(mpg, 14.0, 38.0, 0.0, 100.0)
        + 0.24 * remap(minutes, 500.0, 2800.0, 0.0, 100.0)
        + 0.16 * remap(usg, 14.0, 34.0, 0.0, 100.0)
        + 0.16 * remap(tracking_dist_miles_pg, 1.20, 3.00, 0.0, 100.0),
        0.0,
        100.0,
    )

    heavy_minute_player = mpg >= heavy_mpg_threshold and minutes >= 1800.0
    if heavy_minute_player:
        stamina_target = remap(stamina_workload_signal, 52.0, 100.0, 90.0, 97.0)
    else:
        stamina_target = remap(stamina_workload_signal, 0.0, 100.0, 78.0, 92.0)
    final_attributes["Stamina"] = attr_clamp(clamp(stamina_target, 60.0, 95.0))

    hustle_activity_signal = clamp(
        0.24 * p_deflections_pg
        + 0.18 * p_contested_shots_pg
        + 0.16 * p_stl
        + 0.10 * p_blk
        + 0.10 * p_oreb
        + 0.08 * p_dreb
        + 0.14 * p_minutes,
        0.0,
        100.0,
    )
    hustle_target = 44.0 + 0.44 * hustle_activity_signal
    if (
        hustle_deflections_pg >= 3.0
        and hustle_contested_shots_pg >= 4.0
        and mpg >= 24.0
    ):
        hustle_target = max(
            hustle_target, remap(hustle_activity_signal, 60.0, 95.0, 80.0, 88.0)
        )
    if minutes < 500.0 or mpg < 12.0:
        hustle_target = min(hustle_target, 74.0)
    final_attributes["Hustle"] = attr_clamp(clamp(hustle_target, 25.0, 95.0))

    # Driving layup recalibration: reward guard touch/craft, keep non-elites mostly 70s.
    lay_touch_signal = remap(ft_pct, 0.66, 0.92, 0.0, 100.0)
    lay_craft_signal = remap(1.0 - assisted2, 0.20, 0.82, 0.0, 100.0)
    lay_rim_signal = remap(rim_share, 0.10, 0.52, 0.0, 100.0)
    lay_contact_signal = remap(fta36, 1.0, 10.0, 0.0, 100.0)
    lay_eff_signal = remap(two_pct, 0.46, 0.68, 0.0, 100.0)

    driving_layup_target = (
        44.0
        + 0.24 * lay_rim_signal
        + 0.24 * lay_eff_signal
        + 0.20 * lay_contact_signal
        + 0.18 * lay_touch_signal
        + 0.14 * lay_craft_signal
    )

    if is_guard:
        driving_layup_target += 1.5
        guard_skill = (
            0.40 * lay_touch_signal
            + 0.35 * lay_craft_signal
            + 0.25 * lay_contact_signal
        )
        if guard_skill >= 74.0 and usg >= 27.0 and lay_rim_signal >= 28.0:
            driving_layup_target = max(
                driving_layup_target, remap(guard_skill, 74.0, 95.0, 82.0, 93.0)
            )
        elif guard_skill >= 55.0:
            driving_layup_target = max(
                driving_layup_target, remap(guard_skill, 55.0, 90.0, 72.0, 84.0)
            )
        else:
            driving_layup_target = max(driving_layup_target, 68.0)

        # Soft cap low-rim guards so touch/craft can help, but not to elite tiers.
        if rim_share < 0.16:
            low_rim_cap = 82.0
            if usg >= 30.0 and lay_craft_signal >= 70.0:
                low_rim_cap = 86.0
            driving_layup_target = min(driving_layup_target, low_rim_cap)
        elif rim_share < 0.20:
            driving_layup_target = min(driving_layup_target, 87.0)

    final_attributes["Driving Layup"] = attr_clamp(
        clamp(driving_layup_target, 55.0, 95.0)
    )

    # Close shot recalibration: center/big interior touch should be reflected more
    # strongly than pure creation profile, while guards remain in realistic lanes.
    close_near_signal = remap(close_share, 0.06, 0.34, 0.0, 100.0)
    close_profile_signal = remap(rim_share + close_share, 0.18, 0.78, 0.0, 100.0)
    close_score = (
        0.32 * (close_profile_signal / 100.0)
        + 0.24 * (lay_eff_signal / 100.0)
        + 0.18 * (lay_contact_signal / 100.0)
        + 0.16 * (close_near_signal / 100.0)
        + 0.10 * (lay_touch_signal / 100.0)
    )
    close_shot_target = 50.0 + (34.0 * close_score)
    if is_center:
        close_shot_target += 4.0
        if rim_share >= 0.36:
            close_shot_target = max(close_shot_target, 66.0)
        if rim_share >= 0.50 and two_pct >= 0.58:
            close_shot_target = max(close_shot_target, 72.0)
    elif is_forward:
        close_shot_target += 1.0
    else:
        # Small guards with very low rim pressure should not spike close shot.
        if rim_share < 0.14 and lay_contact_signal < 45.0:
            close_shot_target = min(close_shot_target, 72.0)

    final_attributes["Close Shot"] = attr_clamp(clamp(close_shot_target, 25.0, 95.0))

    # Post attribute recalibration using tracking-first post-touch proxies.
    post_touch_signal = remap(hook_freq + fade_freq, 0.005, 0.14, 0.0, 100.0)
    post_interior_signal = remap(rim_share + close_share, 0.18, 0.72, 0.0, 100.0)
    post_mid_signal = remap(mid_share + long_mid_share, 0.06, 0.42, 0.0, 100.0)

    post_hook_score = (
        0.34 * remap(size_signal, 40.0, 100.0, 0.0, 100.0)
        + 0.24 * post_touch_signal
        + 0.18 * lay_contact_signal
        + 0.14 * lay_eff_signal
        + 0.10 * post_interior_signal
    ) / 100.0
    post_fade_score = (
        0.30 * post_mid_signal
        + 0.22 * lay_touch_signal
        + 0.20 * post_touch_signal
        + 0.18 * usage_score
        + 0.10 * remap(size_signal, 40.0, 100.0, 0.0, 100.0)
    ) / 100.0
    post_control_score = (
        0.34 * remap(size_signal, 40.0, 100.0, 0.0, 100.0)
        + 0.24 * lay_contact_signal
        + 0.18 * post_interior_signal
        + 0.14 * post_touch_signal
        + 0.10 * usage_score
    ) / 100.0

    post_hook_target = 38.0 + (42.0 * post_hook_score)
    post_fade_target = 38.0 + (44.0 * post_fade_score)
    post_control_target = 40.0 + (42.0 * post_control_score)

    if is_guard:
        if post_touch_signal < 22.0:
            post_hook_target = min(post_hook_target, 58.0)
            post_fade_target = min(post_fade_target, 68.0)
            post_control_target = min(post_control_target, 62.0)
    elif is_forward:
        if post_touch_signal < 20.0:
            post_hook_target = min(post_hook_target, 70.0)
            post_fade_target = min(post_fade_target, 76.0)
            post_control_target = min(post_control_target, 74.0)
        elif post_touch_signal >= 45.0 and usage_score >= 55.0:
            post_fade_target = max(post_fade_target, 74.0)
            post_control_target = max(post_control_target, 70.0)
    elif is_center:
        if post_touch_signal < 16.0:
            post_fade_target = min(post_fade_target, 80.0)
        if post_touch_signal >= 45.0 and lay_contact_signal >= 55.0:
            post_hook_target = max(post_hook_target, 74.0)
            post_control_target = max(post_control_target, 78.0)

    final_attributes["Post Hook"] = attr_clamp(clamp(post_hook_target, 25.0, 93.0))
    final_attributes["Post Fade"] = attr_clamp(clamp(post_fade_target, 25.0, 93.0))
    final_attributes["Post Control"] = attr_clamp(
        clamp(post_control_target, 25.0, 93.0)
    )

    # Playmaking recalibration using tracking-first passing/touch/drives data.
    pass_table_signal = clamp(
        0.28 * g_potential_ast_pg
        + 0.20 * g_ast_adj_pg
        + 0.16 * g_passes_made_pg
        + 0.14 * g_ast_to_pass_pct_adj
        + 0.12 * g_secondary_ast_pg
        + 0.10 * g_ft_ast_pg,
        0.0,
        100.0,
    )
    touch_orch_signal = clamp(
        0.34 * g_touches_pg
        + 0.28 * g_time_of_poss_pg
        + 0.20 * g_front_ct_touches_pg
        + 0.18 * g_avg_drib_per_touch,
        0.0,
        100.0,
    )
    drive_kick_signal = clamp(
        0.34 * g_drive_passes_pg
        + 0.22 * g_drive_ast_pg
        + 0.18 * g_drive_pass_rate
        + 0.12 * g_drive_ast_rate
        + 0.14 * g_drives_pg,
        0.0,
        100.0,
    )
    on_ball_pressure_signal = clamp(
        0.34 * g_drives_pg
        + 0.24 * g_time_of_poss_pg
        + 0.24 * g_avg_drib_per_touch
        + 0.18 * g_drive_tov_ctrl,
        0.0,
        100.0,
    )
    swb_burst_signal = clamp(
        0.32 * on_ball_pressure_signal
        + 0.24 * g_avg_speed_off
        + 0.18 * g_drive_fg_pct
        + 0.14 * athletic_signal
        + 0.12 * g_avg_speed,
        0.0,
        100.0,
    )

    handle_signal = clamp(
        0.28 * creation_2_score
        + 0.18 * g_tov_ctrl
        + 0.14 * g_usg
        + 0.18 * touch_orch_signal
        + 0.12 * drive_kick_signal
        + 0.10 * on_ball_pressure_signal,
        0.0,
        100.0,
    )
    pass_accuracy_signal = clamp(
        0.28 * g_ast
        + 0.18 * g_ast100
        + 0.24 * pass_table_signal
        + 0.16 * g_tov_ctrl
        + 0.14 * drive_kick_signal,
        0.0,
        100.0,
    )
    pass_iq_signal = clamp(
        0.20 * g_ast
        + 0.14 * g_ast100
        + 0.30 * pass_table_signal
        + 0.22 * g_tov_ctrl
        + 0.14 * touch_orch_signal,
        0.0,
        100.0,
    )
    pass_vision_signal = clamp(
        0.22 * g_ast
        + 0.16 * g_ast100
        + 0.26 * pass_table_signal
        + 0.24 * touch_orch_signal
        + 0.12 * drive_kick_signal,
        0.0,
        100.0,
    )

    ball_handle_target = 46.0 + 0.42 * handle_signal
    speed_with_ball_target = (
        41.0
        + 0.20 * handle_signal
        + 0.38 * swb_burst_signal
        + 0.08 * drive_kick_signal
        + (6.0 if is_guard else (2.0 if is_forward else -2.0))
    )
    pass_accuracy_target = 42.0 + 0.44 * pass_accuracy_signal
    pass_iq_target = 44.0 + 0.42 * pass_iq_signal
    pass_vision_target = 42.0 + 0.45 * pass_vision_signal

    if is_guard:
        if handle_signal >= 60.0:
            ball_handle_target = max(
                ball_handle_target, remap(handle_signal, 60.0, 92.0, 74.0, 91.0)
            )
        guard_swb_signal = max(swb_burst_signal, handle_signal)
        if guard_swb_signal >= 58.0:
            speed_with_ball_target = max(
                speed_with_ball_target, remap(guard_swb_signal, 58.0, 94.0, 73.0, 90.0)
            )
    elif is_forward:
        if touch_orch_signal < 24.0 and pass_table_signal < 24.0:
            pass_accuracy_target = min(pass_accuracy_target, 76.0)
            pass_iq_target = min(pass_iq_target, 78.0)
            pass_vision_target = min(pass_vision_target, 79.0)
        if tracking_drives_pg < 6.0 and tracking_time_of_poss_pg < 2.2:
            speed_with_ball_target = min(speed_with_ball_target, 71.0)
        if (
            tracking_drives_pg < 8.5
            and tracking_time_of_poss_pg < 2.2
            and tracking_avg_drib_per_touch < 1.8
        ):
            speed_with_ball_target = min(speed_with_ball_target, 72.0)

        # Heliocentric forward creators (Luka/LeBron archetype) should not sit
        # in slow-big movement tiers when they carry on-ball creation.
        heliocentric_forward_creator = (
            usg >= 28.0
            and ast_pct >= 22.0
            and tracking_drives_pg >= 8.0
            and tracking_time_of_poss_pg >= 3.5
            and tracking_avg_drib_per_touch >= 2.2
            and tracking_touches_pg >= 60.0
        )
        if heliocentric_forward_creator:
            forward_creator_signal = clamp(
                0.36 * on_ball_pressure_signal
                + 0.28 * handle_signal
                + 0.22 * game_burst_signal
                + 0.14 * remap(tracking_drives_pg, 8.0, 20.0, 0.0, 100.0),
                0.0,
                100.0,
            )
            forward_swb_floor = remap(forward_creator_signal, 30.0, 90.0, 74.0, 86.0)
            speed_with_ball_target = max(speed_with_ball_target, forward_swb_floor)
    elif is_center:
        ball_handle_target = min(ball_handle_target, 82.0)
        speed_with_ball_target = min(speed_with_ball_target, 78.0)
        if pass_table_signal < 45.0 or touch_orch_signal < 45.0:
            pass_accuracy_target = min(pass_accuracy_target, 74.0)
            pass_iq_target = min(pass_iq_target, 76.0)
            pass_vision_target = min(pass_vision_target, 78.0)
        # Keep genuine hub centers (Jokic archetype) clearly separated.
        if pass_table_signal >= 72.0 and touch_orch_signal >= 65.0 and g_ast >= 80.0:
            pass_accuracy_target = max(pass_accuracy_target, 82.0)
            pass_iq_target = max(pass_iq_target, 84.0)
            pass_vision_target = max(pass_vision_target, 84.0)
        if tracking_drives_pg < 4.0 and tracking_time_of_poss_pg < 2.0:
            speed_with_ball_target = min(speed_with_ball_target, 66.0)

    elite_ball_creator = (
        tracking_drives_pg >= 14.0
        and tracking_time_of_poss_pg >= 4.8
        and tracking_avg_drib_per_touch >= 3.5
    )
    if elite_ball_creator:
        ball_handle_target = max(
            ball_handle_target, remap(tracking_drives_pg, 14.0, 22.0, 80.0, 92.0)
        )
        speed_with_ball_target = max(
            speed_with_ball_target, remap(tracking_drives_pg, 14.0, 22.0, 78.0, 90.0)
        )

    # Explicit elite-passer rewards so top creators and hub bigs are not
    # compressed into average passing tiers.
    elite_creator = (
        ast_pct >= 34.0
        and tracking_potential_ast_pg >= 12.0
        and tracking_ast_adj_pg >= 9.0
        and tracking_ast_to_pass_pct_adj >= 0.16
        and tracking_touches_pg >= 70.0
    )
    strong_creator = (
        ast_pct >= 28.0
        and tracking_potential_ast_pg >= 9.5
        and tracking_ast_adj_pg >= 7.0
        and tracking_ast_to_pass_pct_adj >= 0.13
        and tracking_touches_pg >= 60.0
    )
    hub_center = (
        is_center
        and ast_pct >= 18.0
        and tracking_potential_ast_pg >= 6.0
        and tracking_ast_to_pass_pct_adj >= 0.095
        and tracking_touches_pg >= 55.0
    )
    elite_hub_center = (
        hub_center
        and ast_pct >= 24.0
        and tracking_potential_ast_pg >= 9.0
        and tracking_ast_adj_pg >= 6.8
    )

    if elite_creator:
        pass_accuracy_target = max(pass_accuracy_target, 88.0)
        pass_iq_target = max(pass_iq_target, 90.0)
        pass_vision_target = max(pass_vision_target, 92.0)
    elif strong_creator:
        creator_floor_pa = remap(tracking_potential_ast_pg, 9.5, 14.5, 80.0, 84.0)
        creator_floor_piq = creator_floor_pa + 2.0
        creator_floor_pv = creator_floor_pa + 4.0
        pass_accuracy_target = max(pass_accuracy_target, creator_floor_pa)
        pass_iq_target = max(pass_iq_target, creator_floor_piq)
        pass_vision_target = max(pass_vision_target, creator_floor_pv)

    if hub_center:
        pass_accuracy_target = max(pass_accuracy_target, 78.0)
        pass_iq_target = max(pass_iq_target, 80.0)
        pass_vision_target = max(pass_vision_target, 83.0)
    if elite_hub_center:
        pass_accuracy_target = max(pass_accuracy_target, 84.0)
        pass_iq_target = max(pass_iq_target, 86.0)
        pass_vision_target = max(pass_vision_target, 88.0)

    final_attributes["Ball Handle"] = attr_clamp(clamp(ball_handle_target, 25.0, 95.0))
    final_attributes["Speed with Ball"] = attr_clamp(
        clamp(speed_with_ball_target, 25.0, 95.0)
    )
    final_attributes["Pass Accuracy"] = attr_clamp(
        clamp(pass_accuracy_target, 25.0, 95.0)
    )
    final_attributes["Pass IQ"] = attr_clamp(clamp(pass_iq_target, 25.0, 95.0))
    final_attributes["Pass Vision"] = attr_clamp(clamp(pass_vision_target, 25.0, 95.0))

    # ── Standing Dunk recalibration ──────────────────────────────────────
    standing_dunk_target = (
        40.0
        + remap(dunks_share, 0.02, 0.25, 0.0, 20.0)
        + remap(dunks, 10.0, 200.0, 0.0, 14.0)
        + remap(rim_share, 0.15, 0.55, 0.0, 8.0)
        + remap(size_signal, 30.0, 100.0, 0.0, 12.0)
    )
    if is_center:
        standing_dunk_target += 4.0
        if rim_share >= 0.40 and dunks_share >= 0.12:
            standing_dunk_target = max(standing_dunk_target, 80.0)
        if rim_share >= 0.50 and dunks_share >= 0.18:
            standing_dunk_target = max(standing_dunk_target, 86.0)
    elif is_forward:
        standing_dunk_target += 2.0
        if dunks_share >= 0.08 and dunks >= 50.0:
            standing_dunk_target = max(standing_dunk_target, 74.0)
    elif is_guard:
        standing_dunk_target -= 4.0
        if dunks_share < 0.03:
            standing_dunk_target = min(standing_dunk_target, 58.0)
    if minutes < 600.0 or mpg < 14.0:
        standing_dunk_target = min(standing_dunk_target, 78.0)
    final_attributes["Standing Dunk"] = attr_clamp(
        clamp(standing_dunk_target, 25.0, 95.0)
    )

    # ── Driving Dunk recalibration ───────────────────────────────────────
    # Power-build factor: muscular, explosive builds dunk better.
    _age_explode = clamp(remap(age, 20.0, 38.0, 1.0, 0.30), 0.30, 1.0)
    driving_dunk_target = (
        42.0
        + remap(dunks_share, 0.01, 0.15, 0.0, 20.0)
        + remap(dunks, 5.0, 120.0, 0.0, 14.0)
        + 0.08 * _power_build
        + remap(tracking_avg_speed_off, 4.0, 5.2, 0.0, 6.0)
        + remap(1.0 - remap(age, 20.0, 36.0, 0.0, 1.0), 0.0, 1.0, 0.0, 6.0)
    )
    if is_guard:
        if dunks_share >= 0.05 and dunks >= 30.0:
            _pb_adj = remap(_power_build, 30.0, 80.0, -3.0, 3.0)
            driving_dunk_target = max(
                driving_dunk_target,
                78.0 + remap(dunks, 30.0, 120.0, 0.0, 10.0) + _pb_adj,
            )
        elif dunks_share >= 0.03 and dunks >= 20.0:
            _pb_adj = remap(_power_build, 30.0, 80.0, -3.0, 3.0)
            driving_dunk_target = max(
                driving_dunk_target, 70.0 + remap(dunks, 20.0, 60.0, 0.0, 8.0) + _pb_adj
            )
    elif is_forward:
        if dunks_share >= 0.10 and dunks >= 60.0:
            driving_dunk_target = max(
                driving_dunk_target, 82.0 + remap(dunks, 60.0, 150.0, 0.0, 8.0)
            )
        elif dunks_share >= 0.04 and dunks >= 20.0:
            driving_dunk_target = max(
                driving_dunk_target, 72.0 + remap(dunks, 20.0, 80.0, 0.0, 8.0)
            )
        elif (
            tracking_drives_pg >= 6.0
            and usg >= 23.0
            and (rim_share >= 0.13 or (height_in >= 79.0 and rim_share >= 0.09))
        ):
            # High-usage wing scorers who drive frequently but rarely dunk (KD / Tatum archetype):
            # they can finish at the rim but dunk infrequently vs. drive volume.
            # Tall wings (6'7"+) qualify at lower rim_share since they also score off glass/euro-step.
            _wing_rim_floor = (
                62.0
                + remap(tracking_drives_pg, 6.0, 18.0, 0.0, 16.0)
                + remap(height_in, 75.0, 84.0, 0.0, 8.0)
            )
            driving_dunk_target = max(driving_dunk_target, _wing_rim_floor)
    elif is_center:
        if dunks_share >= 0.15 and rim_share >= 0.40:
            driving_dunk_target = max(driving_dunk_target, 76.0)
    if dunks_share < 0.01 and rim_share < 0.12:
        driving_dunk_target = min(driving_dunk_target, 60.0)
    if minutes < 600.0 or mpg < 14.0:
        driving_dunk_target = min(driving_dunk_target, 80.0)
    # Explosive dunker boost for muscular, powerful guards/wings.
    # Boost scales with dunk frequency: players who rarely convert drives into dunks
    # receive a proportionally smaller bonus regardless of their athleticism.
    if (is_guard or is_forward) and dunks_share >= 0.03 and dunks >= 15:
        if is_guard:
            _boost_scale = clamp(remap(dunks_share, 0.03, 0.06, 0.25, 1.0), 0.0, 1.0)
        else:  # is_forward
            _boost_scale = clamp(remap(dunks_share, 0.03, 0.08, 0.25, 1.0), 0.0, 1.0)
        _explosive_boost = (
            remap(_power_build, 40.0, 85.0, 0.0, 12.0) * _age_explode * _boost_scale
        )
        _youth_boost = clamp(remap(age, 20.0, 33.0, 4.0, 0.0), 0.0, 4.0) * _boost_scale
        driving_dunk_target += _explosive_boost + _youth_boost
    final_attributes["Driving Dunk"] = attr_clamp(
        clamp(driving_dunk_target, 25.0, 95.0)
    )

    # ── Offensive Rebound recalibration ──────────────────────────────────
    # Use box-score oreb_pct + tracking rebound chances when available.
    tracking_oreb_chance_pct = as_float(blended_row, "tracking_oreb_chance_pct")
    tracking_oreb_chances_pg = as_float(blended_row, "tracking_oreb_chances_pg")
    tracking_box_outs_off_pg = as_float(blended_row, "tracking_box_outs_off_pg")
    oreb_extra = (
        remap(tracking_oreb_chance_pct, 0.05, 0.35, 0.0, 6.0)
        + remap(tracking_oreb_chances_pg, 0.5, 6.0, 0.0, 4.0)
        + remap(tracking_box_outs_off_pg, 0.1, 2.0, 0.0, 3.0)
    )
    oreb_target = (
        38.0
        + remap(orb_pct, 1.0, 16.0, 0.0, 30.0)
        + remap(size_signal, 20.0, 100.0, 0.0, 12.0)
        + remap(minutes, 500.0, 2800.0, 0.0, 6.0)
        + oreb_extra
    )
    if is_center:
        oreb_target += 4.0
        if orb_pct >= 8.0:
            oreb_target = max(oreb_target, 82.0)
        if orb_pct >= 12.0:
            oreb_target = max(oreb_target, 88.0)
    elif is_forward:
        oreb_target += 2.0
        if orb_pct >= 6.0:
            oreb_target = max(oreb_target, 76.0)
    elif is_guard:
        if orb_pct < 2.0:
            oreb_target = min(oreb_target, 60.0)
    if minutes < 500.0 or mpg < 12.0:
        oreb_target = min(oreb_target, 72.0)
    final_attributes["Offensive Rebound"] = attr_clamp(clamp(oreb_target, 25.0, 95.0))

    # ── Defensive Rebound recalibration ──────────────────────────────────
    tracking_dreb_chance_pct = as_float(blended_row, "tracking_dreb_chance_pct")
    tracking_dreb_chances_pg = as_float(blended_row, "tracking_dreb_chances_pg")
    tracking_box_outs_def_pg = as_float(blended_row, "tracking_box_outs_def_pg")
    dreb_extra = (
        remap(tracking_dreb_chance_pct, 0.20, 0.75, 0.0, 6.0)
        + remap(tracking_dreb_chances_pg, 3.0, 14.0, 0.0, 4.0)
        + remap(tracking_box_outs_def_pg, 0.5, 4.0, 0.0, 3.0)
    )
    dreb_target = (
        42.0
        + remap(drb_pct, 8.0, 30.0, 0.0, 28.0)
        + remap(size_signal, 20.0, 100.0, 0.0, 12.0)
        + remap(minutes, 500.0, 2800.0, 0.0, 6.0)
        + dreb_extra
    )
    if is_center:
        dreb_target += 4.0
        if drb_pct >= 22.0:
            dreb_target = max(dreb_target, 86.0)
        if drb_pct >= 28.0:
            dreb_target = max(dreb_target, 92.0)
    elif is_forward:
        dreb_target += 2.0
        if drb_pct >= 18.0:
            dreb_target = max(dreb_target, 80.0)
    elif is_guard:
        if drb_pct < 10.0:
            dreb_target = min(dreb_target, 62.0)
    if minutes < 500.0 or mpg < 12.0:
        dreb_target = min(dreb_target, 74.0)
    final_attributes["Defensive Rebound"] = attr_clamp(clamp(dreb_target, 25.0, 95.0))

    # ── Overall Durability recalibration ─────────────────────────────────
    durability_target = (
        35.0
        + remap(durability_availability_score, 40.0, 100.0, 0.0, 35.0)
        + remap(mpg, 12.0, 36.0, 0.0, 12.0)
        + remap(1.0 - remap(age, 22.0, 38.0, 0.0, 1.0), 0.0, 1.0, 0.0, 6.0)
    )
    # Ironman tiers — single season elite availability
    if durability_availability_score >= 95.0 and mpg >= 28.0:
        durability_target = max(durability_target, 90.0)
    # Multi-season ironman: 90%+ this season AND at least 2 prior seasons of 70+ games
    elif durability_availability_score >= 90.0 and mpg >= 26.0 and ironman_seasons >= 2:
        durability_target = max(durability_target, 86.0)
    # Consistent history ironman: 3+ seasons of 70+ games (even if slightly down this year)
    if ironman_seasons >= 3 and durability_availability_score >= 75.0:
        durability_target = max(durability_target, 83.0)
    if durability_availability_score < 60.0:
        durability_target = min(durability_target, 68.0)
    # Every NBA player with meaningful minutes has a baseline durability floor —
    # even injury-prone players are professional athletes.
    if mpg >= 20.0:
        durability_target = max(durability_target, 60.0)
    elif mpg >= 15.0:
        durability_target = max(durability_target, 55.0)
    elif mpg >= 10.0:
        durability_target = max(durability_target, 50.0)
    final_attributes["Overall Durability"] = attr_clamp(
        clamp(durability_target, 25.0, 95.0)
    )

    # ── Potential recalibration ──────────────────────────────────────────
    # Potential = how much better a player can still become.
    # Young elite players → 90-95.  Prime superstars → 85-92.
    # Long-time veterans → declines with age; even great ones cap at ~88.
    star_signal = clamp(
        0.40 * usage_score
        + 0.30 * efficiency_score
        + 0.20 * creation_2_score
        + 0.10 * workload_score,
        0.0,
        100.0,
    )
    # Base: youth-weighted with star talent.
    potential_target = (
        35.0
        + remap(max(0.0, 30.0 - age), 0.0, 11.0, 0.0, 30.0)  # youth bonus (19→30 age)
        + remap(star_signal, 20.0, 90.0, 0.0, 18.0)  # talent bonus
    )
    # --- Young superstars (≤24): 90-95 ---
    if age <= 22.0 and usg >= 24.0 and ts_pct >= 0.55:
        potential_target = max(potential_target, remap(age, 19.0, 22.0, 95.0, 93.0))
    elif age <= 24.0 and usg >= 24.0 and ts_pct >= 0.55:
        potential_target = max(potential_target, remap(age, 22.0, 24.0, 93.0, 90.0))
    elif age <= 22.0 and mpg >= 20.0:
        potential_target = max(potential_target, remap(age, 19.0, 22.0, 93.0, 88.0))
    elif age <= 24.0 and usg >= 20.0 and mpg >= 20.0:
        potential_target = max(potential_target, remap(age, 22.0, 24.0, 89.0, 85.0))
    # --- Prime-age stars (25-28): 85-92 ---
    if 24.0 < age <= 28.0 and usg >= 28.0 and ts_pct >= 0.56:
        potential_target = max(potential_target, remap(age, 25.0, 28.0, 92.0, 88.0))
    elif 24.0 < age <= 28.0 and usg >= 22.0 and mpg >= 26.0:
        potential_target = max(potential_target, remap(age, 25.0, 28.0, 87.0, 82.0))
    # --- Peak/late-prime (29-31): max ~85-88 ---
    if 28.0 < age <= 31.0 and usg >= 26.0 and ts_pct >= 0.56:
        potential_target = max(potential_target, remap(age, 29.0, 31.0, 87.0, 83.0))
    elif 28.0 < age <= 31.0 and usg >= 20.0 and mpg >= 24.0:
        potential_target = max(potential_target, remap(age, 29.0, 31.0, 82.0, 76.0))
    # --- Veterans (32+): production-based ceiling with age penalty ---
    if age >= 32.0:
        vet_production = clamp(0.50 * usage_score + 0.50 * efficiency_score, 0.0, 100.0)
        vet_ceiling = remap(vet_production, 25.0, 85.0, 62.0, 88.0)
        age_penalty = remap(age, 32.0, 42.0, 2.0, 16.0)
        potential_target = max(potential_target, vet_ceiling - age_penalty)
    # --- NBA activity floor: any player with real minutes gets a realistic potential ---
    # Role players and bench contributors max out lower, but 40 is unrealistically low.
    if mpg >= 15.0:
        age_potential_floor = clamp(remap(age, 22.0, 38.0, 75.0, 48.0), 48.0, 75.0)
        potential_target = max(potential_target, age_potential_floor)
    elif mpg >= 10.0:
        age_potential_floor = clamp(remap(age, 22.0, 38.0, 65.0, 42.0), 42.0, 65.0)
        potential_target = max(potential_target, age_potential_floor)
    final_attributes["Potential"] = attr_clamp(clamp(potential_target, 25.0, 95.0))

    # Intangibles is fixed at 25 for all players and excluded from OVR.
    final_attributes["Intangibles"] = 25

    elite_guard_lock = (
        is_guard
        and stl_pct >= 2.0
        and hustle_deflections_pg >= 2.0
        and (
            defense_dash_3pt_stop_delta >= 0.010
            or defense_dash_overall_stop_delta >= 0.010
        )
        and minutes >= 900.0
    )
    elite_wing_lock = (
        is_forward
        and stl_pct
        >= 1.5  # must be an actual disruptive defender, not just high-volume hustle
        and hustle_deflections_pg >= 1.8
        and hustle_contested_3pt_pg >= 1.7
        and defense_dash_overall_stop_delta >= 0.010
        and minutes >= 1100.0
    )
    elite_rim_anchor = (
        (is_center or is_forward)
        and blk_pct >= 3.6
        and hustle_contested_2pt_pg >= 3.0
        and defense_dash_lt6_stop_delta >= 0.025
        and minutes >= 1200.0
    )

    if elite_guard_lock:
        final_attributes["Perimeter Defense"] = max(
            final_attributes["Perimeter Defense"], 86
        )
        final_attributes["Steal"] = max(final_attributes["Steal"], 88)
        final_attributes["Help Defense IQ"] = max(
            final_attributes["Help Defense IQ"], 84
        )
        final_attributes["Pass Perception"] = max(
            final_attributes["Pass Perception"], 88
        )
        final_attributes["Defensive Consistency"] = max(
            final_attributes["Defensive Consistency"], 84
        )

    if elite_wing_lock:
        final_attributes["Perimeter Defense"] = max(
            final_attributes["Perimeter Defense"], 85
        )
        final_attributes["Help Defense IQ"] = max(
            final_attributes["Help Defense IQ"], 84
        )
        final_attributes["Pass Perception"] = max(
            final_attributes["Pass Perception"], 84
        )
        final_attributes["Defensive Consistency"] = max(
            final_attributes["Defensive Consistency"], 83
        )

    if elite_rim_anchor:
        final_attributes["Interior Defense"] = max(
            final_attributes["Interior Defense"], 88
        )
        final_attributes["Block"] = max(final_attributes["Block"], 90)
        final_attributes["Help Defense IQ"] = max(
            final_attributes["Help Defense IQ"], 86
        )
        final_attributes["Defensive Consistency"] = max(
            final_attributes["Defensive Consistency"], 84
        )

    legacy_elite_perimeter = (
        (is_guard or is_forward)
        and minutes >= 900.0
        and defense_peak_signal
        >= 40.0  # career-peak signal; scaled for NBA site DEF_WS range
        and stl_pct >= 1.6
        and dws
        >= 0.11  # raised from 0.09: DWS 0.11+ separates elite from good (Kawhi=0.134, Curry=0.095)
    )
    legendary_perimeter_specialist = (
        (is_guard or is_forward)
        and minutes >= 1200.0
        and defense_peak_signal >= 55.0
        and stl_pct >= 2.0
        and dws >= 0.13  # NBA site DEF_WS scale (was 2.0 for BR scale)
    )
    elite_switch_big = (
        is_forward
        and minutes >= 1200.0
        and defense_peak_signal >= 52.0
        and dws >= 0.14  # NBA site DEF_WS scale (was 2.2 for BR scale)
        and (stl_pct >= 1.8 or blk_pct >= 2.5)
    )

    if legacy_elite_perimeter:
        elite_pd_floor = int(round(remap(defense_peak_signal, 48.0, 84.0, 84.0, 90.0)))
        final_attributes["Perimeter Defense"] = max(
            final_attributes["Perimeter Defense"], elite_pd_floor
        )
        final_attributes["Steal"] = max(final_attributes["Steal"], elite_pd_floor)
        final_attributes["Pass Perception"] = max(
            final_attributes["Pass Perception"], elite_pd_floor - 1
        )
        final_attributes["Help Defense IQ"] = max(
            final_attributes["Help Defense IQ"], elite_pd_floor - 1
        )
        final_attributes["Defensive Consistency"] = max(
            final_attributes["Defensive Consistency"], elite_pd_floor - 1
        )

    if legendary_perimeter_specialist:
        legend_pd_floor = int(round(remap(defense_peak_signal, 60.0, 90.0, 88.0, 93.0)))
        final_attributes["Perimeter Defense"] = max(
            final_attributes["Perimeter Defense"], legend_pd_floor
        )
        final_attributes["Steal"] = max(final_attributes["Steal"], legend_pd_floor - 1)
        final_attributes["Pass Perception"] = max(
            final_attributes["Pass Perception"], legend_pd_floor - 1
        )
        final_attributes["Help Defense IQ"] = max(
            final_attributes["Help Defense IQ"], legend_pd_floor - 1
        )
        final_attributes["Defensive Consistency"] = max(
            final_attributes["Defensive Consistency"], legend_pd_floor - 1
        )

    if elite_switch_big:
        switch_pd_floor = int(round(remap(defense_peak_signal, 58.0, 90.0, 84.0, 90.0)))
        final_attributes["Perimeter Defense"] = max(
            final_attributes["Perimeter Defense"], switch_pd_floor
        )
        final_attributes["Help Defense IQ"] = max(
            final_attributes["Help Defense IQ"], switch_pd_floor
        )
        final_attributes["Defensive Consistency"] = max(
            final_attributes["Defensive Consistency"], switch_pd_floor - 1
        )

    # High-usage heliocentric guards can generate steals but are rarely true
    # elite point-of-attack stoppers without exceptional disruption rates.
    # DBPM bonus allows quality defensive heliocentrics to earn higher caps.
    heliocentric_guard = is_guard and ((usg >= 28.0 and ast_pct >= 30.0) or usg >= 32.0)
    if heliocentric_guard and stl_pct < 2.8:
        pd_cap_base = remap(stl_pct, 1.4, 2.8, 53.0, 65.0)
        pd_dbpm_bonus = clamp(remap(dbpm, 0.0, 2.5, 0.0, 10.0), 0.0, 10.0)
        pd_cap = int(round(pd_cap_base + pd_dbpm_bonus))
        steal_cap = min(78, pd_cap + 2)
        pp_cap = min(76, pd_cap + 1)
        hdiq_cap = min(76, pd_cap + 1)
        dc_cap = min(75, pd_cap)
        final_attributes["Perimeter Defense"] = min(
            final_attributes["Perimeter Defense"], pd_cap
        )
        final_attributes["Steal"] = min(final_attributes["Steal"], steal_cap)
        final_attributes["Pass Perception"] = min(
            final_attributes["Pass Perception"], pp_cap
        )
        final_attributes["Help Defense IQ"] = min(
            final_attributes["Help Defense IQ"], hdiq_cap
        )
        final_attributes["Defensive Consistency"] = min(
            final_attributes["Defensive Consistency"], dc_cap
        )

    scoring_guard = is_guard and usg >= 30.0 and ast_pct < 30.0
    if scoring_guard and stl_pct < 2.4:
        score_guard_pd_cap = int(round(remap(stl_pct, 1.2, 2.4, 66.0, 78.0)))
        score_guard_stl_cap = min(80, score_guard_pd_cap + 2)
        score_guard_hdiq_cap = min(79, score_guard_pd_cap + 1)
        score_guard_pp_cap = min(79, score_guard_pd_cap + 1)
        score_guard_dc_cap = min(78, score_guard_pd_cap)
        final_attributes["Perimeter Defense"] = min(
            final_attributes["Perimeter Defense"], score_guard_pd_cap
        )
        final_attributes["Steal"] = min(final_attributes["Steal"], score_guard_stl_cap)
        final_attributes["Help Defense IQ"] = min(
            final_attributes["Help Defense IQ"], score_guard_hdiq_cap
        )
        final_attributes["Pass Perception"] = min(
            final_attributes["Pass Perception"], score_guard_pp_cap
        )
        final_attributes["Defensive Consistency"] = min(
            final_attributes["Defensive Consistency"], score_guard_dc_cap
        )

    # Heliocentric forwards — high-usage ball-dominant SF/PF who carry the offense
    # but are not genuine perimeter stoppers (e.g. LeBron at 38+, Giannis without
    # elite stl numbers).  Mirror the heliocentric guard cap for forwards so their
    # PD can't be inflated by the raw formula or legacy floors.
    heliocentric_forward = (
        is_forward
        and not is_center
        and ((usg >= 27.0 and ast_pct >= 27.0) or usg >= 32.0)
        and stl_pct < 2.5
    )
    if heliocentric_forward:
        hf_pd_cap_base = remap(stl_pct, 1.0, 2.5, 60.0, 75.0)
        hf_pd_dbpm_bonus = clamp(remap(dbpm, -1.0, 2.0, 0.0, 8.0), 0.0, 8.0)
        hf_pd_cap = int(round(hf_pd_cap_base + hf_pd_dbpm_bonus))
        hf_steal_cap = min(78, hf_pd_cap + 4)
        hf_pp_cap = min(76, hf_pd_cap + 2)
        hf_hdiq_cap = min(78, hf_pd_cap + 4)
        hf_dc_cap = min(75, hf_pd_cap)
        final_attributes["Perimeter Defense"] = min(
            final_attributes["Perimeter Defense"], hf_pd_cap
        )
        final_attributes["Steal"] = min(final_attributes["Steal"], hf_steal_cap)
        final_attributes["Pass Perception"] = min(
            final_attributes["Pass Perception"], hf_pp_cap
        )
        final_attributes["Help Defense IQ"] = min(
            final_attributes["Help Defense IQ"], hf_hdiq_cap
        )
        final_attributes["Defensive Consistency"] = min(
            final_attributes["Defensive Consistency"], hf_dc_cap
        )

    if is_guard:
        guard_id_cap = 50
        guard_id_cap += int(round(remap(stl_pct, 1.0, 3.0, 0.0, 4.0)))
        guard_id_cap += int(round(remap(blk_pct, 0.3, 2.6, 0.0, 6.0)))
        if height_in >= 77.5:
            guard_id_cap += 2
        if blk_pct >= 2.0:
            guard_id_cap += 2
        final_attributes["Interior Defense"] = min(
            final_attributes["Interior Defense"], int(clamp(guard_id_cap, 50, 62))
        )

    # Rebounding recalibration: separate true rebounders from guard/creator stat padding.
    orb_target = (
        40.0
        + 0.44 * p_oreb
        + 0.18 * size_signal
        + 0.10 * p_minutes
        + (8.0 if is_center else (4.0 if is_forward else 0.0))
    )
    drb_target = (
        42.0
        + 0.46 * p_dreb
        + 0.22 * size_signal
        + 0.12 * p_minutes
        + (7.0 if is_center else (4.0 if is_forward else 0.0))
    )
    final_attributes["Offensive Rebound"] = attr_clamp(
        clamp(
            0.45 * final_attributes["Offensive Rebound"] + 0.55 * orb_target, 35.0, 95.0
        )
    )
    final_attributes["Defensive Rebound"] = attr_clamp(
        clamp(
            0.45 * final_attributes["Defensive Rebound"] + 0.55 * drb_target, 40.0, 95.0
        )
    )

    if is_guard:
        guard_orb_cap = remap(orb_pct, 0.8, 6.5, 44.0, 74.0)
        guard_drb_cap = remap(drb_pct, 7.0, 18.0, 52.0, 80.0)
        if height_in >= 77.5:
            guard_orb_cap += 2.0
            guard_drb_cap += 2.0
        if usg >= 28.0:
            guard_orb_cap -= 3.0
            guard_drb_cap -= 4.0
        final_attributes["Offensive Rebound"] = min(
            final_attributes["Offensive Rebound"],
            attr_clamp(clamp(guard_orb_cap, 44.0, 78.0)),
        )
        final_attributes["Defensive Rebound"] = min(
            final_attributes["Defensive Rebound"],
            attr_clamp(clamp(guard_drb_cap, 25.0, 82.0)),
        )

    if is_center:
        center_orb_floor = remap(p_oreb, 60.0, 98.0, 66.0, 84.0)
        center_drb_floor = remap(p_dreb, 62.0, 99.0, 74.0, 88.0)
        center_orb_cap = remap(orb_pct, 6.0, 15.0, 72.0, 90.0)
        center_drb_cap = remap(drb_pct, 18.0, 36.0, 80.0, 92.0)
        final_attributes["Offensive Rebound"] = max(
            final_attributes["Offensive Rebound"],
            attr_clamp(clamp(center_orb_floor, 64.0, 84.0)),
        )
        final_attributes["Defensive Rebound"] = max(
            final_attributes["Defensive Rebound"],
            attr_clamp(clamp(center_drb_floor, 72.0, 88.0)),
        )
        final_attributes["Offensive Rebound"] = min(
            final_attributes["Offensive Rebound"],
            attr_clamp(clamp(center_orb_cap, 70.0, 90.0)),
        )
        final_attributes["Defensive Rebound"] = min(
            final_attributes["Defensive Rebound"],
            attr_clamp(clamp(center_drb_cap, 78.0, 92.0)),
        )
    elif is_forward:
        forward_orb_floor = remap(p_oreb, 40.0, 95.0, 54.0, 78.0)
        forward_drb_floor = remap(p_dreb, 45.0, 96.0, 62.0, 84.0)
        forward_orb_cap = remap(orb_pct, 2.0, 10.0, 58.0, 84.0)
        forward_drb_cap = remap(drb_pct, 10.0, 30.0, 66.0, 88.0)
        if usg >= 30.0 and ast_pct >= 25.0:
            forward_orb_cap -= 3.0
            forward_drb_cap -= 3.0
        final_attributes["Offensive Rebound"] = max(
            final_attributes["Offensive Rebound"],
            attr_clamp(clamp(forward_orb_floor, 52.0, 78.0)),
        )
        final_attributes["Defensive Rebound"] = max(
            final_attributes["Defensive Rebound"],
            attr_clamp(clamp(forward_drb_floor, 60.0, 84.0)),
        )
        final_attributes["Offensive Rebound"] = min(
            final_attributes["Offensive Rebound"],
            attr_clamp(clamp(forward_orb_cap, 56.0, 84.0)),
        )
        final_attributes["Defensive Rebound"] = min(
            final_attributes["Defensive Rebound"],
            attr_clamp(clamp(forward_drb_cap, 64.0, 88.0)),
        )

    # Position dunk ladder:
    # guards -> driving priority, standing low;
    # bigs -> standing priority, driving lower;
    # SF -> middle, but still driving > standing.
    if is_guard:
        guard_standing_cap = 48
        if dunks_share >= 0.05:
            guard_standing_cap = 55
        if dunks_share >= 0.08:
            guard_standing_cap = 62
        final_attributes["Standing Dunk"] = min(
            final_attributes["Standing Dunk"], guard_standing_cap
        )

        drive_guard_floor = attr_clamp(
            48.0 + 0.22 * dunk_explosive_signal + 0.12 * _power_build
        )
        final_attributes["Driving Dunk"] = max(
            final_attributes["Driving Dunk"], drive_guard_floor
        )
        final_attributes["Driving Dunk"] = max(
            final_attributes["Driving Dunk"], final_attributes["Standing Dunk"] + 8
        )
        # Dunk-frequency cap: guards who rarely convert drives into dunks
        # should not reach elite dunker tiers regardless of athleticism.
        if dunks_share < 0.03:
            final_attributes["Driving Dunk"] = min(final_attributes["Driving Dunk"], 72)
        elif dunks_share < 0.06:
            final_attributes["Driving Dunk"] = min(final_attributes["Driving Dunk"], 84)

    if is_center:
        stand_big_floor = attr_clamp(
            54.0
            + 0.18 * remap(size_signal, 40.0, 100.0, 0.0, 100.0)
            + 0.28 * p_dunk_share
            + 0.10 * p_dunks
        )
        stand_big_floor = min(stand_big_floor, 90)

        # Only true elite lob/putback centers should enter low-90s tier.
        elite_center_dunker = (
            dunks_share >= 0.24 and rim_share >= 0.55 and p_dunk_share >= 90.0
        )
        if elite_center_dunker:
            stand_big_floor = max(stand_big_floor, 92)

        # Skill hubs without elite vertical dunk profile (e.g., Jokic archetype)
        # should stay below top dunk tiers.
        if dunks_share < 0.18:
            stand_big_floor = min(stand_big_floor, 86)
        elif dunks_share < 0.24:
            stand_big_floor = min(stand_big_floor, 89)

        final_attributes["Standing Dunk"] = max(
            final_attributes["Standing Dunk"], stand_big_floor
        )

        drive_big_cap = 66
        if rim_share < 0.18:
            drive_big_cap = 58
        elif rim_share < 0.24:
            drive_big_cap = 62
        if usg < 22.0:
            drive_big_cap = min(drive_big_cap, 62)
        if usg < 18.0:
            drive_big_cap = min(drive_big_cap, 58)
        # Elite athletic centers who actually dunk on drives should not be capped
        # at traditional center levels. Require significant drive volume to prevent
        # lob/putback centers (e.g. Gobert) from benefiting here.
        if dunks_share >= 0.20 and dunks >= 80.0 and tracking_drives_pg >= 3.0:
            drive_big_cap = max(
                drive_big_cap, 80 + int(remap(dunks, 80.0, 200.0, 0.0, 15.0))
            )
        elif dunks_share >= 0.12 and dunks >= 40.0 and tracking_drives_pg >= 2.0:
            drive_big_cap = max(
                drive_big_cap, 72 + int(remap(dunks, 40.0, 120.0, 0.0, 10.0))
            )
        final_attributes["Driving Dunk"] = min(
            final_attributes["Driving Dunk"], drive_big_cap
        )
        final_attributes["Driving Dunk"] = min(
            final_attributes["Driving Dunk"],
            max(58, final_attributes["Standing Dunk"] - 4),
        )

    is_true_pf = ("PF" in position.upper()) and ("SF" not in position.upper())
    if is_true_pf:
        pf_stand_floor = attr_clamp(
            56.0
            + 0.22 * remap(size_signal, 40.0, 100.0, 0.0, 100.0)
            + 0.18 * p_dunk_share
        )
        final_attributes["Standing Dunk"] = max(
            final_attributes["Standing Dunk"], pf_stand_floor
        )

        pf_drive_cap = 70
        if usg < 21.0:
            pf_drive_cap = 66
        if rim_share < 0.20:
            pf_drive_cap = min(pf_drive_cap, 62)
        # Athletic PFs who drive and explode to the rim (Giannis, Zion archetype)
        # should not be capped at the same level as stretch PFs.
        if dunks_share >= 0.18 and tracking_drives_pg >= 8.0:
            pf_drive_cap = max(
                pf_drive_cap, 88 + int(remap(dunks_share, 0.18, 0.30, 0.0, 6.0))
            )
        elif dunks_share >= 0.10 and tracking_drives_pg >= 4.0:
            pf_drive_cap = max(
                pf_drive_cap, 76 + int(remap(dunks_share, 0.10, 0.25, 0.0, 8.0))
            )
        elif dunks_share >= 0.07 and tracking_drives_pg >= 3.0:
            pf_drive_cap = max(
                pf_drive_cap, 72 + int(remap(dunks_share, 0.07, 0.15, 0.0, 6.0))
            )
        final_attributes["Driving Dunk"] = min(
            final_attributes["Driving Dunk"], pf_drive_cap
        )
        # Athletic drive-heavy PFs (Giannis, Zion) can have DrDnk >= StDnk; stretch PFs cannot.
        if dunks_share >= 0.18 and tracking_drives_pg >= 8.0:
            _pf_std_gap = -2  # DrDnk can exceed StDnk by up to 2
        elif dunks_share >= 0.10 and tracking_drives_pg >= 4.0:
            _pf_std_gap = 2  # DrDnk up to StDnk-2
        else:
            _pf_std_gap = 4  # Default: DrDnk <= StDnk-4
        final_attributes["Driving Dunk"] = min(
            final_attributes["Driving Dunk"],
            max(56, final_attributes["Standing Dunk"] - _pf_std_gap),
        )

    is_sf = (
        ("SF" in position.upper())
        and ("PF" not in position.upper())
        and ("C" not in position.upper())
    )
    if is_sf:
        # Cap SD before using it as a DD floor to avoid uncapped SD inflating DD.
        final_attributes["Standing Dunk"] = min(final_attributes["Standing Dunk"], 78)
        final_attributes["Driving Dunk"] = max(
            final_attributes["Driving Dunk"], final_attributes["Standing Dunk"] + 3
        )
        # Dunk-frequency cap: SFs who rarely dunk should not reach elite-dunker territory.
        if dunks_share < 0.05:
            final_attributes["Driving Dunk"] = min(final_attributes["Driving Dunk"], 78)
        elif dunks_share < 0.08:
            final_attributes["Driving Dunk"] = min(final_attributes["Driving Dunk"], 84)

    # Dependency smoothing to avoid contradictory outputs.
    final_attributes["Pass IQ"] = max(
        final_attributes["Pass IQ"], final_attributes["Pass Accuracy"] - 4
    )
    final_attributes["Pass Vision"] = max(
        final_attributes["Pass Vision"], final_attributes["Pass Accuracy"] - 2
    )
    vertical_dunk_factor = 0.55
    if is_center:
        vertical_dunk_factor = 0.40
    elif is_forward:
        vertical_dunk_factor = 0.48
    final_attributes["Driving Dunk"] = max(
        final_attributes["Driving Dunk"],
        int(round(vertical_dunk_factor * final_attributes["Vertical"])),
    )
    if is_guard:
        guard_mobility_floor = attr_clamp(
            48.0 + 0.24 * creation_2_score + 0.18 * p_stl + 0.10 * p_age_youth
        )
        final_attributes["Speed"] = max(final_attributes["Speed"], guard_mobility_floor)
        final_attributes["Agility"] = max(
            final_attributes["Agility"], guard_mobility_floor + 2
        )
        # Rotation guards should never have unrealistically low speed;
        # even the slowest NBA rotation guard is a professional athlete.
        if mpg >= 18.0:
            _guard_mpg_speed_floor = attr_clamp(58.0 + remap(mpg, 18.0, 35.0, 0.0, 5.0))
            final_attributes["Speed"] = max(
                final_attributes["Speed"], _guard_mpg_speed_floor
            )
        high_on_ball_guard = (
            tracking_drives_pg >= 11.0
            and tracking_avg_drib_per_touch >= 3.3
            and tracking_time_of_poss_pg >= 4.5
        )
        if high_on_ball_guard:
            guard_handle_floor = remap(tracking_drives_pg, 11.0, 18.0, 80.0, 88.0)
            guard_swb_floor = remap(tracking_drives_pg, 11.0, 18.0, 80.0, 89.0)
            final_attributes["Ball Handle"] = max(
                final_attributes["Ball Handle"], attr_clamp(guard_handle_floor)
            )
            final_attributes["Speed with Ball"] = max(
                final_attributes["Speed with Ball"], attr_clamp(guard_swb_floor)
            )
            final_attributes["Speed with Ball"] = max(
                final_attributes["Speed with Ball"], final_attributes["Speed"] + 2
            )
    if is_forward:
        forward_agility_floor = attr_clamp(
            52.0 + 0.22 * athletic_signal + 0.16 * p_age_youth + 0.12 * p_stl
        )
        final_attributes["Agility"] = max(
            final_attributes["Agility"], forward_agility_floor
        )

        # Athletic forwards who drive and attack: speed/agility floor from game burst.
        if tracking_drives_pg >= 6.0 and mpg >= 20.0:
            forward_burst_floor = remap(game_burst_signal, 25.0, 85.0, 62.0, 82.0)
            forward_agi_burst_floor = remap(game_burst_signal, 25.0, 85.0, 66.0, 84.0)
            final_attributes["Speed"] = max(
                final_attributes["Speed"], attr_clamp(forward_burst_floor)
            )
            final_attributes["Agility"] = max(
                final_attributes["Agility"], attr_clamp(forward_agi_burst_floor)
            )
            # Elite wing scorers who are tall (6'7"+), high-usage, and still actively driving:
            # their low tracking avg-speed underestimates their game mobility.
            if (
                height_in >= 79.0
                and usg >= 27.0
                and tracking_drives_pg >= 7.0
                and mpg >= 26.0
            ):
                _elite_wing_spd_floor = attr_clamp(
                    68.0 + remap(tracking_drives_pg, 7.0, 16.0, 0.0, 8.0)
                )
                final_attributes["Speed"] = max(
                    final_attributes["Speed"], _elite_wing_spd_floor
                )
                final_attributes["Agility"] = max(
                    final_attributes["Agility"], attr_clamp(_elite_wing_spd_floor + 2.0)
                )

        heliocentric_forward_creator = (
            usg >= 28.0
            and ast_pct >= 22.0
            and tracking_drives_pg >= 8.0
            and tracking_time_of_poss_pg >= 3.5
            and tracking_avg_drib_per_touch >= 2.2
            and tracking_touches_pg >= 60.0
        )
        if heliocentric_forward_creator:
            creator_forward_mobility_signal = clamp(
                0.34 * on_ball_pressure_signal
                + 0.28 * handle_signal
                + 0.22 * game_burst_signal
                + 0.16 * remap(tracking_drives_pg, 8.0, 20.0, 0.0, 100.0),
                0.0,
                100.0,
            )
            creator_forward_speed_floor = attr_clamp(
                remap(creator_forward_mobility_signal, 30.0, 90.0, 70.0, 86.0)
            )
            creator_forward_agility_floor = attr_clamp(
                remap(creator_forward_mobility_signal, 30.0, 90.0, 74.0, 88.0)
            )
            final_attributes["Speed"] = max(
                final_attributes["Speed"], creator_forward_speed_floor
            )
            final_attributes["Agility"] = max(
                final_attributes["Agility"], creator_forward_agility_floor
            )
            final_attributes["Speed with Ball"] = max(
                final_attributes["Speed with Ball"],
                attr_clamp(clamp(creator_forward_speed_floor + 6.0, 72.0, 86.0)),
            )

        # Explosive forwards who combine high dunks_share + frequent drives are faster
        # than tracking avg_speed suggests (they conserve energy, then burst).
        if (
            dunks_share >= 0.18
            and tracking_drives_pg >= 9.0
            and game_burst_signal >= 60.0
            and mpg >= 22.0
        ):
            _elite_explosive_fwd_speed = attr_clamp(
                remap(game_burst_signal, 60.0, 90.0, 83.0, 90.0)
            )
            final_attributes["Speed"] = max(
                final_attributes["Speed"], _elite_explosive_fwd_speed
            )
            final_attributes["Agility"] = max(
                final_attributes["Agility"],
                attr_clamp(_elite_explosive_fwd_speed + 2.0),
            )

    # Athletic centers: burst-speed floor based on drives, dunks, transition.
    if is_center and mpg >= 20.0:
        center_burst_floor = remap(game_burst_signal, 20.0, 80.0, 52.0, 78.0)
        center_agi_burst_floor = remap(game_burst_signal, 20.0, 80.0, 48.0, 76.0)
        final_attributes["Speed"] = max(
            final_attributes["Speed"], attr_clamp(center_burst_floor)
        )
        final_attributes["Agility"] = max(
            final_attributes["Agility"], attr_clamp(center_agi_burst_floor)
        )
        # Elite athletic centers who drive heavily (Giannis archetype)
        if tracking_drives_pg >= 10.0 and usg >= 28.0 and dunks_share >= 0.15:
            center_creator_burst = remap(game_burst_signal, 30.0, 85.0, 72.0, 86.0)
            center_creator_agi = remap(game_burst_signal, 30.0, 85.0, 68.0, 82.0)
            final_attributes["Speed"] = max(
                final_attributes["Speed"], attr_clamp(center_creator_burst)
            )
            final_attributes["Agility"] = max(
                final_attributes["Agility"], attr_clamp(center_creator_agi)
            )
            final_attributes["Speed with Ball"] = max(
                final_attributes["Speed with Ball"],
                attr_clamp(center_creator_burst - 4.0),
            )
        # Low-drive centers are rim-position based, not burst athletes: cap their speed.
        elif tracking_drives_pg < 1.5:
            _no_drive_c_cap = attr_clamp(
                58.0 + remap(tracking_avg_speed, 3.80, 4.80, 0.0, 14.0)
            )
            final_attributes["Speed"] = min(final_attributes["Speed"], _no_drive_c_cap)
            final_attributes["Agility"] = min(
                final_attributes["Agility"], _no_drive_c_cap + 2
            )

    # Physical-family guardrails: avoid inflated mobility/hustle for high-load,
    # older creators while keeping truly explosive guards high.
    # Age penalty scales gently — a productive veteran (LeBron at 40) should
    # still reflect that they can move, just not at peak levels.
    age_mobility_penalty = remap(age, 31.0, 40.0, 0.0, 8.0)
    if age_mobility_penalty > 0.0:
        speed_age_cap = 90.0 - age_mobility_penalty
        agility_age_cap = 92.0 - age_mobility_penalty
        if is_guard:
            speed_age_cap -= remap(usg, 20.0, 35.0, 0.0, 1.5)
            agility_age_cap -= remap(usg, 20.0, 35.0, 0.0, 1.5)
        final_attributes["Speed"] = min(
            final_attributes["Speed"], attr_clamp(clamp(speed_age_cap, 70.0, 90.0))
        )
        final_attributes["Agility"] = min(
            final_attributes["Agility"], attr_clamp(clamp(agility_age_cap, 72.0, 92.0))
        )

    if is_guard and usg >= 28.0:
        guard_mobility_cap_signal = clamp(
            0.50 * athletic_signal
            + 0.20 * creation_2_score
            + 0.18 * p_age_youth
            + 0.12 * p_mpg,
            0.0,
            100.0,
        )
        guard_speed_cap = remap(guard_mobility_cap_signal, 20.0, 88.0, 68.0, 88.0)
        if age >= 30.0:
            guard_speed_cap -= remap(age, 30.0, 37.0, 1.0, 7.0)
        guard_agility_cap = guard_speed_cap + 2.0
        final_attributes["Speed"] = min(
            final_attributes["Speed"], attr_clamp(clamp(guard_speed_cap, 68.0, 88.0))
        )
        final_attributes["Agility"] = min(
            final_attributes["Agility"],
            attr_clamp(clamp(guard_agility_cap, 70.0, 90.0)),
        )

        # High-usage guard hustle should not sit in elite wing/energy-big tiers
        # unless disruption profile is truly elite.
        if stl_pct < 2.8:
            guard_hustle_cap = remap(stl_pct, 1.0, 2.8, 64.0, 82.0)
            guard_hustle_cap += remap(drb_pct, 7.0, 18.0, 0.0, 4.0)
            guard_hustle_cap += remap(hustle_deflections_pg, 0.6, 3.8, 0.0, 3.0)
            final_attributes["Hustle"] = min(
                final_attributes["Hustle"],
                attr_clamp(clamp(guard_hustle_cap, 64.0, 84.0)),
            )

    # Elite tracked speed guards should be either true on-ball burners
    # or extreme off-ball speed runners, not just high movement volume.
    if is_guard and age <= 30.5:
        guard_movement_baseline = attr_clamp(
            60.0
            + 0.30 * remap(tracking_avg_speed_off, 4.20, 5.10, 0.0, 100.0)
            + 0.20 * remap(tracking_avg_speed, 4.00, 4.80, 0.0, 100.0)
        )
        final_attributes["Speed"] = max(
            final_attributes["Speed"], min(86, guard_movement_baseline)
        )
        final_attributes["Agility"] = max(
            final_attributes["Agility"], min(88, guard_movement_baseline + 2)
        )

        on_ball_burner = tracking_drives_pg >= 10.0 and (
            (tracking_time_of_poss_pg >= 3.4 and tracking_avg_drib_per_touch >= 3.0)
            or tracking_drives_pg >= 13.0
        )
        extreme_off_ball_runner = (
            tracking_avg_speed_off >= 5.00
            and tracking_avg_speed >= 4.55
            and tracking_dist_miles_pg >= 2.05
            and mpg >= 20.0
        )

        elite_tracked_guard = (
            tracking_avg_speed_off >= 4.62
            and tracking_avg_speed >= 4.24
            and tracking_dist_miles_pg >= 1.80
            and (on_ball_burner or extreme_off_ball_runner)
        )
        if elite_tracked_guard:
            elite_speed_guard_signal = clamp(
                0.52 * remap(tracking_avg_speed_off, 4.62, 5.10, 0.0, 100.0)
                + 0.28 * remap(tracking_avg_speed, 4.24, 4.85, 0.0, 100.0)
                + 0.20 * remap(tracking_dist_miles_pg, 1.80, 3.05, 0.0, 100.0),
                0.0,
                100.0,
            )
            if on_ball_burner:
                elite_speed_floor = attr_clamp(
                    remap(elite_speed_guard_signal, 0.0, 100.0, 90.0, 97.0)
                )
                elite_agility_floor = attr_clamp(
                    remap(elite_speed_guard_signal, 0.0, 100.0, 92.0, 98.0)
                )
            else:
                elite_speed_floor = attr_clamp(
                    remap(elite_speed_guard_signal, 0.0, 100.0, 90.0, 94.0)
                )
                elite_agility_floor = attr_clamp(
                    remap(elite_speed_guard_signal, 0.0, 100.0, 91.0, 95.0)
                )
            final_attributes["Speed"] = max(
                final_attributes["Speed"], elite_speed_floor
            )
            final_attributes["Agility"] = max(
                final_attributes["Agility"], elite_agility_floor
            )

        movement_only_guard = (
            tracking_avg_speed_off >= 4.75
            and tracking_avg_speed >= 4.40
            and tracking_dist_miles_pg >= 1.85
            and tracking_drives_pg < 6.5
            and tracking_time_of_poss_pg < 2.3
            and tracking_avg_drib_per_touch < 2.2
        )
        if movement_only_guard and not extreme_off_ball_runner:
            final_attributes["Speed"] = min(final_attributes["Speed"], 89)
            final_attributes["Agility"] = min(final_attributes["Agility"], 90)

        # Limit tiny-sample guards from landing in elite speed tiers.
        if (
            (minutes < 900.0 or mpg < 18.0)
            and not elite_tracked_guard
            and not on_ball_burner
        ):
            low_sample_speed_cap = 80.0 + 0.08 * remap(
                tracking_avg_speed_off, 4.30, 5.10, 0.0, 100.0
            )
            low_sample_agility_cap = low_sample_speed_cap + 2.0
            final_attributes["Speed"] = min(
                final_attributes["Speed"],
                attr_clamp(clamp(low_sample_speed_cap, 80.0, 88.0)),
            )
            final_attributes["Agility"] = min(
                final_attributes["Agility"],
                attr_clamp(clamp(low_sample_agility_cap, 82.0, 90.0)),
            )

    # Tall guards (6'5"+) cover ground via stride length, not true quickness:
    # apply a graduated speed/agility ceiling that scales with height above 76".
    if is_guard and height_in >= 77.0:
        _guard_ht_spd_cap = clamp(94.0 - (height_in - 76.0) * 3.5, 72.0, 94.0)
        final_attributes["Speed"] = min(
            final_attributes["Speed"], attr_clamp(_guard_ht_spd_cap)
        )
        final_attributes["Agility"] = min(
            final_attributes["Agility"], attr_clamp(_guard_ht_spd_cap + 2.0)
        )

    final_attributes["Speed with Ball"] = min(
        final_attributes["Speed with Ball"], final_attributes["Speed"] + 8
    )
    if is_guard_like:
        guard_block_cap = 44 + int(round(0.08 * p_blk))
        if height_in >= 77.5:
            guard_block_cap += 3
        if (stl_pct + blk_pct) >= 3.8:
            guard_block_cap += 2
        if is_sf:
            guard_block_cap += 4  # SFs can block a bit more than pure guards
        final_attributes["Block"] = min(
            final_attributes["Block"], int(clamp(guard_block_cap, 44, 64))
        )
    elif is_forward:
        final_attributes["Block"] = min(final_attributes["Block"], 82)

    # Apply role boosts last — after all recalibration passes — so nothing overwrites them.
    final_attributes = apply_role_modifiers(final_attributes, roles, role_catalog)

    for name in ATTRIBUTE_ORDER:
        final_attributes[name] = int(
            clamp(final_attributes[name], ATTRIBUTE_MIN, ATTRIBUTE_MAX)
        )

    family_scores = compute_attribute_family_averages(final_attributes)
    ovr = compute_overall_rating(
        row.get("position", ""),
        final_attributes,
        family_scores,
        usg=float(row.get("advanced_usg_percent", 0) or 0),
    )

    # Apply committee correction for 2025-26 season
    final_attributes = _apply_committee_correction(
        final_attributes,
        str(row.get("player_name", "")),
        str(row.get("season_label", "")),
    )
    # Recompute OVR after correction
    family_scores = compute_attribute_family_averages(final_attributes)
    ovr = compute_overall_rating(
        row.get("position", ""),
        final_attributes,
        family_scores,
        usg=float(row.get("advanced_usg_percent", 0) or 0),
    )

    badge_groups: Dict[str, List[Dict[str, Any]]] = {}
    if badges_txt_path and os.path.exists(badges_txt_path):
        badge_groups = compute_badge_groups(
            row,
            final_attributes,
            tendencies,
            family_scores,
            ovr,
            badges_txt_path,
        )

    return {
        "attributes": final_attributes,
        "roles": roles,
        "badges": badge_groups,
        "family_scores": family_scores,
        "ovr": ovr,
        "role_catalog_sections": len(role_catalog),
        "definition_count": len(attr_definitions),
        "attribute_blend": "60% season + 40% career",
    }


def print_attribute_report(
    row: Dict[str, Any], attribute_bundle: Dict[str, Any]
) -> None:
    attrs: Dict[str, int] = attribute_bundle["attributes"]
    roles: List[str] = attribute_bundle["roles"]
    badge_groups: Dict[str, List[Dict[str, Any]]] = attribute_bundle.get("badges", {})
    family_scores = attribute_bundle.get(
        "family_scores", compute_attribute_family_averages(attrs)
    )
    print("=" * 92)
    print("NBA 2K26 Generator - Attributes Report")
    print("=" * 92)
    print(
        f"Player: {repair_mojibake_text(row.get('player_name'))} | Season: {row.get('season_label')} | Team: {row.get('team_abbr')} | Source: {row.get('__source_file')}"
    )
    print(f"Roles: {', '.join(roles)}")
    print(f"Range Guardrail: {ATTRIBUTE_MIN}-{ATTRIBUTE_MAX}")
    print("-" * 92)
    print("Attribute Families (Averages)")
    for family_name in [
        "Finishing",
        "Shooting",
        "Playmaking",
        "Defense",
        "Physical",
        "Intangibles",
    ]:
        if family_name in family_scores:
            print(f"{family_name:<24} {family_scores[family_name]:>3}")
    print("-" * 92)
    print("Attributes")
    for name in ATTRIBUTE_ORDER:
        print(f"{name:<24} {attrs[name]:>3}")

    # ── Badges ────────────────────────────────────────────────────────────
    total_badges = sum(len(v) for v in badge_groups.values())
    if total_badges > 0:
        print("-" * 92)
        tier_counts: Dict[str, int] = {}
        for section_badges in badge_groups.values():
            for b in section_badges:
                tier_counts[b["value"]] = tier_counts.get(b["value"], 0) + 1
        tier_summary = ", ".join(
            f"{tier_counts.get(t, 0)} {t}"
            for t in BADGE_TIER_ORDER
            if tier_counts.get(t, 0) > 0
        )
        print(f"Badges ({total_badges} total: {tier_summary})")
        for section_name in [
            "Finishing",
            "Shooting",
            "Playmaking",
            "Defense",
            "Post",
            "Off-Ball",
        ]:
            section_list = badge_groups.get(section_name, [])
            if not section_list:
                continue
            print(f"  {section_name}:")
            for b in section_list:
                print(f"    {b['name']:<24} {b['value']:<8} ({b['score']:.0f})")


def print_report(row: Dict[str, Any], results: List[TendencyResult]) -> None:
    print("=" * 92)
    print("NBA 2K26 Generator - Milestone 1 Report")
    print("=" * 92)
    print(
        f"Player: {repair_mojibake_text(row.get('player_name'))} | Season: {row.get('season_label')} | Team: {row.get('team_abbr')} | Source: {row.get('__source_file')}"
    )
    print(
        f"Position: {row.get('position')} | Age: {row.get('age')} | Minutes: {row.get('totals_mp')}"
    )
    print("-" * 92)

    for result in results:
        norm_low, norm_high = result.norm_range
        print(
            f"{result.name:<20} pre_cap={result.pre_cap:>5} | final={result.final:>3} "
            f"| norm={norm_low}-{norm_high} | rec_cap={result.recommended_cap} | abs_cap={result.absolute_cap}"
        )
        evidence_pairs = ", ".join([f"{k}={v}" for k, v in result.evidence.items()])
        print(f"  evidence: {evidence_pairs}")

    print("-" * 92)
    print("Legend: pre_cap = raw formula output before cap logic")
    print("        final   = min(pre_cap, recommended_cap, absolute_cap)")


# ── JSON Profile Helpers ──────────────────────────────────────────────────

def normalize_key(name):
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")

def _sf(v, default=0.0):
    try:
        f = float(str(v or "").strip())
        return f if f == f else default
    except Exception:
        return default

def _as_float(v, default=0.0):
    return _sf(v, default)

def _first_non_empty(*values):
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() not in {"none", "nan", "na", "n/a"}:
            return s
    return ""

def _format_height(row):
    explicit = _first_non_empty(row.get("height"), row.get("height_without_shoes"))
    if explicit:
        return explicit
    inches_raw = _first_non_empty(row.get("player_info_ht_in_in"))
    if not inches_raw:
        return "NA"
    total = int(_sf(inches_raw, 0.0))
    if total <= 0:
        return "NA"
    feet = total // 12
    inches = total % 12
    return f"{feet}'{inches}\""

def _build_headshot_url(row):
    nba_id = _first_non_empty(row.get("player_id"))
    if nba_id and str(nba_id).strip().isdigit():
        return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{str(nba_id).strip()}.png"
    espn_id = _first_non_empty(row.get("espn_id"), row.get("espn_player_id"))
    if espn_id and str(espn_id).isdigit():
        return f"https://a.espncdn.com/i/headshots/nba/players/full/{espn_id}.png"
    return ""

def _build_team_logo_url(row):
    tid = _first_non_empty(row.get("team_id"))
    if tid and str(tid).strip().isdigit():
        return f"https://cdn.nba.com/logos/nba/{str(tid).strip()}/primary/L/logo.svg"
    return ""

def _format_draft(row):
    draft_year = _first_non_empty(row.get("draft_year"), row.get("draft_season"))
    draft_round = _first_non_empty(row.get("draft_round"), "")
    draft_pick = _first_non_empty(row.get("draft_number"), "")
    if draft_year and str(draft_year).strip().lower() not in ("undrafted", "", "none", "nan"):
        result = str(draft_year).strip()
        if draft_round:
            result += f" R{draft_round}"
        if draft_pick:
            result += f" Pick {draft_pick}"
        return result
    return "Undrafted" if str(draft_year).strip().lower() == "undrafted" else "NA"

def _season_year(label):
    m = re.match(r"^(\d{4})", str(label or "").strip())
    return int(m.group(1)) if m else -1

def _find_previous_season_row(row, all_rows):
    season_label = str(row.get("season_label", "")).strip()
    player_name = str(row.get("player_name", "")).strip().lower()
    current_year = _season_year(season_label)
    if current_year <= 0:
        return None
    for r in all_rows:
        if str(r.get("player_name", "")).strip().lower() == player_name:
            if _season_year(r.get("season_label", "")) == current_year - 1:
                return r
    return None

def _compute_career_snapshot(row, all_rows):
    player_name = str(row.get("player_name", "")).strip().lower()
    current_year = _season_year(row.get("season_label", ""))
    career_total_g = 0.0
    career_acc = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "stl": 0.0, "blk": 0.0, "fgPct": 0.0, "fg3Pct": 0.0}
    if all_rows:
        for r in all_rows:
            if str(r.get("player_name", "")).strip().lower() == player_name:
                if _season_year(r.get("season_label", "")) <= current_year:
                    s = stat_snapshot(r)
                    g = max(float(s.get("gp", 0)), 1.0)
                    career_total_g += g
                    for k in career_acc:
                        career_acc[k] += float(s.get(k, 0.0)) * g
    if career_total_g > 0:
        return {k: round((career_acc[k] / career_total_g), 3 if "Pct" in k else 1) for k in career_acc}
    return {"pts": 0.0, "reb": 0.0, "ast": 0.0, "stl": 0.0, "blk": 0.0, "fgPct": 0.0, "fg3Pct": 0.0, "gp": 0}

def stat_snapshot(r):
    if not r:
        return {"pts": 0.0, "reb": 0.0, "ast": 0.0, "stl": 0.0, "blk": 0.0, "fgPct": 0.0, "fg3Pct": 0.0, "gp": 0}
    g = max(_sf(r.get("per_game_g", r.get("advanced_g", r.get("totals_g", 0.0)))), 1.0)
    pts = _sf(r.get("per_game_pts_per_game", r.get("per_game_pts", _sf(r.get("totals_pts", 0.0)) / g)))
    reb = _sf(r.get("per_game_reb_per_game", r.get("per_game_trb", _sf(r.get("totals_trb", 0.0)) / g)))
    ast = _sf(r.get("per_game_ast_per_game", r.get("per_game_ast", _sf(r.get("totals_ast", 0.0)) / g)))
    stl = _sf(r.get("per_game_stl_per_game", r.get("per_game_stl", _sf(r.get("totals_stl", 0.0)) / g)))
    blk = _sf(r.get("per_game_blk_per_game", r.get("per_game_blk", _sf(r.get("totals_blk", 0.0)) / g)))
    fg_raw = _first_non_empty(
        r.get("per_game_fg_percent"), r.get("per_game_fg_pct"), r.get("shooting_fg_percent"),
        r.get("shooting_fg_pct"), r.get("totals_fg_percent"), r.get("totals_fg_pct"),
        r.get("fg_percent"), r.get("fg_pct"),
    )
    fg = _sf(fg_raw, None) if fg_raw else None
    if fg is None:
        fgm = _sf(r.get("totals_fg", 0.0))
        fga = max(_sf(r.get("totals_fga", 0.0)), 1.0)
        fg = fgm / fga
    fg3_raw = _first_non_empty(
        r.get("per_game_x3p_percent"), r.get("per_game_fg3_pct"), r.get("shooting_fg_percent_from_x3p_range"),
        r.get("shooting_fg3_pct"), r.get("totals_x3p_percent"), r.get("totals_fg3_pct"),
        r.get("fg3_percent"), r.get("fg3_pct"),
    )
    fg3 = _sf(fg3_raw, None) if fg3_raw else None
    if fg3 is None:
        fg3m = _sf(r.get("totals_fg3", 0.0))
        fg3a = max(_sf(r.get("totals_fg3a", 0.0)), 1.0)
        fg3 = fg3m / fg3a
    return {
        "pts": round(pts, 1), "reb": round(reb, 1), "ast": round(ast, 1),
        "stl": round(stl, 1), "blk": round(blk, 1),
        "fgPct": round(fg, 3), "fg3Pct": round(fg3, 3),
        "gp": int(_sf(r.get("per_game_g", r.get("advanced_g", r.get("totals_g", 0.0))))),
    }

def _build_attribute_groups(attrs):
    order = [
        ("Finishing", ["Driving Layup", "Standing Dunk", "Driving Dunk", "Close Shot"]),
        ("Shooting", ["Mid-Range Shot", "Three-Point Shot", "Free Throw", "Shot IQ"]),
        ("Post Game", ["Post Hook", "Post Fade", "Post Control"]),
        ("Playmaking", ["Draw Foul", "Ball Handle", "Speed with Ball", "Hands", "Pass Accuracy", "Pass IQ", "Pass Vision"]),
        ("Mental", ["Offensive Consistency", "Defensive Consistency"]),
        ("Defense", ["Interior Defense", "Perimeter Defense", "Steal", "Block", "Help Defense IQ", "Pass Perception"]),
        ("Rebounding", ["Offensive Rebound", "Defensive Rebound"]),
        ("Physical", ["Speed", "Agility", "Strength", "Vertical", "Stamina"]),
        ("Meta", ["Intangibles", "Hustle", "Overall Durability", "Potential"]),
    ]
    groups = {}
    for family_name, names in order:
        groups[family_name] = [
            {"key": normalize_key(n), "name": n, "value": int(attrs.get(n, 0))}
            for n in names if n in attrs
        ]
    return groups

TENDENCY_ALIASES = {
    "step_through_shot": ["step_through"], "shot_under_basket": ["shot_under"],
    "touches": ["touch"], "shot_mid_range": ["shot_mid"], "shot_three": ["shot_3"],
    "spot_up_shot_mid_range": ["spot_up_mid", "spot_up_shot_mid"], "spot_up_shot_three": ["spot_up_3"],
    "off_screen_shot_mid_range": ["off_screen_mid", "off_screen_shot_mid"], "off_screen_shot_three": ["off_screen_3"],
    "contested_jumper_mid_range": ["contested_mid"], "contested_jumper_three": ["contested_3"],
    "stepback_jumper_mid_range": ["step_back_mid"], "stepback_jumper_three": ["step_back_3"],
    "drive_pull_up_mid_range": ["dribble_pull_up_mid", "drive_pull_up_mid"],
    "drive_pull_up_three": ["dribble_pull_up_3", "drive_pull_up_3"],
    "driving_layup": ["drive"], "hop_step_layup": ["hop_step"], "euro_step_layup": ["eurostep"],
    "transition_pull_up_three": ["transition_pull_up_3"], "transition_spot_up": ["spot_vs_cut"],
    "driving_crossover": ["drive_crossover"], "driving_spin": ["drive_spin"],
    "driving_step_back": ["drive_step_back"], "driving_half_spin": ["drive_half_spin"],
    "driving_double_crossover": ["drive_double_crossover"], "driving_behind_the_back": ["drive_behind_back"],
    # Dribble setup name mismatches
    "setup_with_sizeup": ["set_up_size_up"], "setup_with_hesitation": ["set_up_hesitation"],
    # Dribble moves name mismatches
    "driving_dribble_hesitation": ["drive_hesitation"], "driving_in_and_out": ["drive_in_out"],
    "no_driving_dribble_move": ["no_drive_dribble_move"],
    # Driving name mismatches
    "attack_strong_on_drive": ["attack_strong_drive"],
    # Passing name mismatches
    "dish_to_open_man": ["dish"],
    # Isolation name mismatches
    "iso_vs_elite_defender": ["iso_vs_elite"], "iso_vs_good_defender": ["iso_vs_good"],
    "iso_vs_average_defender": ["iso_vs_average"], "iso_vs_poor_defender": ["iso_vs_poor"],
    # Post name mismatches
    "post_aggressive_backdown": ["post_aggressive_back_down"],
    "post_shimmy_shot": ["post_shimmy"], "post_step_back_shot": ["post_step_back"],
    "post_up_and_under": ["post_up_under"], "post_hop_step": ["post_hop_shot"],
    # Defense name mismatches
    "block_shot": ["block"],
}

TENDENCY_GROUP_ORDER = [
    ("finishing", ["Step Through Shot", "Shot Under Basket", "Shot Close", "Use Glass", "Driving Layup", "Standing Dunk",
                   "Driving Dunk", "Flashy Dunk", "Alley-Oop", "Putback", "Crash", "Spin Layup", "Hop Step Layup",
                   "Euro Step Layup", "Floater"]),
    ("sub_zone", ["Shot Close Left", "Shot Close Middle", "Shot Close Right", "Shot Mid Left", "Shot Mid Left-Center",
                  "Shot Mid Center", "Shot Mid Right-Center", "Shot Mid Right", "Shot Three Left",
                  "Shot Three Left-Center", "Shot Three Center", "Shot Three Right-Center", "Shot Three Right"]),
    ("shooting", ["Shot Mid-Range", "Spot Up Shot Mid-Range", "Off Screen Shot Mid-Range", "Shot Three",
                  "Spot Up Shot Three", "Off Screen Shot Three", "Contested Jumper Three", "Contested Jumper Mid-Range",
                  "Stepback Jumper Three", "Stepback Jumper Mid-Range", "Spin Jumper", "Transition Pull Up Three",
                  "Drive Pull Up Three", "Drive Pull Up Mid-Range"]),
    ("triple_threat", ["Triple Threat Pump Fake", "Triple Threat Jab Step", "Triple Threat Idle", "Triple Threat Shoot"]),
    ("dribble_setup", ["Setup With Sizeup", "Setup With Hesitation", "No Setup Dribble"]),
    ("driving", ["Drive", "Spot Up Drive", "Off Screen Drive", "Drive Right", "Attack Strong On Drive"]),
    ("dribble_moves", ["Driving Crossover", "Driving Spin", "Driving Step Back", "Driving Half Spin",
                       "Driving Double Crossover", "Driving Behind The Back", "Driving Dribble Hesitation",
                       "Driving In And Out", "No Driving Dribble Move"]),
    ("passing", ["Dish To Open Man", "Flashy Pass", "Alley-Oop Pass"]),
    ("post", ["Post Up", "Post Shimmy Shot", "Post Face Up", "Post Back Down", "Post Aggressive Backdown",
              "Shoot From Post", "Post Hook Left", "Post Hook Right", "Post Fade Left", "Post Fade Right",
              "Post Up And Under", "Post Hop Shot", "Post Step Back Shot", "Post Drive", "Post Spin",
              "Post Drop Step", "Post Hop Step"]),
    ("core", ["Shot", "Touches", "Play Discipline"]),
    ("playstyle", ["Roll vs. Pop", "Transition Spot Up"]),
    ("isolation", ["Iso vs. Elite Defender", "Iso vs. Good Defender", "Iso vs. Average Defender", "Iso vs. Poor Defender"]),
    ("defense", ["Pass Interception", "Take Charge", "On-Ball Steal", "Contest Shot", "Block Shot"]),
    ("physical", ["Foul", "Hard Foul"]),
]

def _build_tendency_groups(tendency_results):
    tendency_by_name = {t.name: t for t in tendency_results}
    tendency_by_norm = {normalize_key(t.name): t for t in tendency_results}

    def resolve_tendency(name):
        t = tendency_by_name.get(name)
        if t:
            return t
        norm = normalize_key(name)
        t = tendency_by_norm.get(norm)
        if t:
            return t
        for alias in TENDENCY_ALIASES.get(norm, []):
            t = tendency_by_norm.get(alias)
            if t:
                return t
        return None

    groups = {}
    for group_name, names in TENDENCY_GROUP_ORDER:
        grp_rows = []
        for n in names:
            t = resolve_tendency(n)
            grp_rows.append({
                "key": normalize_key(n),
                "name": n,
                "value": int(t.final) if t else 0,
                "preCap": float(t.pre_cap) if t else 0.0,
                "recommendedCap": int(t.recommended_cap) if t else 0,
                "absoluteCap": int(t.absolute_cap) if t else 0,
            })
        groups[group_name] = grp_rows
    return groups


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NBA 2K26 Generator CLI (Milestone 1)")
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--player", help="Exact player name, e.g. 'Giannis Antetokounmpo'"
    )
    target_group.add_argument("--team", help="Team abbreviation, e.g. 'LAL'")
    parser.add_argument("--season", required=True, help="Season label, e.g. '2025-26'")
    parser.add_argument(
        "--mode",
        choices=["tendencies", "attributes", "both"],
        default="both",
        help="Output mode (default: both)",
    )
    parser.add_argument(
        "--database-dir",
        default=os.path.join(os.getcwd(), "NBA Site data"),
        help="Path to NBA Site CSV directory (default: ./NBA Site data)",
    )
    parser.add_argument(
        "--player-roles-dir",
        default=os.path.join(os.getcwd(), "Player Roles"),
        help="Path to Player Roles directory (default: ./Player Roles)",
    )
    parser.add_argument(
        "--badges-txt",
        default=os.path.join(os.getcwd(), "Badges", "NBA 2K26 Badges.txt"),
        help="Path to badges definition file (default: ./Badges/NBA 2K26 Badges.txt)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output full JSON profile (for Electron app integration)",
    )
    return parser


def main() -> None:
    configure_output_streams()
    args = build_arg_parser().parse_args()

    rows = load_rows(args.database_dir)

    def run_for_row(row: Dict[str, Any]) -> None:
        # For 2025-26 rows, use 2024-25 data for tendencies.
        # If the row is already a 2024-25 fallback (injured player), use it as-is.
        # Rookies with no prior data keep their 2025-26 row for tendencies.
        tendency_row = row
        season_start = parse_season_start_year(args.season)
        row_year = _season_year(row.get("season_label", ""))
        if season_start == 2025 and row_year == 2025:
            prev_row = _find_previous_season_row(row, rows)
            if prev_row is not None:
                tendency_row = prev_row

        tendencies: List[TendencyResult] = compute_tendencies(tendency_row)
        if args.json:
            attribute_bundle = _compute_attributes_with_ml(
                row, tendencies, args.player_roles_dir, rows, args.badges_txt,
            )
            print(json.dumps({"ok": True, "player": row.get("player_name", ""), "profile": attribute_bundle}))
        else:
            if args.mode in {"tendencies", "both"}:
                print_report(row, tendencies)
            if args.mode in {"attributes", "both"}:
                if args.mode == "both":
                    print()
                attribute_bundle = compute_attributes(
                    row,
                    tendencies,
                    args.player_roles_dir,
                    rows,
                    badges_txt_path=args.badges_txt,
                )
                print_attribute_report(row, attribute_bundle)

    if args.player:
        row = select_player_season_row(rows, args.player, args.season)
        run_for_row(row)
        return

    team_rows = select_team_season_rows(rows, args.team, args.season)
    clear_team_generation_caches()
    print("=" * 92)
    print(
        f"Team Generation | Team: {str(args.team).upper()} | Season: {args.season} | Players: {len(team_rows)}"
    )
    print("=" * 92)
    for i, row in enumerate(team_rows):
        if i > 0:
            print("\n" + ("#" * 92) + "\n")
        run_for_row(row)


def _compute_attributes_with_ml(
    row: Dict[str, Any],
    tendencies: List[TendencyResult],
    player_roles_dir: str,
    all_rows: Optional[List[Dict[str, Any]]] = None,
    badges_txt_path: str = "",
) -> Dict[str, Any]:
    """Compute full JSON profile using ML attributes from generator_cli_ml.py."""
    if _compute_attributes_ml is not None:
        ml_result = _compute_attributes_ml(row, tendencies, player_roles_dir, all_rows, badges_txt_path)
    else:
        ml_result = compute_attributes(row, tendencies, player_roles_dir, all_rows, badges_txt_path)

    attrs = ml_result.get("attributes", {})
    roles = ml_result.get("roles", [])
    ovr = ml_result.get("ovr", 75)

    # Compute family scores
    family_scores = compute_attribute_family_averages(attrs)
    family_scores = {k: int(v) for k, v in family_scores.items()}

    # Compute tendencies
    tendency_results = tendencies

    # Compute badges
    badge_groups = compute_badge_groups(row, attrs, tendency_results, family_scores, ovr, badges_txt_path)

    # Stats
    current_snapshot = stat_snapshot(row)
    prev_row = _find_previous_season_row(row, all_rows) if all_rows else None
    previous_snapshot = stat_snapshot(prev_row) if prev_row else {}

    career_snapshot = _compute_career_snapshot(row, all_rows)

    # Strengths/weaknesses
    sorted_attrs = sorted(attrs.items(), key=lambda kv: kv[1], reverse=True)
    strengths = [k for k, _ in sorted_attrs[:6]]
    weaknesses = [k for k, _ in sorted(attrs.items(), key=lambda kv: kv[1])[:6]]

    # Attribute groups
    attribute_groups = _build_attribute_groups(attrs)

    # Tendency groups
    tendency_groups = _build_tendency_groups(tendency_results)

    # Info
    info = {
        "name": repair_mojibake_text(row.get("player_name", "")),
        "team": str(row.get("team_abbr", "")),
        "position": str(row.get("position", row.get("pos", ""))),
        "season": str(row.get("season_label", "")),
        "age": float(row.get("age", 0) or 0),
        "height": _format_height(row),
        "weight": _first_non_empty(row.get("weight"), row.get("weight_lbs"), row.get("player_info_wt")) or "NA",
        "yearsPro": int(_as_float(row.get("experience", 0))),
        "draft": _format_draft(row),
        "school": _first_non_empty(row.get("college"), row.get("school"), row.get("draft_college"), row.get("player_info_colleges")) or "NA",
        "country": _first_non_empty(row.get("country"), "") or "",
        "photoUrl": _build_headshot_url(row),
        "teamLogoUrl": _build_team_logo_url(row),
        "actionPhotoUrl": "",
        "nbaPlayerId": str(row.get("player_id", "")).strip(),
    }

    return {
        "info": info,
        "ovr": ovr,
        "role": roles[0] if roles else "Core",
        "archetype": roles[0] if roles else "Core",
        "archetypes": roles,
        "usage": roles,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "familyScores": family_scores,
        "attributes": {normalize_key(k): int(v) for k, v in attrs.items()},
        "attributeGroups": attribute_groups,
        "tendencyGroups": tendency_groups,
        "badgeGroups": badge_groups,
        "playStylePriorities": [t.name for t in sorted(tendency_results, key=lambda x: x.final, reverse=True)[:3]],
        "statBlocks": {"current": current_snapshot, "previous": previous_snapshot, "career": career_snapshot},
    }


if __name__ == "__main__":
    main()
