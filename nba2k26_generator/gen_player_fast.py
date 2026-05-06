"""Fast player profile generator - formula-based attributes, no pandas/sklearn.

Reads CSVs via nba_site_normalization (pure csv module),
computes attributes using statistical formulas, tendencies, and badges.

Usage:
    python gen_player_fast.py "LeBron James" "2024-25" <project_root> <db_dir> <roles_dir>

Outputs JSON to stdout.
"""
import csv
import json
import math
import os
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

# ── Arguments (set at module level for CLI, overridden by main()) ──────────
player_name_arg = sys.argv[1].strip() if len(sys.argv) > 1 else ""
season_arg = sys.argv[2].strip() if len(sys.argv) > 2 else ""
project_root = sys.argv[3] if len(sys.argv) > 3 else ""
db_dir = sys.argv[4] if len(sys.argv) > 4 else ""
roles_dir = sys.argv[5] if len(sys.argv) > 5 else ""
badges_txt = os.path.join(project_root, "Badges", "NBA 2K26 Badges.txt") if project_root else ""

# ── Helpers ────────────────────────────────────────────────────────────────
def sf(v, default=0.0):
    try:
        f = float(str(v or "").strip())
        return f if f == f else default
    except Exception:
        return default

def normalize_key(name):
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")

def season_year(label):
    m = re.match(r"^(\d{4})", str(label or "").strip())
    return int(m.group(1)) if m else -1

def first_non_empty(*values):
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() not in {"none", "nan", "na", "n/a"}:
            return s
    return ""

def repair_text(value):
    text = str(value or "")
    if not text:
        return ""
    def likely_mojibake(s):
        hints = ("\u00c3", "\u00c2", "\u00e2", "\u00c4", "\u00c5", "\u00d0", "\u00f0", "\u2021")
        return any(h in s for h in hints) or any(0x80 <= ord(ch) <= 0x9F for ch in s)
    def to_bytes(s):
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
        if not likely_mojibake(fixed):
            break
        raw = to_bytes(fixed)
        if not raw:
            break
        try:
            decoded = raw.decode("utf-8")
        except Exception:
            break
        if not decoded or decoded == fixed:
            break
        fixed = decoded
    return fixed or text

def normalize_name(name):
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()

def clamp(value, low, high):
    return max(low, min(high, value))

def remap(value, old_min, old_max, new_min, new_max):
    if old_max <= old_min:
        return new_min
    v = clamp(value, old_min, old_max)
    proportion = (v - old_min) / (old_max - old_min)
    return new_min + proportion * (new_max - new_min)

def format_height(row):
    explicit = first_non_empty(row.get("height"), row.get("height_without_shoes"))
    if explicit:
        return explicit
    inches_raw = first_non_empty(row.get("player_info_ht_in_in"))
    if not inches_raw:
        return "NA"
    total = int(sf(inches_raw, 0.0))
    if total <= 0:
        return "NA"
    feet = total // 12
    inches = total % 12
    return f"{feet}'{inches}\""

def build_headshot_url(row):
    nba_id = first_non_empty(row.get("player_id"))
    if nba_id and str(nba_id).strip().isdigit():
        return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{str(nba_id).strip()}.png"
    espn_id = first_non_empty(row.get("espn_id"), row.get("espn_player_id"), row.get("player_info_espn_id"))
    if espn_id and str(espn_id).isdigit():
        return f"https://a.espncdn.com/i/headshots/nba/players/full/{espn_id}.png"
    return ""

def build_team_logo_url(row):
    tid = first_non_empty(row.get("team_id"))
    if tid and str(tid).strip().isdigit():
        return f"https://cdn.nba.com/logos/nba/{str(tid).strip()}/primary/L/logo.svg"
    return ""

def find_action_photo(row, project_root):
    name = repair_text(row.get("player_name", "")).strip()
    if not name:
        return ""
    photos_dir = os.path.join(project_root, "Player Photos")
    if not os.path.isdir(photos_dir):
        return ""
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = os.path.join(photos_dir, name + ext)
        if os.path.isfile(candidate):
            return candidate
    def strip_accents(s):
        nfkd = unicodedata.normalize("NFKD", s)
        return "".join(c for c in nfkd if not unicodedata.combining(c))
    name_lower = strip_accents(name).lower()
    try:
        for f in os.listdir(photos_dir):
            stem, ext = os.path.splitext(f)
            if ext.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                if strip_accents(stem).lower() == name_lower:
                    return os.path.join(photos_dir, f)
    except Exception:
        pass
    return ""

def stat_snapshot(r):
    if not r:
        return {"pts": 0.0, "reb": 0.0, "ast": 0.0, "stl": 0.0, "blk": 0.0, "fgPct": 0.0, "fg3Pct": 0.0, "gp": 0}
    g = max(sf(r.get("per_game_g", r.get("advanced_g", r.get("totals_g", 0.0)))), 1.0)
    pts = sf(r.get("per_game_pts_per_game", r.get("per_game_pts", sf(r.get("totals_pts", 0.0)) / g)))
    reb = sf(r.get("per_game_reb_per_game", r.get("per_game_trb", sf(r.get("totals_trb", 0.0)) / g)))
    ast = sf(r.get("per_game_ast_per_game", r.get("per_game_ast", sf(r.get("totals_ast", 0.0)) / g)))
    stl = sf(r.get("per_game_stl_per_game", r.get("per_game_stl", sf(r.get("totals_stl", 0.0)) / g)))
    blk = sf(r.get("per_game_blk_per_game", r.get("per_game_blk", sf(r.get("totals_blk", 0.0)) / g)))
    fg_raw = first_non_empty(
        r.get("per_game_fg_percent"), r.get("per_game_fg_pct"), r.get("shooting_fg_percent"),
        r.get("shooting_fg_pct"), r.get("totals_fg_percent"), r.get("totals_fg_pct"),
        r.get("fg_percent"), r.get("fg_pct"),
    )
    fg = sf(fg_raw, None) if fg_raw else None
    if fg is None:
        fgm = sf(r.get("totals_fg", 0.0))
        fga = max(sf(r.get("totals_fga", 0.0)), 1.0)
        fg = fgm / fga
    fg3_raw = first_non_empty(
        r.get("per_game_x3p_percent"), r.get("per_game_fg3_pct"), r.get("shooting_fg_percent_from_x3p_range"),
        r.get("shooting_fg3_pct"), r.get("totals_x3p_percent"), r.get("totals_fg3_pct"),
        r.get("fg3_percent"), r.get("fg3_pct"),
    )
    fg3 = sf(fg3_raw, None) if fg3_raw else None
    if fg3 is None:
        fg3m = sf(r.get("totals_fg3", 0.0))
        fg3a = max(sf(r.get("totals_fg3a", 0.0)), 1.0)
        fg3 = fg3m / fg3a
    return {
        "pts": round(pts, 1), "reb": round(reb, 1), "ast": round(ast, 1),
        "stl": round(stl, 1), "blk": round(blk, 1),
        "fgPct": round(fg, 3), "fg3Pct": round(fg3, 3),
        "gp": int(sf(r.get("per_game_g", r.get("advanced_g", r.get("totals_g", 0.0))))),
    }

def preferred_row(rows):
    if not rows:
        return None
    for r in rows:
        if str(r.get("team_abbr", "")).upper() == "2TM":
            return r
    return max(rows, key=lambda r: sf(r.get("totals_mp", 0.0)))

# ── CSV loading (pure csv module, no pandas) ───────────────────────────────
def _read_csv(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def _to_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace('%', '')
    if not s:
        return default
    try:
        value = float(s)
        if math.isnan(value) or math.isinf(value):
            return default
        return value
    except ValueError:
        return default

def _index_by_player_id(rows, pid_col='PLAYER_ID'):
    idx = {}
    for r in rows:
        pid = str(r.get(pid_col, '')).strip()
        if pid:
            idx[pid] = r
    return idx

def _aggregate_rows(rows, group_key='PLAYER_ID'):
    groups = defaultdict(list)
    for r in rows:
        k = str(r.get(group_key, '')).strip()
        if not k:
            continue
        groups[k].append(r)
    out = []
    for key, items in groups.items():
        if len(items) == 1:
            out.append(items[0])
            continue
        cols = set()
        for it in items:
            cols.update(it.keys())
        merged = {}
        for c in cols:
            vals = [(it.get(c) or '').strip() for it in items if (it.get(c) or '').strip()]
            if not vals:
                merged[c] = ''
                continue
            try:
                nums = [_to_float(v) for v in vals]
                if all(n > 0 for n in nums):
                    merged[c] = str(sum(nums) / len(nums))
                else:
                    merged[c] = vals[0]
            except:
                merged[c] = vals[0]
        out.append(merged)
    return out

def load_season_rows(season_dir):
    """Load and merge NBA Site CSVs for one season directory."""
    base = Path(season_dir)
    files = sorted(base.glob('*.csv'))
    if not files:
        return []
    
    import re as _re
    season_tag = None
    for f in files:
        m = _re.search(r'player_traditional_(\d{4}-\d{2})_regular_season\.csv', f.name)
        if m:
            season_tag = m.group(1)
            break
    if not season_tag:
        return []
    
    def sf_name(name):
        return name.replace('SEASON', season_tag)
    
    trad_path = base / sf_name('player_traditional_SEASON_regular_season.csv')
    if not trad_path.exists():
        return []
    
    trad_rows = _read_csv(trad_path)
    trad_idx = _index_by_player_id(trad_rows)
    merged = {pid: dict(row) for pid, row in trad_idx.items()}
    
    merge_files = [
        sf_name('player_advanced_SEASON_regular_season.csv'),
        sf_name('player_usage_SEASON_regular_season.csv'),
        sf_name('player_scoring_SEASON_regular_season.csv'),
        sf_name('player_shooting_by_zone_SEASON_regular_season.csv'),
        sf_name('player_tracking_speed_distance_SEASON_regular_season.csv'),
        sf_name('player_tracking_drives_SEASON_regular_season.csv'),
        sf_name('player_tracking_pullup_SEASON_regular_season.csv'),
        sf_name('player_tracking_catch_shoot_SEASON_regular_season.csv'),
        sf_name('player_tracking_passing_SEASON_regular_season.csv'),
        sf_name('player_tracking_touches_SEASON_regular_season.csv'),
        sf_name('player_tracking_tracking_post_ups_SEASON_regular_season.csv'),
        sf_name('player_defense_SEASON_regular_season.csv'),
        sf_name('player_hustle_SEASON_regular_season.csv'),
        sf_name('player_bio_SEASON_regular_season.csv'),
        sf_name('player_playtype_isolation_SEASON_regular_season.csv'),
        sf_name('player_playtype_spot_up_SEASON_regular_season.csv'),
        sf_name('player_tracking_offensive_rebounding_SEASON_regular_season.csv'),
        sf_name('player_tracking_defensive_rebounding_SEASON_regular_season.csv'),
        sf_name('player_box_outs_SEASON_regular_season.csv'),
        sf_name('player_misc_SEASON_regular_season.csv'),
    ]
    
    # Protected keys from traditional CSV that should not be overwritten
    TRADITIONAL_PROTECTED = {
        'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'OREB', 'DREB',
        'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'PF', 'PFD',
        'FG_PCT', 'FG3_PCT', 'FT_PCT', 'MIN', 'GP', 'W', 'L', 'W_PCT',
        'PLUS_MINUS', 'BLKA',
    }
    
    for fname in merge_files:
        fp = base / fname
        if not fp.exists():
            continue
        rows = _read_csv(fp)
        rows = _aggregate_rows(rows)
        idx = _index_by_player_id(rows)
        for pid, target in merged.items():
            src = idx.get(pid)
            if not src:
                continue
            for k, v in src.items():
                if k == 'PLAYER_ID':
                    continue
                # Skip if this key is protected and already exists in traditional data
                if k in TRADITIONAL_PROTECTED and k in target:
                    continue
                # Strip filename prefix: "player_advanced_SEASON_regular_season.csv:usg_pct" -> "usg_pct"
                clean_key = k
                if ':' in k:
                    clean_key = k.split(':', 1)[1]
                # Also strip season tag from key names
                clean_key = clean_key.replace(f'_{season_tag}', '')
                target[clean_key] = v
    
    # Add season_label and normalize keys to lowercase
    out = []
    for row in merged.values():
        row['season_label'] = season_tag
        normalized = {}
        for k, v in row.items():
            nk = k.lower()
            # Map common NBA Site keys to expected names
            key_map = {
                'player_name': 'player_name',
                'team_abbreviation': 'team_abbr',
                'player_id': 'player_id',
                'age': 'age',
                'gp': 'per_game_g',
                'pts': 'per_game_pts_per_game',
                'reb': 'per_game_reb_per_game',
                'ast': 'per_game_ast_per_game',
                'stl': 'per_game_stl_per_game',
                'blk': 'per_game_blk_per_game',
                'fg_pct': 'per_game_fg_percent',
                'fg3_pct': 'per_game_x3p_percent',
                'ft_pct': 'per_game_ft_percent',
                'oreb': 'per_game_oreb_per_game',
                'dreb': 'per_game_dreb_per_game',
                'tov': 'per_game_tov_per_game',
                'pf': 'per_game_pf_per_game',
                'min': 'per_game_mp_per_game',
                # Advanced stats
                'usg_pct': 'advanced_usg_percent',
                'ast_pct': 'advanced_ast_percent',
                'tov_pct': 'advanced_tov_percent',
                'oreb_pct': 'advanced_orb_percent',
                'dreb_pct': 'advanced_drb_percent',
                'stl_pct': 'advanced_stl_percent',
                'blk_pct': 'advanced_blk_percent',
                'ts_pct': 'advanced_ts_percent',
                'efg_pct': 'per_game_e_fg_percent',
                # Per 36 stats
                'fga_pg': 'per_36_fga_per_36_min',
                'fta_pg': 'per_36_fta_per_36_min',
                'fg3a_pg': 'per_36_x3pa_per_36_min',
                # Shooting by zone
                'restricted_area_fga': 'shooting_num_fga_from_x0_3_range',
                'restricted_area_fgm': 'shooting_num_fgm_from_x0_3_range',
                'restricted_area_fg_pct': 'shooting_percent_fga_from_x0_3_range',
                'in_the_paint_non_ra_fga': 'shooting_num_fga_from_x3_10_range',
                'in_the_paint_non_ra_fg_pct': 'shooting_percent_fga_from_x3_10_range',
                'mid_range_fga': 'shooting_num_fga_from_x10_16_range',
                'mid_range_fg_pct': 'shooting_percent_fga_from_x10_16_range',
                'above_the_break_3_fga': 'shooting_num_fga_from_x16_3p_range',
                'above_the_break_3_fg_pct': 'shooting_percent_fga_from_x16_3p_range',
                'corner_3_fga': 'shooting_num_fga_from_x3p_range',
                'corner_3_fg_pct': 'shooting_percent_corner_3s_of_3pa',
                # Tracking
                'drives': 'tracking_drives_pg',
                'drive_fga': 'tracking_drive_fga',
                'drive_fg_pct': 'tracking_drive_fg_pct',
                'ast_to_pass_pct': 'tracking_ast_to_pass_pct',
                'ast_to_pass_pct_adj': 'tracking_ast_to_pass_pct_adj',
                'touches': 'tracking_touches_pg',
                'potential_ast': 'tracking_potential_ast_pg',
                'passes_made': 'tracking_passes_made_pg',
                'secondary_ast': 'tracking_secondary_ast_pg',
                'avg_speed': 'tracking_avg_speed',
                'avg_speed_off': 'tracking_avg_speed_off',
                'avg_speed_def': 'tracking_avg_speed_def',
                'dist_miles': 'tracking_dist_miles_pg',
                'dist_miles_off': 'tracking_dist_miles_off_pg',
                'dist_miles_def': 'tracking_dist_miles_def_pg',
                'avg_sec_per_touch': 'tracking_avg_sec_per_touch',
                'avg_drib_per_touch': 'tracking_avg_drib_per_touch',
                'time_of_poss': 'tracking_time_of_poss_pg',
                'front_ct_touches': 'tracking_front_ct_touches_pg',
                'elbow_touches': 'tracking_elbow_touches_pg',
                # Hustle
                'deflections': 'hustle_deflections_pg',
                'contested_shots': 'hustle_contested_shots_pg',
                'contested_shots_2pt': 'hustle_contested_2pt_pg',
                'contested_shots_3pt': 'hustle_contested_3pt_pg',
                'charges_drawn': 'hustle_charges_drawn_pg',
                'loose_balls_recovered': 'hustle_loose_balls_recovered',
                'def_loose_balls_recovered': 'hustle_loose_balls_recovered_def_pg',
                # Playtype
                'poss_pct': 'playtype_transition_poss_pct',
                'pfd': 'misc_pfd_pg',
                # Bio
                'player_height': 'height',
                'player_height_inches': 'player_info_ht_in_in',
                'player_weight': 'player_info_wt',
                'position': 'position',
                'draft_year': 'draft_year',
                'draft_round': 'draft_round',
                'draft_number': 'draft_number',
                'country': 'country',
                # Scoring
                'pct_uast_2pm': 'shooting_percent_assisted_x2p_fg',
                'pct_uast_3pm': 'shooting_percent_assisted_x3p_fg',
                'pct_pts_paint': 'misc_pts_paint_pg',
                'pct_fga_3pt': 'shooting_percent_fga_from_x3p_range',
                'pct_fga_2pt': 'shooting_percent_fga_from_x0_10_range',
                'pct_pts_2pt_mr': 'shooting_percent_fga_from_x10_16_range',
                # Pullup
                'pull_up_fga': 'tracking_pullup_fga',
                'pull_up_fg_pct': 'tracking_pullup_fg_pct',
                'pull_up_fg3a': 'tracking_pullup_fg3a',
                'pull_up_fg3_pct': 'tracking_pullup_fg3_pct',
                'pull_up_efg_pct': 'tracking_pullup_efg_pct',
                # Catch shoot
                'catch_shoot_fga': 'tracking_catch_shoot_fga',
                'catch_shoot_fg_pct': 'tracking_catch_shoot_fg_pct',
                'catch_shoot_fg3a': 'tracking_catch_shoot_fg3a',
                'catch_shoot_fg3_pct': 'tracking_catch_shoot_fg3_pct',
                'catch_shoot_efg_pct': 'tracking_catch_shoot_efg_pct',
                # Drives
                'drive_fta': 'tracking_drive_fta',
                'drive_ft_pct': 'tracking_drive_ft_pct',
                'drive_ast': 'tracking_drive_ast_pg',
                'drive_passes': 'tracking_drive_passes_pg',
                'drive_passes_pct': 'tracking_drive_pass_rate',
                'drive_ast_pct': 'tracking_drive_ast_rate',
                'drive_tov_pct': 'tracking_drive_tov_pct',
                'drive_pts_pct': 'tracking_drive_pts_pct',
                # Rebounding
                'oreb_chances': 'tracking_oreb_chances',
                'oreb_chance_pct': 'tracking_oreb_chance_pct',
                'oreb_contest_pct': 'tracking_oreb_contest_pct',
                'dreb_chances': 'tracking_dreb_chances',
                'dreb_chance_pct': 'tracking_dreb_chance_pct',
                'dreb_contest_pct': 'tracking_dreb_contest_pct',
                # Box outs
                'box_outs': 'hustle_box_outs_pg',
                'def_boxouts': 'hustle_def_boxouts_pg',
                'off_boxouts': 'hustle_off_boxouts_pg',
                # Passing
                'ft_ast': 'tracking_ft_ast_pg',
                'ast_pts_created': 'tracking_ast_pts_created',
                'passes_received': 'tracking_passes_received',
                # Post ups
                'post_touches': 'tracking_post_touches',
                'post_touch_fga': 'tracking_post_touch_fga',
                'post_touch_fg_pct': 'tracking_post_touch_fg_pct',
                'post_touch_ast': 'tracking_post_touch_ast',
                'post_touch_ast_pct': 'tracking_post_touch_ast_pct',
                'post_touch_passes': 'tracking_post_touch_passes',
                'post_touch_passes_pct': 'tracking_post_touch_passes_pct',
                'post_touch_pts': 'tracking_post_touch_pts',
                'post_touch_pts_pct': 'tracking_post_touch_pts_pct',
                'post_touch_tov': 'tracking_post_touch_tov',
                'post_touch_tov_pct': 'tracking_post_touch_tov_pct',
                'post_touch_fta': 'tracking_post_touch_fta',
                'post_touch_ft_pct': 'tracking_post_touch_ft_pct',
                'post_touch_fouls': 'tracking_post_touch_fouls',
                'post_touch_fouls_pct': 'tracking_post_touch_fouls_pct',
                # Misc
                'pts_paint': 'misc_pts_paint_pg',
                'pts_fb': 'misc_pts_fb_pg',
                'pts_2nd_chance': 'misc_pts_2nd_chance_pg',
                'pts_off_tov': 'misc_pts_off_tov_pg',
                'opp_pts_paint': 'misc_opp_pts_paint_pg',
                'opp_pts_fb': 'misc_opp_pts_fb_pg',
                'opp_pts_2nd_chance': 'misc_opp_pts_2nd_chance_pg',
                'opp_pts_off_tov': 'misc_opp_pts_off_tov_pg',
                # Isolation
                'poss': 'playtype_iso_poss',
                'ppp': 'playtype_iso_ppp',
                'fga': 'playtype_iso_fga',
                'fg_pct': 'playtype_iso_fg_pct',
                'efg_pct': 'playtype_iso_efg_pct',
                # Spot up
                'poss_pct': 'playtype_spotup_poss_pct',
                'ppp': 'playtype_spotup_ppp',
                'fga': 'playtype_spotup_fga',
                'fg_pct': 'playtype_spotup_fg_pct',
                'efg_pct': 'playtype_spotup_efg_pct',
                # Experience
                'experience': 'experience',
                # Team
                'team_abbr': 'team_abbr',
                'team_id': 'team_id',
                # Season
                'season': 'season_label',
                # Plus/minus
                'plus_minus': 'per_game_plus_minus',
                # Dunks
                'pct_dunks_of_fga': 'shooting_percent_dunks_of_fga',
                'num_of_dunks': 'shooting_num_of_dunks',
            }
            if nk in key_map:
                nk = key_map[nk]
            normalized[nk] = v
        out.append(normalized)
    
    return out

def load_all_rows(db_dir):
    all_rows = []
    candidates = [
        db_dir,
        os.path.join(db_dir, "NBA Site data"),
        os.path.join(os.getcwd(), "NBA Site data"),
    ]
    seen = set()
    season_dirs = []
    
    for cand in candidates:
        norm = os.path.normcase(os.path.abspath(cand))
        if norm in seen:
            continue
        seen.add(norm)
        if os.path.isdir(norm):
            if any(f.startswith("player_traditional_") for f in os.listdir(norm)):
                season_dirs.append(norm)
            for sub in sorted(os.listdir(norm)):
                subpath = os.path.join(norm, sub)
                if os.path.isdir(subpath):
                    sub_norm = os.path.normcase(os.path.abspath(subpath))
                    if sub_norm not in seen:
                        seen.add(sub_norm)
                        if any(f.startswith("player_traditional_") for f in os.listdir(subpath)):
                            season_dirs.append(subpath)
    
    for sdir in season_dirs:
        try:
            rows = load_season_rows(sdir)
            for i, row in enumerate(rows):
                row.setdefault("__source_file", f"NBA Site data ({os.path.basename(sdir)})")
                row.setdefault("__row_index", i)
            all_rows.extend(rows)
        except Exception:
            pass
    
    return all_rows

# ── Role catalog ───────────────────────────────────────────────────────────
def load_role_catalog(roles_dir):
    catalog = {}
    if not os.path.isdir(roles_dir):
        return catalog
    for f in os.listdir(roles_dir):
        if f.endswith('.json'):
            try:
                with open(os.path.join(roles_dir, f), 'r') as fh:
                    data = json.load(fh)
                    if isinstance(data, dict):
                        catalog[f.replace('.json', '')] = data
            except:
                pass
    return catalog

def load_attribute_definitions(roles_dir):
    """Load attribute definition files if they exist."""
    defs = {}
    attr_def_path = os.path.join(roles_dir, "attribute_definitions.json")
    if os.path.exists(attr_def_path):
        try:
            with open(attr_def_path, 'r') as f:
                defs = json.load(f)
        except:
            pass
    return defs

# ── Committee floors ───────────────────────────────────────────────────────
def load_committee_floors(roles_dir):
    floors = {}
    excel_path = os.path.join(roles_dir, "attributes two.xlsx")
    if not os.path.exists(excel_path):
        return floors
    # Try to read as CSV if xlsx isn't available
    csv_path = os.path.join(roles_dir, "attributes_two.csv")
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('player_name', '').strip().lower()
                    if name:
                        normalized_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
                        floors[normalized_name] = {k: int(sf(v, 0)) for k, v in row.items() if k != 'player_name' and sf(v, 0) > 0}
        except:
            pass
    return floors

# ── Formula-based attribute computation ────────────────────────────────────
def compute_attributes_formula(row, tendencies, roles_dir, all_rows=None):
    """Compute attributes using statistical formulas (no ML)."""
    usg = sf(row.get("advanced_usg_percent"))
    ast_pct = sf(row.get("advanced_ast_percent"))
    tov_pct = sf(row.get("advanced_tov_percent"))
    orb_pct = sf(row.get("advanced_orb_percent"))
    drb_pct = sf(row.get("advanced_drb_percent"))
    stl_pct = sf(row.get("advanced_stl_percent"))
    blk_pct = sf(row.get("advanced_blk_percent"))
    fta36 = sf(row.get("per_36_fta_per_36_min"))
    fg3a36 = sf(row.get("per_36_x3pa_per_36_min"))
    fg3a_pg = sf(row.get("per_36_x3pa_per_36_min"))
    fga36 = sf(row.get("per_36_fga_per_36_min"))
    three_pct = sf(row.get("per_36_x3p_percent"), sf(row.get("per_game_x3p_percent")))
    two_pct = sf(row.get("per_36_x2p_percent"), sf(row.get("per_game_x2p_percent")))
    efg_pct = sf(row.get("per_36_e_fg_percent"), sf(row.get("per_game_e_fg_percent")))
    ts_pct = sf(row.get("advanced_ts_percent"), efg_pct)
    ft_pct = sf(row.get("per_36_ft_percent"), sf(row.get("per_game_ft_percent")))
    assisted2 = sf(row.get("shooting_percent_assisted_x2p_fg"))
    assisted3 = sf(row.get("shooting_percent_assisted_x3p_fg"))
    rim_share = sf(row.get("shooting_percent_fga_from_x0_3_range"))
    close_share = sf(row.get("shooting_percent_fga_from_x3_10_range"))
    mid_share = sf(row.get("shooting_percent_fga_from_x10_16_range"))
    long_mid_share = sf(row.get("shooting_percent_fga_from_x16_3p_range"))
    three_share = sf(row.get("shooting_percent_fga_from_x3p_range"))
    corner_three_share = sf(row.get("shooting_percent_corner_3s_of_3pa"))
    dunks_share = sf(row.get("shooting_percent_dunks_of_fga"))
    dunks = sf(row.get("shooting_num_of_dunks"))
    minutes = sf(row.get("totals_mp"))
    mpg = sf(row.get("per_game_mp_per_game"))
    pf100 = sf(row.get("per_100_pf_per_100_poss"))
    age = sf(row.get("age"), 27.0)
    position = str(row.get("position", ""))
    
    tracking_drives_pg = sf(row.get("tracking_drives_pg"))
    tracking_ast_to_pass_pct = sf(row.get("tracking_ast_to_pass_pct"))
    tracking_ast_to_pass_pct_adj = sf(row.get("tracking_ast_to_pass_pct_adj"), tracking_ast_to_pass_pct)
    tracking_touches_pg = sf(row.get("tracking_touches_pg"))
    tracking_potential_ast_pg = sf(row.get("tracking_potential_ast_pg"))
    tracking_passes_made_pg = sf(row.get("tracking_passes_made_pg"))
    tracking_secondary_ast_pg = sf(row.get("tracking_secondary_ast_pg"))
    tracking_avg_speed = sf(row.get("tracking_avg_speed"))
    tracking_avg_speed_off = sf(row.get("tracking_avg_speed_off"), tracking_avg_speed)
    tracking_avg_speed_def = sf(row.get("tracking_avg_speed_def"), tracking_avg_speed)
    hustle_contested_shots_pg = sf(row.get("hustle_contested_shots_pg"))
    hustle_contested_2pt_pg = sf(row.get("hustle_contested_2pt_pg"))
    hustle_contested_3pt_pg = sf(row.get("hustle_contested_3pt_pg"))
    hustle_deflections_pg = sf(row.get("hustle_deflections_pg"))
    hustle_contested_shots_pg = sf(row.get("hustle_contested_shots_pg"))
    hustle_contested_2pt_pg = sf(row.get("hustle_contested_2pt_pg"))
    hustle_contested_3pt_pg = sf(row.get("hustle_contested_3pt_pg"))
    hustle_charges_drawn_pg = sf(row.get("hustle_charges_drawn_pg"))
    hustle_loose_balls_recovered_def_pg = sf(row.get("hustle_loose_balls_recovered_def_pg"))
    
    pts_pg = sf(row.get("per_game_pts_per_game"))
    reb_pg = sf(row.get("per_game_reb_per_game"))
    ast_pg = sf(row.get("per_game_ast_per_game"))
    stl_pg = sf(row.get("per_game_stl_per_game"))
    blk_pg = sf(row.get("per_game_blk_per_game"))
    height_in = sf(row.get("player_info_ht_in_in"))
    weight = sf(row.get("player_info_wt"))
    
    # Derived scores
    usage_score = remap(usg, 12.0, 35.0, 0.0, 100.0)
    creation_2_score = remap(1.0 - assisted2, 0.10, 0.85, 0.0, 100.0)
    creation_3_score = remap(1.0 - assisted3, 0.10, 0.85, 0.0, 100.0)
    efficiency_score = remap(ts_pct, 0.48, 0.68, 0.0, 100.0)
    turnover_control = remap(1.0 - remap(tov_pct, 8.0, 20.0, 0.0, 1.0), 0.0, 1.0, 0.0, 100.0)
    workload_score = remap(minutes, 350.0, 3000.0, 0.0, 100.0)
    play_gravity_score = 0.60 * remap(three_pct, 0.30, 0.41, 0.0, 100.0) + 0.40 * remap(fg3a_pg, 0.5, 8.0, 0.0, 100.0)
    burst_score = 0.62 * remap(rim_share, 0.10, 0.55, 0.0, 100.0) + 0.38 * remap(dunks_share, 0.00, 0.14, 0.0, 100.0)
    handle_pace_score = 0.40 * creation_2_score + 0.28 * creation_3_score + 0.18 * turnover_control + 0.14 * burst_score
    downhill_pressure_score = 0.54 * remap(rim_share, 0.10, 0.55, 0.0, 100.0) + 0.30 * remap(fta36, 1.0, 12.0, 0.0, 100.0) + 0.16 * remap(mpg, 8.0, 38.0, 0.0, 100.0)
    shot_quality_score = 0.44 * remap(ts_pct, 0.52, 0.66, 0.0, 100.0) + 0.26 * remap(efg_pct, 0.48, 0.62, 0.0, 100.0) + 0.18 * remap(two_pct, 0.46, 0.67, 0.0, 100.0) + 0.12 * remap(ft_pct, 0.60, 0.90, 0.0, 100.0)
    
    is_big = "C" in position or "PF" in position
    is_guard = "PG" in position or "SG" in position
    is_forward = "SF" in position or "PF" in position
    is_center = "C" in position and "PF" not in position
    
    # Committee floors
    committee = load_committee_floors(roles_dir)
    pname_raw = repair_text(row.get("player_name", "")).strip().lower()
    pname_lower = unicodedata.normalize("NFKD", pname_raw).encode("ascii", "ignore").decode("ascii")
    committee_attrs = committee.get(pname_lower, {})
    
    # Compute each attribute
    attrs = {}
    
    # FINISHING
    attrs["Close Shot"] = int(clamp(
        0.45 * remap(rim_share, 0.10, 0.55, 30, 90) +
        0.30 * remap(ts_pct, 0.50, 0.68, 30, 90) +
        0.25 * remap(1.0 - assisted2, 0.15, 0.80, 30, 90),
        25, 99))
    
    attrs["Driving Layup"] = int(clamp(
        0.40 * remap(tracking_drives_pg, 2.0, 18.0, 30, 95) +
        0.25 * remap(rim_share, 0.10, 0.55, 30, 90) +
        0.20 * remap(two_pct, 0.45, 0.67, 30, 90) +
        0.15 * burst_score,
        25, 99))
    
    attrs["Standing Dunk"] = int(clamp(
        0.50 * remap(dunks_share, 0.00, 0.14, 25, 95) +
        0.30 * (90 if height_in >= 82 else 70 if height_in >= 80 else 50 if height_in >= 78 else 35) +
        0.20 * remap(weight, 200, 280, 30, 90),
        25, 99))
    
    attrs["Driving Dunk"] = int(clamp(
        0.45 * remap(dunks_share, 0.00, 0.14, 25, 95) +
        0.25 * burst_score +
        0.15 * remap(tracking_drives_pg, 2.0, 18.0, 30, 90) +
        0.15 * (90 if height_in >= 80 else 70 if height_in >= 78 else 50),
        25, 99))
    
    # SHOOTING
    attrs["Mid-Range Shot"] = int(clamp(
        0.40 * remap(two_pct, 0.40, 0.60, 30, 90) +
        0.30 * remap(mid_share + long_mid_share, 0.05, 0.40, 30, 90) +
        0.30 * remap(1.0 - assisted2, 0.15, 0.80, 30, 90),
        25, 99))
    
    attrs["Three-Point Shot"] = int(clamp(
        0.50 * remap(three_pct, 0.28, 0.45, 30, 95) +
        0.30 * remap(fg3a_pg, 0.5, 10.0, 30, 95) +
        0.20 * play_gravity_score,
        25, 99))
    
    attrs["Free Throw"] = int(clamp(
        0.70 * remap(ft_pct, 0.55, 0.92, 30, 99) +
        0.30 * remap(fta36, 1.0, 12.0, 30, 90),
        25, 99))
    
    attrs["Shot IQ"] = int(clamp(
        0.40 * shot_quality_score +
        0.30 * remap(1.0 - tov_pct / 100.0, 0.70, 0.92, 30, 95) +
        0.30 * efficiency_score,
        25, 99))
    
    # POST
    attrs["Post Hook"] = int(clamp(
        0.50 * (80 if is_big else 35) +
        0.30 * remap(rim_share, 0.10, 0.55, 25, 85) +
        0.20 * remap(weight, 220, 280, 25, 80),
        25, 99))
    
    attrs["Post Fade"] = int(clamp(
        0.40 * remap(long_mid_share, 0.02, 0.25, 25, 85) +
        0.35 * (75 if is_forward else 40) +
        0.25 * creation_2_score,
        25, 99))
    
    attrs["Post Control"] = int(clamp(
        0.40 * (80 if is_big else 35) +
        0.30 * remap(weight, 220, 280, 25, 85) +
        0.30 * remap(height_in, 78, 84, 25, 90),
        25, 99))
    
    # PLAYMAKING
    attrs["Ball Handle"] = int(clamp(
        0.40 * handle_pace_score +
        0.25 * remap(tracking_drives_pg, 2.0, 18.0, 30, 95) +
        0.20 * turnover_control +
        0.15 * (90 if is_guard else 60 if is_forward else 40),
        25, 99))
    
    attrs["Speed with Ball"] = int(clamp(
        0.45 * handle_pace_score +
        0.30 * remap(tracking_drives_pg, 2.0, 18.0, 30, 90) +
        0.25 * (85 if is_guard else 60 if is_forward else 40),
        25, 99))
    
    attrs["Pass Accuracy"] = int(clamp(
        0.40 * remap(tracking_ast_to_pass_pct, 0.10, 0.40, 30, 95) +
        0.30 * remap(ast_pct, 10.0, 45.0, 30, 95) +
        0.30 * turnover_control,
        25, 99))
    
    attrs["Pass IQ"] = int(clamp(
        0.35 * remap(ast_pct, 10.0, 45.0, 30, 95) +
        0.30 * remap(tracking_ast_to_pass_pct, 0.10, 0.40, 30, 90) +
        0.20 * remap(tracking_secondary_ast_pg, 0.5, 4.0, 30, 90) +
        0.15 * turnover_control,
        25, 99))
    
    attrs["Pass Vision"] = int(clamp(
        0.35 * remap(ast_pg, 1.0, 11.0, 30, 95) +
        0.30 * remap(tracking_potential_ast_pg, 2.0, 15.0, 30, 95) +
        0.20 * remap(tracking_passes_made_pg, 100, 500, 30, 90) +
        0.15 * remap(ast_pct, 10.0, 45.0, 30, 90),
        25, 99))
    
    attrs["Draw Foul"] = int(clamp(
        0.50 * remap(fta36, 1.0, 12.0, 25, 95) +
        0.30 * remap(usg, 12.0, 35.0, 25, 90) +
        0.20 * burst_score,
        25, 99))
    
    attrs["Hands"] = int(clamp(
        0.40 * remap(1.0 - tov_pct / 100.0, 0.70, 0.92, 30, 95) +
        0.30 * remap(reb_pg, 1.0, 14.0, 30, 90) +
        0.30 * efficiency_score,
        25, 99))
    
    # DEFENSE
    attrs["Interior Defense"] = int(clamp(
        0.40 * remap(blk_pct, 0.5, 6.0, 30, 95) +
        0.30 * (85 if is_big else 55 if is_forward else 40) +
        0.15 * remap(height_in, 76, 84, 30, 90) +
        0.15 * remap(weight, 180, 280, 30, 85),
        25, 99))
    
    attrs["Perimeter Defense"] = int(clamp(
        0.40 * remap(stl_pct, 0.5, 3.5, 30, 95) +
        0.30 * (85 if is_guard else 60 if is_forward else 45) +
        0.15 * remap(hustle_deflections_pg, 1.0, 6.0, 30, 90) +
        0.15 * remap(tracking_avg_speed, 3.5, 5.0, 30, 90),
        25, 99))
    
    attrs["Steal"] = int(clamp(
        0.50 * remap(stl_pct, 0.5, 3.5, 25, 95) +
        0.30 * remap(hustle_deflections_pg, 1.0, 6.0, 25, 90) +
        0.20 * (85 if is_guard else 55 if is_forward else 40),
        25, 99))
    
    attrs["Block"] = int(clamp(
        0.55 * remap(blk_pct, 0.5, 6.0, 25, 95) +
        0.25 * remap(height_in, 76, 84, 25, 90) +
        0.20 * (85 if is_center else 60 if is_big else 35),
        25, 99))
    
    attrs["Help Defense IQ"] = int(clamp(
        0.35 * remap(blk_pct, 0.5, 6.0, 30, 90) +
        0.30 * remap(hustle_contested_shots_pg, 1.0, 6.0, 30, 90) +
        0.20 * (80 if is_big else 55) +
        0.15 * remap(drb_pct, 5.0, 30.0, 30, 90),
        25, 99))
    
    attrs["Pass Perception"] = int(clamp(
        0.40 * remap(stl_pct, 0.5, 3.5, 30, 90) +
        0.30 * remap(hustle_deflections_pg, 1.0, 6.0, 30, 90) +
        0.30 * (80 if is_guard else 55 if is_forward else 50),
        25, 99))
    
    # REBOUNDING
    attrs["Offensive Rebound"] = int(clamp(
        0.55 * remap(orb_pct, 2.0, 15.0, 25, 95) +
        0.25 * (85 if is_big else 50 if is_forward else 30) +
        0.20 * remap(weight, 180, 280, 25, 85),
        25, 99))
    
    attrs["Defensive Rebound"] = int(clamp(
        0.50 * remap(drb_pct, 5.0, 30.0, 30, 95) +
        0.30 * (85 if is_big else 55 if is_forward else 35) +
        0.20 * remap(weight, 180, 280, 25, 85),
        25, 99))
    
    # PHYSICAL
    attrs["Speed"] = int(clamp(
        0.50 * remap(tracking_avg_speed, 3.5, 5.0, 30, 95) +
        0.30 * (85 if is_guard else 60 if is_forward else 45) +
        0.20 * remap(1.0 - weight / 300.0, 0.60, 0.85, 30, 95),
        25, 99))
    
    attrs["Agility"] = int(clamp(
        0.40 * remap(tracking_avg_speed, 3.5, 5.0, 30, 90) +
        0.30 * (85 if is_guard else 60 if is_forward else 45) +
        0.30 * remap(burst_score, 20, 80, 30, 95),
        25, 99))
    
    attrs["Strength"] = int(clamp(
        0.50 * remap(weight, 170, 280, 25, 95) +
        0.30 * (85 if is_big else 55 if is_forward else 40) +
        0.20 * remap(orb_pct + drb_pct, 5.0, 35.0, 25, 90),
        25, 99))
    
    attrs["Vertical"] = int(clamp(
        0.40 * burst_score +
        0.30 * remap(dunks_share, 0.00, 0.14, 25, 95) +
        0.15 * (85 if height_in <= 80 else 60 if height_in <= 82 else 45) +
        0.15 * remap(tracking_avg_speed, 3.5, 5.0, 30, 90),
        25, 99))
    
    attrs["Stamina"] = int(clamp(
        0.50 * remap(mpg, 8.0, 38.0, 30, 95) +
        0.30 * remap(minutes, 350.0, 3000.0, 30, 95) +
        0.20 * remap(1.0 - age / 45.0, 0.60, 0.85, 30, 90),
        25, 99))
    
    # MENTAL
    attrs["Offensive Consistency"] = int(clamp(
        0.40 * efficiency_score +
        0.30 * remap(usg, 12.0, 35.0, 30, 95) +
        0.30 * turnover_control,
        25, 99))
    
    attrs["Defensive Consistency"] = int(clamp(
        0.40 * remap(hustle_contested_shots_pg, 1.0, 6.0, 30, 95) +
        0.30 * remap(stl_pct + blk_pct, 1.0, 8.0, 30, 95) +
        0.30 * remap(mpg, 8.0, 38.0, 30, 90),
        25, 99))
    
    # META
    attrs["Intangibles"] = 25  # constant
    attrs["Hustle"] = int(clamp(
        0.40 * remap(hustle_deflections_pg, 1.0, 6.0, 30, 95) +
        0.30 * remap(hustle_contested_shots_pg, 1.0, 6.0, 30, 90) +
        0.30 * remap(orb_pct, 2.0, 15.0, 25, 90),
        25, 99))
    attrs["Overall Durability"] = int(clamp(
        remap(sf(row.get("per_game_g", 0)), 10, 82, 25, 99),
        25, 99))
    attrs["Potential"] = int(clamp(
        remap(1.0 - age / 45.0, 0.60, 0.90, 25, 99),
        25, 99))
    
    # Apply committee floors
    for attr_name, floor_val in committee_attrs.items():
        if attr_name in attrs:
            attrs[attr_name] = max(attrs[attr_name], floor_val)
    
    # Force Shot IQ to exactly match the sheet value
    if "Shot IQ" in committee_attrs:
        attrs["Shot IQ"] = committee_attrs["Shot IQ"]
    
    # Roles
    roles = []
    if usage_score > 60 and handle_pace_score > 55:
        roles.append("Primary Ball Handler")
    if play_gravity_score > 60 and three_pct > 0.36:
        roles.append("Floor Spacer")
    if burst_score > 55 and dunks_share > 0.05:
        roles.append("Rim Attacker")
    if shot_quality_score > 55:
        roles.append("Efficient Scorer")
    if is_big and attrs["Interior Defense"] > 60:
        roles.append("Rim Protector")
    if not roles:
        roles.append("Core")
    
    # OVR
    finishing = [attrs.get("Driving Layup", 50), attrs.get("Standing Dunk", 50), attrs.get("Driving Dunk", 50), attrs.get("Close Shot", 50)]
    shooting = [attrs.get("Mid-Range Shot", 50), attrs.get("Three-Point Shot", 50), attrs.get("Free Throw", 50), attrs.get("Shot IQ", 50)]
    playmaking = [attrs.get("Ball Handle", 50), attrs.get("Speed with Ball", 50), attrs.get("Pass Accuracy", 50), attrs.get("Pass IQ", 50), attrs.get("Pass Vision", 50)]
    defense = [attrs.get("Interior Defense", 50), attrs.get("Perimeter Defense", 50), attrs.get("Steal", 50), attrs.get("Block", 50)]
    physical = [attrs.get("Speed", 50), attrs.get("Agility", 50), attrs.get("Strength", 50), attrs.get("Vertical", 50)]
    
    def avg(vals):
        return sum(vals) / len(vals) if vals else 50
    
    ovr = int(clamp(
        avg(finishing) * 0.15 +
        avg(shooting) * 0.25 +
        avg(playmaking) * 0.15 +
        avg(defense) * 0.20 +
        avg(physical) * 0.10 +
        attrs.get("Intangibles", 50) * 0.10 +
        attrs.get("Hustle", 50) * 0.05,
        60, 99))
    
    return {"attributes": attrs, "roles": roles, "ovr": ovr}

# ── Tendency computation ───────────────────────────────────────────────────
@dataclass
class TendencyResult:
    name: str
    final: float
    pre_cap: float
    recommended_cap: int
    absolute_cap: int

THREE_POINT_RULES = {
    "Shot Three": {"base_key": "per_game_x3p_percent", "range": (0.0, 50.0), "cap": 95},
    "Spot Up Shot Three": {"base_key": "spot_up_three_point_frequency", "range": (0.0, 40.0), "cap": 90},
    "Off Screen Shot Three": {"base_key": "off_screen_three_point_frequency", "range": (0.0, 30.0), "cap": 85},
    "Contested Jumper Three": {"base_key": "contested_three_point_frequency", "range": (0.0, 30.0), "cap": 85},
    "Stepback Jumper Three": {"base_key": "step_back_three_point_frequency", "range": (0.0, 20.0), "cap": 80},
    "Drive Pull Up Three": {"base_key": "dribble_pull_up_three_point_frequency", "range": (0.0, 25.0), "cap": 80},
    "Transition Pull Up Three": {"base_key": "transition_pull_up_three_point_frequency", "range": (0.0, 20.0), "cap": 75},
}

MID_POST_RULES = {
    "Shot Mid-Range": {"base_key": "per_game_fg_percent", "range": (0.0, 60.0), "cap": 90},
    "Spot Up Shot Mid-Range": {"base_key": "spot_up_mid_range_frequency", "range": (0.0, 30.0), "cap": 85},
    "Off Screen Shot Mid-Range": {"base_key": "off_screen_mid_range_frequency", "range": (0.0, 25.0), "cap": 80},
    "Contested Jumper Mid-Range": {"base_key": "contested_mid_range_frequency", "range": (0.0, 25.0), "cap": 80},
    "Stepback Jumper Mid-Range": {"base_key": "step_back_mid_range_frequency", "range": (0.0, 15.0), "cap": 75},
    "Drive Pull Up Mid-Range": {"base_key": "dribble_pull_up_mid_range_frequency", "range": (0.0, 20.0), "cap": 80},
}

DRIBBLE_RULES = {
    "Driving Layup": {"base_key": "drives_per_game", "range": (0.0, 15.0), "cap": 95},
    "Driving Crossover": {"base_key": "crossover_frequency", "range": (0.0, 30.0), "cap": 90},
    "Driving Spin": {"base_key": "spin_frequency", "range": (0.0, 20.0), "cap": 85},
    "Driving Step Back": {"base_key": "step_back_frequency", "range": (0.0, 15.0), "cap": 80},
    "Driving Half Spin": {"base_key": "half_spin_frequency", "range": (0.0, 15.0), "cap": 80},
    "Driving Double Crossover": {"base_key": "double_crossover_frequency", "range": (0.0, 15.0), "cap": 80},
    "Driving Behind The Back": {"base_key": "behind_the_back_frequency", "range": (0.0, 15.0), "cap": 80},
    "Driving Dribble Hesitation": {"base_key": "hesitation_frequency", "range": (0.0, 15.0), "cap": 80},
    "Driving In And Out": {"base_key": "in_and_out_frequency", "range": (0.0, 15.0), "cap": 80},
}

DEFENSE_RULES = {
    "Block Shot": {"base_key": "per_game_blk_per_game", "range": (0.0, 3.0), "cap": 95},
    "On-Ball Steal": {"base_key": "per_game_stl_per_game", "range": (0.0, 2.5), "cap": 90},
    "Contest Shot": {"base_key": "contested_shot_frequency", "range": (0.0, 30.0), "cap": 85},
    "Pass Interception": {"base_key": "deflections_per_game", "range": (0.0, 5.0), "cap": 90},
}

def compute_tendencies(row):
    results = []
    all_rules = {**THREE_POINT_RULES, **MID_POST_RULES, **DRIBBLE_RULES, **DEFENSE_RULES}
    
    for name, rule in all_rules.items():
        base_key = rule["base_key"]
        range_min, range_max = rule["range"]
        cap = rule["cap"]
        
        raw = sf(row.get(base_key, 0.0))
        pre_cap = ((raw - range_min) / (range_max - range_min)) * 100.0 if range_max > range_min else 0.0
        pre_cap = max(0.0, min(100.0, pre_cap))
        final = min(pre_cap, cap)
        
        results.append(TendencyResult(
            name=name,
            final=round(final, 1),
            pre_cap=round(pre_cap, 1),
            recommended_cap=cap,
            absolute_cap=min(cap + 10, 99),
        ))
    
    for core_name, core_key in [("Touches", "per_game_touches"), ("Shot", "per_game_fga"), ("Play Discipline", "per_game_ast")]:
        raw = sf(row.get(core_key, 0.0))
        pre_cap = min(raw * 5.0, 100.0)
        results.append(TendencyResult(
            name=core_name,
            final=round(pre_cap, 1),
            pre_cap=round(pre_cap, 1),
            recommended_cap=90,
            absolute_cap=99,
        ))
    
    return results

# ── Badge computation ──────────────────────────────────────────────────────
def load_badges_from_file(badges_txt):
    badges = []
    if not os.path.exists(badges_txt):
        return badges
    with open(badges_txt, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                badges.append({"name": parts[0], "group": parts[1], "threshold": sf(parts[2])})
    return badges

def compute_badge_groups(row, attrs, tendencies, family_scores, ovr, badges_txt):
    badges_list = load_badges_from_file(badges_txt)
    groups = {}
    for badge in badges_list:
        group = badge["group"]
        if group not in groups:
            groups[group] = []
        
        threshold = badge["threshold"]
        attr_key = normalize_key(badge["name"])
        attr_val = attrs.get(attr_key, attrs.get(badge["name"], 0))
        
        if attr_val >= threshold:
            tier = "HOF" if attr_val >= threshold * 1.3 else "Gold" if attr_val >= threshold else "Silver"
            groups[group].append({"name": badge["name"], "tier": tier, "value": int(attr_val)})
        else:
            groups[group].append({"name": badge["name"], "tier": "Bronze", "value": int(attr_val)})
    
    return groups

# ── Attribute family averages ──────────────────────────────────────────────
ATTRIBUTE_FAMILIES = {
    "Finishing": ["Driving Layup", "Standing Dunk", "Driving Dunk", "Close Shot"],
    "Shooting": ["Mid-Range Shot", "Three-Point Shot", "Free Throw", "Shot IQ"],
    "Playmaking": ["Ball Handle", "Speed with Ball", "Pass Accuracy", "Pass IQ", "Pass Vision", "Draw Foul", "Hands"],
    "Defense": ["Interior Defense", "Perimeter Defense", "Steal", "Block", "Help Defense IQ", "Pass Perception"],
    "Rebounding": ["Offensive Rebound", "Defensive Rebound"],
    "Physical": ["Speed", "Agility", "Strength", "Vertical", "Stamina"],
    "Mental": ["Offensive Consistency", "Defensive Consistency"],
    "Post": ["Post Hook", "Post Fade", "Post Control"],
}

def compute_attribute_family_averages(attrs):
    families = {}
    for family, members in ATTRIBUTE_FAMILIES.items():
        vals = [attrs.get(m, 50) for m in members if m in attrs]
        families[family] = sum(vals) / len(vals) if vals else 50
    return families

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    # Load rows
    rows = load_all_rows(db_dir)
    
    # Build name index
    name_index = {}
    for r in rows:
        name = normalize_name(repair_text(r.get("player_name", "")))
        if name:
            name_index.setdefault(name, []).append(r)
    
    # Find player
    target_name = normalize_name(player_name_arg)
    target_season = season_arg.strip().lower()
    
    season_matches = []
    for r in name_index.get(target_name, []):
        if str(r.get("season_label", "")).strip().lower() == target_season:
            season_matches.append(r)
    
    row = preferred_row(season_matches)
    
    if row is None and season_year(target_season) == 2025:
        fallback_rows = []
        for r in name_index.get(target_name, []):
            if season_year(r.get("season_label", "")) == 2024:
                fallback_rows.append(r)
        row = preferred_row(fallback_rows)
    
    if row is None:
        print(json.dumps({"error": f"No data found for '{player_name_arg}' in season '{season_arg}'"}))
        sys.exit(1)
    
    player_name_clean = normalize_name(repair_text(row.get("player_name", "")))
    current_year = season_year(row.get("season_label", ""))
    
    all_player_rows = name_index.get(player_name_clean, [])
    prev_rows = [r for r in all_player_rows if season_year(r.get("season_label", "")) == current_year - 1]
    prev_row = preferred_row(prev_rows)
    
    source_row = row
    if current_year == 2025 and prev_row is not None:
        source_row = prev_row
    
    # Use real sklearn ML models (fast with Python 3.12)
    try:
        import sys as _sys
        _gen_dir = os.path.dirname(os.path.abspath(__file__))
        if _gen_dir not in _sys.path:
            _sys.path.insert(0, _gen_dir)
        from ml.predict import AttributeGenerator
        from ml.feature_engineering import engineer_features, detect_position_group
        from ml.season_baselines import load_baselines, apply_baselines
        import pandas as _pd

        generator = AttributeGenerator()
        generator.load_models()

        # Build a DataFrame row for the feature engineering pipeline
        df_row = _pd.DataFrame([source_row])
        engineered = engineer_features(df_row)

        # Fix the train/inference mismatch: pct_* features computed on a single-row
        # DataFrame are always 100% (meaningless). Replace them with correct values
        # derived from the saved full-season population distributions.
        _baselines_path = os.path.join(_gen_dir, "ml", "models", "season_baselines.json")
        _baselines = load_baselines(_baselines_path)
        if _baselines:
            _player_season = str(source_row.get("season_label", season_arg)).strip()
            engineered = apply_baselines(engineered, _baselines, season=_player_season)

        feature_cols = list(open(os.path.join(_gen_dir, "ml", "models", "feature_columns.txt")).read().strip().split("\n"))

        import numpy as _np
        X = _np.zeros((1, len(feature_cols)))
        for i, col in enumerate(feature_cols):
            if col in engineered.columns:
                val = engineered[col].iloc[0]
                if _pd.isna(val):
                    val = 0
                X[0, i] = float(val)
        
        pos_group = detect_position_group(str(source_row.get("position", "SG")))
        attrs = generator.predictor.predict_attributes(X, position_group=pos_group)
        # Remove Overall if present (we compute our own)
        attrs.pop("Overall", None)
        
        # Compute roles from ML attributes
        roles = []
        if attrs.get("Ball Handle", 0) > 60 and attrs.get("Pass Vision", 0) > 55:
            roles.append("Primary Ball Handler")
        if attrs.get("Three-Point Shot", 0) > 65:
            roles.append("Floor Spacer")
        if attrs.get("Driving Dunk", 0) > 60 or attrs.get("Standing Dunk", 0) > 60:
            roles.append("Rim Attacker")
        if attrs.get("Shot IQ", 0) > 65:
            roles.append("Efficient Scorer")
        position = str(source_row.get("position", ""))
        if ("C" in position or "PF" in position) and attrs.get("Interior Defense", 0) > 60:
            roles.append("Rim Protector")
        if not roles:
            roles.append("Core")
        # Compute OVR from ML attributes
        finishing = [attrs.get("Driving Layup", 50), attrs.get("Standing Dunk", 50), attrs.get("Driving Dunk", 50), attrs.get("Close Shot", 50)]
        shooting = [attrs.get("Mid-Range Shot", 50), attrs.get("Three-Point Shot", 50), attrs.get("Free Throw", 50), attrs.get("Shot IQ", 50)]
        playmaking = [attrs.get("Ball Handle", 50), attrs.get("Speed with Ball", 50), attrs.get("Pass Accuracy", 50), attrs.get("Pass IQ", 50), attrs.get("Pass Vision", 50)]
        defense = [attrs.get("Interior Defense", 50), attrs.get("Perimeter Defense", 50), attrs.get("Steal", 50), attrs.get("Block", 50)]
        physical = [attrs.get("Speed", 50), attrs.get("Agility", 50), attrs.get("Strength", 50), attrs.get("Vertical", 50)]
        def avg_vals(vals):
            return sum(vals) / len(vals) if vals else 50
        ovr = int(clamp(
            avg_vals(finishing) * 0.15 +
            avg_vals(shooting) * 0.25 +
            avg_vals(playmaking) * 0.15 +
            avg_vals(defense) * 0.20 +
            avg_vals(physical) * 0.10 +
            attrs.get("Intangibles", 50) * 0.10 +
            attrs.get("Hustle", 50) * 0.05,
            60, 99))
    except Exception as _e:
        ml_result = compute_attributes_formula(source_row, [], roles_dir, rows)
        attrs = ml_result["attributes"]
        roles = ml_result["roles"]
        ovr = ml_result["ovr"]
    
    # Compute tendencies
    tendency_results = compute_tendencies(source_row)
    
    # Compute family scores
    family_scores = compute_attribute_family_averages(attrs)
    family_scores = {k: int(v) for k, v in family_scores.items()}
    
    # Compute badges
    badge_groups = compute_badge_groups(source_row, attrs, tendency_results, family_scores, ovr, badges_txt)
    
    # Stats
    current_snapshot = stat_snapshot(row)
    previous_snapshot = stat_snapshot(prev_row)
    
    career_rows_list = [r for r in all_player_rows if season_year(r.get("season_label", "")) <= current_year]
    career_total_g = 0.0
    career_acc = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "stl": 0.0, "blk": 0.0, "fgPct": 0.0, "fg3Pct": 0.0}
    for cr in career_rows_list:
        s = stat_snapshot(cr)
        g = max(float(s.get("gp", 0)), 1.0)
        career_total_g += g
        for k in career_acc:
            career_acc[k] += float(s.get(k, 0.0)) * g
    career_snapshot = {
        k: round((career_acc[k] / career_total_g) if career_total_g > 0 else 0.0, 3 if "Pct" in k else 1)
        for k in career_acc
    }
    career_snapshot["gp"] = int(round(career_total_g))
    
    # Strengths/weaknesses
    sorted_attrs = sorted(attrs.items(), key=lambda kv: kv[1], reverse=True)
    strengths = [k for k, _ in sorted_attrs[:6]]
    weaknesses = [k for k, _ in sorted(attrs.items(), key=lambda kv: kv[1])[:6]]
    
    # Attribute groups
    attribute_group_order = [
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
    
    attribute_groups = {}
    for family_name, names in attribute_group_order:
        attribute_groups[family_name] = [
            {"key": normalize_key(n), "name": n, "value": int(attrs.get(n, 0))}
            for n in names if n in attrs
        ]
    
    # Tendency groups
    tendency_aliases = {
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
        "driving_dribble_hesitation": ["drive_hesitation"], "driving_in_and_out": ["drive_in_out"],
        "attack_strong_on_drive": ["attack_strong_drive"], "setup_with_sizeup": ["set_up_size_up"],
        "setup_with_hesitation": ["set_up_hesitation"], "dish_to_open_man": ["dish"],
        "iso_vs_elite_defender": ["iso_vs_elite"], "iso_vs_good_defender": ["iso_vs_good"],
        "iso_vs_average_defender": ["iso_vs_average"], "iso_vs_poor_defender": ["iso_vs_poor"],
        "post_shimmy_shot": ["post_shimmy"], "post_aggressive_backdown": ["post_aggressive_back_down"],
        "post_step_back_shot": ["post_step_back"], "post_up_and_under": ["post_up_under", "post_up_&_under"],
        "post_drop_step": ["post_drop_step"], "post_hop_step": ["post_hop_shot"],
        "block_shot": ["block"], "on_ball_steal": ["on_ball_steal"],
    }
    
    tendency_group_order = [
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
        for alias in tendency_aliases.get(norm, []):
            t = tendency_by_norm.get(alias)
            if t:
                return t
        return None
    
    tendency_groups = {}
    for group_name, names in tendency_group_order:
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
        tendency_groups[group_name] = grp_rows
    
    top_tendencies = sorted(tendency_results, key=lambda x: x.final, reverse=True)
    play_style = [t.name for t in top_tendencies[:3]]
    
    # Draft info
    draft_year_raw = first_non_empty(row.get("draft_year"), row.get("draft_season"))
    draft_round_raw = first_non_empty(row.get("draft_round"), "")
    draft_number_raw = first_non_empty(row.get("draft_number"), "")
    if draft_year_raw and str(draft_year_raw).strip().lower() not in ("undrafted", "", "none", "nan"):
        draft_str = str(draft_year_raw).strip()
        if draft_round_raw and str(draft_round_raw).strip().lower() not in ("undrafted", "", "none", "nan"):
            draft_str += f" R{draft_round_raw}"
        if draft_number_raw and str(draft_number_raw).strip().lower() not in ("undrafted", "", "none", "nan"):
            draft_str += f" Pick {draft_number_raw}"
        draft_year_num = int(sf(draft_year_raw, current_year))
    else:
        draft_str = "Undrafted" if str(draft_year_raw).strip().lower() == "undrafted" else "NA"
        draft_year_num = current_year
    years_pro = max(0, current_year - draft_year_num) if current_year > 0 else 0
    
    height_display = first_non_empty(row.get("height"), "") or format_height(row)
    weight_val = first_non_empty(row.get("weight"), row.get("weight_lbs"), row.get("player_info_wt")) or "NA"
    school_val = first_non_empty(row.get("college"), row.get("school"), row.get("draft_college"),
                                 row.get("player_info_colleges")) or "NA"
    country_val = first_non_empty(row.get("country"), "") or ""
    
    photo_url = build_headshot_url(row)
    team_logo_url = build_team_logo_url(row)
    
    action_photo_path = find_action_photo(row, project_root)
    action_photo_url = ""
    if action_photo_path:
        action_photo_url = "player-photo://" + quote(os.path.basename(action_photo_path), safe="")
    
    nba_pid = str(row.get("player_id", "")).strip()
    
    payload = {
        "info": {
            "name": repair_text(row.get("player_name", "")),
            "team": str(row.get("team_abbr", "")),
            "position": str(row.get("position", row.get("pos", ""))),
            "season": str(row.get("season_label", "")),
            "age": float(row.get("age", 0) or 0),
            "height": height_display,
            "weight": weight_val,
            "yearsPro": int(sf(row.get("experience", years_pro))),
            "draft": draft_str,
            "school": school_val,
            "country": country_val,
            "photoUrl": photo_url,
            "teamLogoUrl": team_logo_url,
            "actionPhotoUrl": action_photo_url,
            "nbaPlayerId": nba_pid,
        },
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
        "playStylePriorities": play_style,
        "statBlocks": {"current": current_snapshot, "previous": previous_snapshot, "career": career_snapshot},
    }
    
    print(json.dumps({"ok": True, "player": player_name_arg, "profile": payload}))

if __name__ == "__main__":
    main()
