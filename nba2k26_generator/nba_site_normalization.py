import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


def _to_float(value: Any, default: float = 0.0) -> float:
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


def _pct_to_100(value: float) -> float:
    # NBA endpoints sometimes emit 0-1 ratios and sometimes 0-100 percentages.
    return value * 100.0 if 0.0 <= value <= 1.0 else value


def _pct_to_ratio(value: float) -> float:
    if value > 1.0:
        return value / 100.0
    if value < 0.0:
        return 0.0
    return value


def _safe_div(n: float, d: float, default: float = 0.0) -> float:
    return n / d if d and abs(d) > 1e-9 else default


def _infer_position(height_in: float, ast_pg: float, blk_pct_100: float) -> str:
    # Heuristic fallback when explicit position is unavailable in scraped tables.
    if height_in >= 82.0:
        return 'C'
    if height_in >= 80.0:
        return 'PF' if ast_pg < 4.5 else 'SF'
    if height_in >= 78.0:
        return 'SF' if blk_pct_100 >= 1.8 else 'SG'
    if ast_pg >= 6.0:
        return 'PG'
    return 'SG'


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def _is_rate_column(col: str) -> bool:
    c = col.upper()
    return ('PCT' in c) or ('RATE' in c) or ('RATIO' in c) or ('AVG' in c)


def _is_sum_column(col: str) -> bool:
    c = col.upper()
    tokens = ('FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'PTS', 'AST', 'POSS', 'DRIVES', 'DEFLECTIONS', 'CONTESTED')
    return any(t in c for t in tokens)


def _aggregate_rows(rows: List[Dict[str, Any]], group_key: str = 'PLAYER_ID') -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        k = str(r.get(group_key, '')).strip()
        if not k:
            continue
        groups[k].append(r)

    out: List[Dict[str, Any]] = []
    for key, items in groups.items():
        if len(items) == 1:
            out.append(items[0])
            continue

        cols = set()
        for it in items:
            cols.update(it.keys())

        merged: Dict[str, Any] = {}
        for c in cols:
            vals = [(it.get(c) or '').strip() for it in items if (it.get(c) or '').strip()]
            if not vals:
                merged[c] = ''
                continue

            if _is_rate_column(c):
                weights = []
                for it in items:
                    w = _to_float(it.get('POSS'), 0.0)
                    if w <= 0.0:
                        w = _to_float(it.get('GP'), 0.0)
                    if w <= 0.0:
                        w = 1.0
                    weights.append(w)
                nums = [_to_float(it.get(c), 0.0) for it in items]
                total_w = sum(weights)
                merged[c] = str(sum(n * w for n, w in zip(nums, weights)) / total_w) if total_w > 0 else str(sum(nums) / len(nums))
            elif _is_sum_column(c):
                merged[c] = str(sum(_to_float(v, 0.0) for v in vals))
            else:
                merged[c] = vals[0]

        merged[group_key] = key
        out.append(merged)

    return out


def _index_by_player_id(rows: List[Dict[str, Any]], pid_col: str = 'PLAYER_ID') -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        pid = str(r.get(pid_col, '')).strip()
        if pid:
            out[pid] = r
    return out


def _pivot_shot_dashboard(rows: List[Dict[str, Any]], category_col: str, pid_col: str = 'PLAYER_ID') -> Dict[str, Dict[str, Any]]:
    """Pivot a shot-dashboard CSV (multiple rows per player, one per category) into one flat row per player.

    Each value column gets a prefix derived from the category value, e.g.:
      DRIBBLE_RANGE='0 Dribbles', FG_PCT=0.45  ->  '0_drib_FG_PCT': 0.45
    """
    # Normalise category labels to short prefixes.
    _CATEGORY_PREFIXES = {
        # Dribble ranges
        '0 Dribbles': '0_drib',
        '1 Dribble': '1_drib',
        '2 Dribbles': '2_drib',
        '3-6 Dribbles': '3_6_drib',
        '7+ Dribbles': '7p_drib',
        # Closest defender distance
        '0-2 Feet - Very Tight': 'very_tight',
        '2-4 Feet - Tight': 'tight',
        '4-6 Feet - Open': 'open',
        '6+ Feet - Wide Open': 'wide_open',
        # Touch time
        'Touch < 2 Seconds': 'touch_lt2',
        'Touch 2-6 Seconds': 'touch_2_6',
        'Touch 6+ Seconds': 'touch_6p',
    }

    skip_cols = {pid_col, category_col, 'PLAYER_NAME_LAST_FIRST', 'PLAYER_NAME', 'SORT_ORDER', 'GP', 'G', 'SEASON', 'SEASON_TYPE'}
    out: Dict[str, Dict[str, Any]] = {}

    for r in rows:
        pid = str(r.get(pid_col, '')).strip()
        if not pid:
            continue
        cat_raw = str(r.get(category_col, '')).strip()
        prefix = _CATEGORY_PREFIXES.get(cat_raw, cat_raw.replace(' ', '_').replace('+', 'p').replace('-', '_').lower())
        if pid not in out:
            out[pid] = {pid_col: pid, 'GP': r.get('GP', ''), 'PLAYER_NAME': r.get('PLAYER_NAME_LAST_FIRST', r.get('PLAYER_NAME', ''))}
        target = out[pid]
        for k, v in r.items():
            if k in skip_cols:
                continue
            target[f'{prefix}_{k}'] = v

    return out


def load_nba_site_rows(data_dir: str) -> List[Dict[str, Any]]:
    """Load NBA Site CSVs and produce one canonical row per PLAYER_ID.

    This is a starter normalization layer intended to feed existing formula code.
    Auto-detects the season tag from filenames present in the directory.
    """
    base = Path(data_dir)
    files = sorted(base.glob('*.csv'))
    if not files:
        raise FileNotFoundError(f'No CSV files found in: {data_dir}')

    # Auto-detect season tag from traditional file (e.g. "2025-26")
    import re as _re
    season_tag = None
    for f in files:
        m = _re.search(r'player_traditional_(\d{4}-\d{2})_regular_season\.csv', f.name)
        if m:
            season_tag = m.group(1)
            break
    if season_tag is None:
        raise FileNotFoundError(f'No player_traditional_*_regular_season.csv found in: {data_dir}')

    def sf(name: str) -> str:
        """Season filename helper — insert detected season tag."""
        return name.replace('SEASON', season_tag)

    # Base table
    traditional_path = base / sf('player_traditional_SEASON_regular_season.csv')
    if not traditional_path.exists():
        raise FileNotFoundError(f'Base file not found: {traditional_path.name}')

    traditional_rows = _read_csv(traditional_path)
    traditional_idx = _index_by_player_id(traditional_rows)

    # Merge in selected high-value tables
    merge_files = [
        sf('player_advanced_SEASON_regular_season.csv'),
        sf('player_usage_SEASON_regular_season.csv'),
        sf('player_scoring_SEASON_regular_season.csv'),
        sf('player_shooting_by_zone_SEASON_regular_season.csv'),
        sf('player_tracking_speed_distance_SEASON_regular_season.csv'),
        sf('player_tracking_drives_SEASON_regular_season.csv'),
        sf('player_tracking_pullup_SEASON_regular_season.csv'),
        sf('player_tracking_catch_shoot_SEASON_regular_season.csv'),
        sf('player_tracking_passing_SEASON_regular_season.csv'),
        sf('player_tracking_touches_SEASON_regular_season.csv'),
        sf('player_tracking_tracking_post_ups_SEASON_regular_season.csv'),
        sf('player_defense_SEASON_regular_season.csv'),
        sf('player_hustle_SEASON_regular_season.csv'),
        sf('player_defense_dash_overall_SEASON_regular_season.csv'),
        sf('player_defense_dash_3pt_SEASON_regular_season.csv'),
        sf('player_defense_dash_2pt_SEASON_regular_season.csv'),
        sf('player_defense_dash_lt6_SEASON_regular_season.csv'),
        sf('player_bio_SEASON_regular_season.csv'),
        sf('player_playtype_isolation_SEASON_regular_season.csv'),
        sf('player_playtype_off_screen_SEASON_regular_season.csv'),
        sf('player_playtype_playtype_post_up_SEASON_regular_season.csv'),
        sf('player_playtype_spot_up_SEASON_regular_season.csv'),
        sf('player_playtype_hand_off_SEASON_regular_season.csv'),
        sf('player_playtype_ball_handler_SEASON_regular_season.csv'),
        sf('player_playtype_roll_man_SEASON_regular_season.csv'),
        sf('player_playtype_cut_SEASON_regular_season.csv'),
        sf('player_tracking_offensive_rebounding_SEASON_regular_season.csv'),
        sf('player_tracking_defensive_rebounding_SEASON_regular_season.csv'),
        sf('player_tracking_paint_touch_SEASON_regular_season.csv'),
        sf('player_box_outs_SEASON_regular_season.csv'),
        sf('player_tracking_shooting_efficiency_SEASON_regular_season.csv'),
        sf('player_misc_SEASON_regular_season.csv'),
        sf('player_playtype_transition_SEASON_regular_season.csv'),
        sf('player_tracking_elbow_touch_SEASON_regular_season.csv'),
        sf('player_clutch_traditional_SEASON_regular_season.csv'),
        sf('player_clutch_advanced_SEASON_regular_season.csv'),
    ]

    merged_idx: Dict[str, Dict[str, Any]] = {pid: dict(row) for pid, row in traditional_idx.items()}

    for fname in merge_files:
        fp = base / fname
        if not fp.exists():
            continue
        rows = _read_csv(fp)
        pid_col = 'PLAYER_ID'
        if fname.startswith('player_defense_dash_'):
            pid_col = 'CLOSE_DEF_PERSON_ID'
        # Some files have repeated player rows; aggregate first.
        rows = _aggregate_rows(rows, group_key=pid_col)
        idx = _index_by_player_id(rows, pid_col=pid_col)
        for pid, target in merged_idx.items():
            src = idx.get(pid)
            if not src:
                continue
            for k, v in src.items():
                if k in ('PLAYER_ID', pid_col):
                    continue
                target[f'{fname}:{k}'] = v

    # ── Pivot shot dashboard files (multiple rows per player) ──
    _PIVOT_FILES = [
        (sf('player_shot_dashboard_dribble_SEASON_regular_season.csv'), 'DRIBBLE_RANGE'),
        (sf('player_shot_dashboard_closest_defender_SEASON_regular_season.csv'), 'CLOSE_DEF_DIST_RANGE'),
        (sf('player_shot_dashboard_touch_time_SEASON_regular_season.csv'), 'TOUCH_TIME_RANGE'),
    ]
    for pivot_fname, cat_col in _PIVOT_FILES:
        fp = base / pivot_fname
        if not fp.exists():
            continue
        raw_rows = _read_csv(fp)
        pivoted = _pivot_shot_dashboard(raw_rows, cat_col)
        for pid, target in merged_idx.items():
            src = pivoted.get(pid)
            if not src:
                continue
            for k, v in src.items():
                if k in ('PLAYER_ID', 'GP', 'PLAYER_NAME'):
                    continue
                target[f'{pivot_fname}:{k}'] = v

    # Build canonical + legacy-compatible keys expected by generator formulas.
    out: List[Dict[str, Any]] = []
    for pid, row in merged_idx.items():
        def g(file_name: str, col: str, default: float = 0.0) -> float:
            # Auto-apply season tag: accept either SEASON placeholder or already-substituted names.
            resolved = file_name.replace('SEASON', season_tag) if 'SEASON' in file_name else file_name
            return _to_float(row.get(f'{resolved}:{col}'), default)

        zone_restricted = g('player_shooting_by_zone_SEASON_regular_season.csv', 'restricted_area_fga')
        zone_paint_non_ra = g('player_shooting_by_zone_SEASON_regular_season.csv', 'in_the_paint_non_ra_fga')
        zone_mid = g('player_shooting_by_zone_SEASON_regular_season.csv', 'mid_range_fga')
        zone_corner_l = g('player_shooting_by_zone_SEASON_regular_season.csv', 'left_corner_3_fga')
        zone_corner_r = g('player_shooting_by_zone_SEASON_regular_season.csv', 'right_corner_3_fga')
        zone_above_break = g('player_shooting_by_zone_SEASON_regular_season.csv', 'above_the_break_3_fga')
        zone_backcourt = g('player_shooting_by_zone_SEASON_regular_season.csv', 'backcourt_fga')
        games = _to_float(row.get('GP'))
        mpg = _to_float(row.get('MIN'))
        fga_pg = _to_float(row.get('FGA'))
        fg3a_pg = _to_float(row.get('FG3A'))
        fgm_pg = _to_float(row.get('FGM'))
        fg3m_pg = _to_float(row.get('FG3M'))
        fta_pg = _to_float(row.get('FTA'))
        ftm_pg = _to_float(row.get('FTM'))
        ast_pg = _to_float(row.get('AST'))
        stl_pg = _to_float(row.get('STL'))
        blk_pg = _to_float(row.get('BLK'))
        pf_pg = _to_float(row.get('PF'))

        minutes_total = games * mpg
        pace_poss = g('player_advanced_SEASON_regular_season.csv', 'POSS')
        poss_total = max(1.0, pace_poss)

        # Tracking-first playmaking proxies (passing/touches/drives).
        passes_made_total = g('player_tracking_passing_SEASON_regular_season.csv', 'PASSES_MADE')
        passes_received_total = g('player_tracking_passing_SEASON_regular_season.csv', 'PASSES_RECEIVED')
        potential_ast_total = g('player_tracking_passing_SEASON_regular_season.csv', 'POTENTIAL_AST')
        ast_adj_total = g('player_tracking_passing_SEASON_regular_season.csv', 'AST_ADJ')
        secondary_ast_total = g('player_tracking_passing_SEASON_regular_season.csv', 'SECONDARY_AST')
        ft_ast_total = g('player_tracking_passing_SEASON_regular_season.csv', 'FT_AST')
        ast_to_pass_pct = _pct_to_ratio(g('player_tracking_passing_SEASON_regular_season.csv', 'AST_TO_PASS_PCT'))
        ast_to_pass_pct_adj = _pct_to_ratio(g('player_tracking_passing_SEASON_regular_season.csv', 'AST_TO_PASS_PCT_ADJ'))

        touches_total = g('player_tracking_touches_SEASON_regular_season.csv', 'TOUCHES')
        front_ct_touches_total = g('player_tracking_touches_SEASON_regular_season.csv', 'FRONT_CT_TOUCHES')
        time_of_poss_total = g('player_tracking_touches_SEASON_regular_season.csv', 'TIME_OF_POSS')
        avg_sec_per_touch = g('player_tracking_touches_SEASON_regular_season.csv', 'AVG_SEC_PER_TOUCH')
        avg_drib_per_touch = g('player_tracking_touches_SEASON_regular_season.csv', 'AVG_DRIB_PER_TOUCH')
        pts_per_touch = g('player_tracking_touches_SEASON_regular_season.csv', 'PTS_PER_TOUCH')

        drives_total = g('player_tracking_drives_SEASON_regular_season.csv', 'DRIVES')
        drive_passes_total = g('player_tracking_drives_SEASON_regular_season.csv', 'DRIVE_PASSES')
        drive_ast_total = g('player_tracking_drives_SEASON_regular_season.csv', 'DRIVE_AST')
        drive_passes_pct = _pct_to_ratio(g('player_tracking_drives_SEASON_regular_season.csv', 'DRIVE_PASSES_PCT'))
        drive_fg_pct = _pct_to_ratio(g('player_tracking_drives_SEASON_regular_season.csv', 'DRIVE_FG_PCT'))
        drive_tov_pct = _pct_to_ratio(g('player_tracking_drives_SEASON_regular_season.csv', 'DRIVE_TOV_PCT'))

        tracking_avg_speed = g('player_tracking_speed_distance_SEASON_regular_season.csv', 'AVG_SPEED')
        tracking_avg_speed_off = g('player_tracking_speed_distance_SEASON_regular_season.csv', 'AVG_SPEED_OFF')
        tracking_avg_speed_def = g('player_tracking_speed_distance_SEASON_regular_season.csv', 'AVG_SPEED_DEF')
        tracking_dist_miles = g('player_tracking_speed_distance_SEASON_regular_season.csv', 'DIST_MILES')
        tracking_dist_miles_off = g('player_tracking_speed_distance_SEASON_regular_season.csv', 'DIST_MILES_OFF')
        tracking_dist_miles_def = g('player_tracking_speed_distance_SEASON_regular_season.csv', 'DIST_MILES_DEF')
        tracking_dist_feet = g('player_tracking_speed_distance_SEASON_regular_season.csv', 'DIST_FEET')

        contested_shots_total = g('player_hustle_SEASON_regular_season.csv', 'CONTESTED_SHOTS')
        contested_2pt_total = g('player_hustle_SEASON_regular_season.csv', 'CONTESTED_SHOTS_2PT')
        contested_3pt_total = g('player_hustle_SEASON_regular_season.csv', 'CONTESTED_SHOTS_3PT')
        deflections_total = g('player_hustle_SEASON_regular_season.csv', 'DEFLECTIONS')
        charges_drawn_total = g('player_hustle_SEASON_regular_season.csv', 'CHARGES_DRAWN')
        loose_balls_recovered_def_total = g('player_hustle_SEASON_regular_season.csv', 'LOOSE_BALLS_RECOVERED_DEF')

        dash_overall_dfg = _pct_to_ratio(g('player_defense_dash_overall_SEASON_regular_season.csv', 'D_FG_PCT'))
        dash_overall_nfg = _pct_to_ratio(g('player_defense_dash_overall_SEASON_regular_season.csv', 'NORMAL_FG_PCT'))
        dash_overall_stop_delta = dash_overall_nfg - dash_overall_dfg
        dash_overall_plusminus = g('player_defense_dash_overall_SEASON_regular_season.csv', 'PCT_PLUSMINUS')

        dash_3pt_dfg = _pct_to_ratio(g('player_defense_dash_3pt_SEASON_regular_season.csv', 'FG3_PCT'))
        dash_3pt_nfg = _pct_to_ratio(g('player_defense_dash_3pt_SEASON_regular_season.csv', 'NS_FG3_PCT'))
        dash_3pt_stop_delta = dash_3pt_nfg - dash_3pt_dfg
        dash_3pt_plusminus = g('player_defense_dash_3pt_SEASON_regular_season.csv', 'PLUSMINUS')

        dash_2pt_dfg = _pct_to_ratio(g('player_defense_dash_2pt_SEASON_regular_season.csv', 'FG2_PCT'))
        dash_2pt_nfg = _pct_to_ratio(g('player_defense_dash_2pt_SEASON_regular_season.csv', 'NS_FG2_PCT'))
        dash_2pt_stop_delta = dash_2pt_nfg - dash_2pt_dfg
        dash_2pt_plusminus = g('player_defense_dash_2pt_SEASON_regular_season.csv', 'PLUSMINUS')

        dash_lt6_dfg = _pct_to_ratio(g('player_defense_dash_lt6_SEASON_regular_season.csv', 'LT_06_PCT'))
        dash_lt6_nfg = _pct_to_ratio(g('player_defense_dash_lt6_SEASON_regular_season.csv', 'NS_LT_06_PCT'))
        dash_lt6_stop_delta = dash_lt6_nfg - dash_lt6_dfg
        dash_lt6_plusminus = g('player_defense_dash_lt6_SEASON_regular_season.csv', 'PLUSMINUS')

        passes_made_pg = _safe_div(passes_made_total, max(1.0, games), 0.0)

        # Rebounding tracking data.
        oreb_contest_total = g('player_tracking_offensive_rebounding_SEASON_regular_season.csv', 'OREB_CONTEST')
        oreb_chances_total = g('player_tracking_offensive_rebounding_SEASON_regular_season.csv', 'OREB_CHANCES')
        oreb_chance_pct = _pct_to_ratio(g('player_tracking_offensive_rebounding_SEASON_regular_season.csv', 'OREB_CHANCE_PCT'))
        oreb_chance_pct_adj = _pct_to_ratio(g('player_tracking_offensive_rebounding_SEASON_regular_season.csv', 'OREB_CHANCE_PCT_ADJ'))
        dreb_contest_total = g('player_tracking_defensive_rebounding_SEASON_regular_season.csv', 'DREB_CONTEST')
        dreb_chances_total = g('player_tracking_defensive_rebounding_SEASON_regular_season.csv', 'DREB_CHANCES')
        dreb_chance_pct = _pct_to_ratio(g('player_tracking_defensive_rebounding_SEASON_regular_season.csv', 'DREB_CHANCE_PCT'))
        dreb_chance_pct_adj = _pct_to_ratio(g('player_tracking_defensive_rebounding_SEASON_regular_season.csv', 'DREB_CHANCE_PCT_ADJ'))

        oreb_contest_pg = _safe_div(oreb_contest_total, max(1.0, games), 0.0)
        oreb_chances_pg = _safe_div(oreb_chances_total, max(1.0, games), 0.0)
        dreb_contest_pg = _safe_div(dreb_contest_total, max(1.0, games), 0.0)
        dreb_chances_pg = _safe_div(dreb_chances_total, max(1.0, games), 0.0)

        # Box-out data.
        box_outs_off_total = g('player_box_outs_SEASON_regular_season.csv', 'OFF_BOXOUTS')
        box_outs_def_total = g('player_box_outs_SEASON_regular_season.csv', 'DEF_BOXOUTS')
        box_outs_total = g('player_box_outs_SEASON_regular_season.csv', 'BOX_OUTS')
        box_outs_pg = _safe_div(box_outs_total, max(1.0, games), 0.0)
        box_outs_def_pg = _safe_div(box_outs_def_total, max(1.0, games), 0.0)
        box_outs_off_pg = _safe_div(box_outs_off_total, max(1.0, games), 0.0)

        # Playtype cut and roll-man data (finishing indicators).
        cut_fg_pct = _pct_to_ratio(g('player_playtype_cut_SEASON_regular_season.csv', 'FG_PCT'))
        cut_poss_pct = _pct_to_ratio(g('player_playtype_cut_SEASON_regular_season.csv', 'POSS_PCT'))
        roll_man_fg_pct = _pct_to_ratio(g('player_playtype_roll_man_SEASON_regular_season.csv', 'FG_PCT'))
        roll_man_poss_pct = _pct_to_ratio(g('player_playtype_roll_man_SEASON_regular_season.csv', 'POSS_PCT'))

        # Paint touch data.
        paint_touch_fg_pct = _pct_to_ratio(g('player_tracking_paint_touch_SEASON_regular_season.csv', 'PAINT_TOUCH_FG_PCT'))
        paint_touches_total = g('player_tracking_paint_touch_SEASON_regular_season.csv', 'PAINT_TOUCHES')
        paint_touches_pg = _safe_div(paint_touches_total, max(1.0, games), 0.0)

        # Catch-and-shoot per-game data.
        catch_shoot_fg3_pct = _pct_to_ratio(g('player_tracking_catch_shoot_SEASON_regular_season.csv', 'CATCH_SHOOT_FG3_PCT'))
        catch_shoot_efg_pct = _pct_to_ratio(g('player_tracking_catch_shoot_SEASON_regular_season.csv', 'CATCH_SHOOT_EFG_PCT'))
        catch_shoot_fg3a_total = g('player_tracking_catch_shoot_SEASON_regular_season.csv', 'CATCH_SHOOT_FG3A')
        catch_shoot_fg3a_pg = _safe_div(catch_shoot_fg3a_total, max(1.0, games), 0.0)
        passes_received_pg = _safe_div(passes_received_total, max(1.0, games), 0.0)
        potential_ast_pg = _safe_div(potential_ast_total, max(1.0, games), 0.0)
        ast_adj_pg = _safe_div(ast_adj_total, max(1.0, games), 0.0)
        secondary_ast_pg = _safe_div(secondary_ast_total, max(1.0, games), 0.0)
        ft_ast_pg = _safe_div(ft_ast_total, max(1.0, games), 0.0)

        touches_pg = _safe_div(touches_total, max(1.0, games), 0.0)
        front_ct_touches_pg = _safe_div(front_ct_touches_total, max(1.0, games), 0.0)
        time_of_poss_pg = _safe_div(time_of_poss_total, max(1.0, games), 0.0)

        drives_pg = _safe_div(drives_total, max(1.0, games), 0.0)
        drive_passes_pg = _safe_div(drive_passes_total, max(1.0, games), 0.0)
        drive_ast_pg = _safe_div(drive_ast_total, max(1.0, games), 0.0)
        drive_pass_rate = _safe_div(drive_passes_total, max(1.0, drives_total), 0.0)
        drive_ast_rate = _safe_div(drive_ast_total, max(1.0, drive_passes_total), 0.0)

        contested_shots_pg = _safe_div(contested_shots_total, max(1.0, games), 0.0)
        contested_2pt_pg = _safe_div(contested_2pt_total, max(1.0, games), 0.0)
        contested_3pt_pg = _safe_div(contested_3pt_total, max(1.0, games), 0.0)
        deflections_pg = _safe_div(deflections_total, max(1.0, games), 0.0)
        charges_drawn_pg = _safe_div(charges_drawn_total, max(1.0, games), 0.0)
        loose_balls_recovered_def_pg = _safe_div(loose_balls_recovered_def_total, max(1.0, games), 0.0)
        tracking_dist_miles_pg = _safe_div(tracking_dist_miles, max(1.0, games), 0.0)
        tracking_dist_miles_off_pg = _safe_div(tracking_dist_miles_off, max(1.0, games), 0.0)
        tracking_dist_miles_def_pg = _safe_div(tracking_dist_miles_def, max(1.0, games), 0.0)
        tracking_dist_miles_per_min = _safe_div(tracking_dist_miles, max(1.0, minutes_total), 0.0)

        usg_pct = _pct_to_100(g('player_advanced_SEASON_regular_season.csv', 'USG_PCT', _to_float(row.get(sf('player_usage_SEASON_regular_season.csv') + ':USG_PCT'))))
        ast_pct = _pct_to_100(g('player_advanced_SEASON_regular_season.csv', 'AST_PCT'))
        tov_pct = _pct_to_100(g('player_advanced_SEASON_regular_season.csv', 'E_TOV_PCT', g('player_usage_SEASON_regular_season.csv', 'PCT_TOV')))
        orb_pct = _pct_to_100(g('player_advanced_SEASON_regular_season.csv', 'OREB_PCT'))
        drb_pct = _pct_to_100(g('player_advanced_SEASON_regular_season.csv', 'DREB_PCT'))
        stl_pct = _safe_div(stl_pg * games * 100.0, poss_total, 0.0)
        blk_pct = _safe_div(blk_pg * games * 100.0, poss_total, 0.0)

        height_in = g('player_bio_SEASON_regular_season.csv', 'PLAYER_HEIGHT_INCHES')
        if height_in <= 0.0:
            height_in = 78.0
        weight_lbs = g('player_bio_SEASON_regular_season.csv', 'PLAYER_WEIGHT', 220.0)

        # ── Shot dashboard: dribble breakdown ──
        # 0 dribbles = pure catch-and-shoot, 7+ = off-dribble creation
        drib_file = sf('player_shot_dashboard_dribble_SEASON_regular_season.csv')
        zero_drib_fga = _to_float(row.get(f'{drib_file}:0_drib_FGA'))
        zero_drib_fg_pct = _pct_to_ratio(_to_float(row.get(f'{drib_file}:0_drib_FG_PCT')))
        zero_drib_fg3_pct = _pct_to_ratio(_to_float(row.get(f'{drib_file}:0_drib_FG3_PCT')))
        zero_drib_freq = _pct_to_ratio(_to_float(row.get(f'{drib_file}:0_drib_FGA_FREQUENCY')))
        one_drib_fga = _to_float(row.get(f'{drib_file}:1_drib_FGA'))
        three_six_drib_fga = _to_float(row.get(f'{drib_file}:3_6_drib_FGA'))
        seven_p_drib_fga = _to_float(row.get(f'{drib_file}:7p_drib_FGA'))
        seven_p_drib_fg_pct = _pct_to_ratio(_to_float(row.get(f'{drib_file}:7p_drib_FG_PCT')))
        seven_p_drib_freq = _pct_to_ratio(_to_float(row.get(f'{drib_file}:7p_drib_FGA_FREQUENCY')))
        total_drib_fga = max(1.0, zero_drib_fga + one_drib_fga + three_six_drib_fga + seven_p_drib_fga + _to_float(row.get(f'{drib_file}:2_drib_FGA')))
        off_dribble_freq = _safe_div(three_six_drib_fga + seven_p_drib_fga, total_drib_fga, 0.0)

        # ── Shot dashboard: closest defender distance ──
        def_file = sf('player_shot_dashboard_closest_defender_SEASON_regular_season.csv')
        very_tight_fg_pct = _pct_to_ratio(_to_float(row.get(f'{def_file}:very_tight_FG_PCT')))
        very_tight_freq = _pct_to_ratio(_to_float(row.get(f'{def_file}:very_tight_FGA_FREQUENCY')))
        very_tight_fga = _to_float(row.get(f'{def_file}:very_tight_FGA'))
        tight_fg_pct = _pct_to_ratio(_to_float(row.get(f'{def_file}:tight_FG_PCT')))
        tight_freq = _pct_to_ratio(_to_float(row.get(f'{def_file}:tight_FGA_FREQUENCY')))
        tight_fga = _to_float(row.get(f'{def_file}:tight_FGA'))
        open_fg_pct = _pct_to_ratio(_to_float(row.get(f'{def_file}:open_FG_PCT')))
        open_freq = _pct_to_ratio(_to_float(row.get(f'{def_file}:open_FGA_FREQUENCY')))
        wide_open_fg_pct = _pct_to_ratio(_to_float(row.get(f'{def_file}:wide_open_FG_PCT')))
        wide_open_freq = _pct_to_ratio(_to_float(row.get(f'{def_file}:wide_open_FGA_FREQUENCY')))
        contested_freq = very_tight_freq + tight_freq  # shots with defender <4ft
        contested_fga = very_tight_fga + tight_fga
        # Weighted contested FG% (very tight + tight)
        contested_fg_pct = _safe_div(
            very_tight_fg_pct * very_tight_fga + tight_fg_pct * tight_fga,
            max(1.0, contested_fga), 0.0
        )
        open_total_fg_pct = _safe_div(
            open_fg_pct * _to_float(row.get(f'{def_file}:open_FGA')) + wide_open_fg_pct * _to_float(row.get(f'{def_file}:wide_open_FGA')),
            max(1.0, _to_float(row.get(f'{def_file}:open_FGA')) + _to_float(row.get(f'{def_file}:wide_open_FGA'))), 0.0
        )
        # Contested shot-making delta: how much worse the player is contested vs open
        # Positive = maintains efficiency under pressure
        contested_delta = contested_fg_pct - open_total_fg_pct if (contested_fga >= 10 and open_total_fg_pct > 0) else 0.0

        # ── Shot dashboard: touch time breakdown ──
        tt_file = sf('player_shot_dashboard_touch_time_SEASON_regular_season.csv')
        touch_lt2_freq = _pct_to_ratio(_to_float(row.get(f'{tt_file}:touch_lt2_FGA_FREQUENCY')))
        touch_lt2_fg_pct = _pct_to_ratio(_to_float(row.get(f'{tt_file}:touch_lt2_FG_PCT')))
        touch_lt2_efg = _pct_to_ratio(_to_float(row.get(f'{tt_file}:touch_lt2_EFG_PCT')))
        touch_6p_freq = _pct_to_ratio(_to_float(row.get(f'{tt_file}:touch_6p_FGA_FREQUENCY')))
        touch_6p_fg_pct = _pct_to_ratio(_to_float(row.get(f'{tt_file}:touch_6p_FG_PCT')))

        # ── Transition playtype data ──
        trans_file = 'player_playtype_transition_SEASON_regular_season.csv'
        transition_poss_pct = _pct_to_ratio(g(trans_file, 'POSS_PCT'))
        transition_ppp = g(trans_file, 'PPP')
        transition_fg_pct = _pct_to_ratio(g(trans_file, 'FG_PCT'))
        transition_score_pct = _pct_to_ratio(g(trans_file, 'SCORE_POSS_PCT'))
        transition_poss = g(trans_file, 'POSS')
        transition_percentile = g(trans_file, 'PERCENTILE')

        # ── Misc data (paint pts, fastbreak pts, 2nd chance, blocks against, fouls drawn) ──
        misc_file = 'player_misc_SEASON_regular_season.csv'
        misc_pts_paint = g(misc_file, 'PTS_PAINT')
        misc_pts_fb = g(misc_file, 'PTS_FB')
        misc_pts_2nd_chance = g(misc_file, 'PTS_2ND_CHANCE')
        misc_blka = g(misc_file, 'BLKA')
        misc_pfd = g(misc_file, 'PFD')
        misc_pts_paint_pg = _safe_div(misc_pts_paint, max(1.0, games), 0.0)
        misc_pts_fb_pg = _safe_div(misc_pts_fb, max(1.0, games), 0.0)
        misc_pts_2nd_chance_pg = _safe_div(misc_pts_2nd_chance, max(1.0, games), 0.0)
        misc_blka_pg = _safe_div(misc_blka, max(1.0, games), 0.0)
        misc_pfd_pg = _safe_div(misc_pfd, max(1.0, games), 0.0)

        # ── Elbow touch data ──
        elbow_file = 'player_tracking_elbow_touch_SEASON_regular_season.csv'
        elbow_touches_total = g(elbow_file, 'ELBOW_TOUCHES')
        elbow_touch_fg_pct = _pct_to_ratio(g(elbow_file, 'ELBOW_TOUCH_FG_PCT'))
        elbow_touch_ast = g(elbow_file, 'ELBOW_TOUCH_AST')
        elbow_touch_pts_pct = _pct_to_ratio(g(elbow_file, 'ELBOW_TOUCH_PTS_PCT'))
        elbow_touches_pg = _safe_div(elbow_touches_total, max(1.0, games), 0.0)
        elbow_touch_ast_pg = _safe_div(elbow_touch_ast, max(1.0, games), 0.0)

        # ── Clutch data ──
        clutch_file = 'player_clutch_traditional_SEASON_regular_season.csv'
        clutch_gp = g(clutch_file, 'GP')
        clutch_pts = g(clutch_file, 'PTS')
        clutch_fg_pct = _pct_to_ratio(g(clutch_file, 'FG_PCT'))
        clutch_fg3_pct = _pct_to_ratio(g(clutch_file, 'FG3_PCT'))
        clutch_ft_pct = _pct_to_ratio(g(clutch_file, 'FT_PCT'))
        clutch_fga = g(clutch_file, 'FGA')
        clutch_ast = g(clutch_file, 'AST')
        clutch_tov = g(clutch_file, 'TOV')
        clutch_plus_minus = g(clutch_file, 'PLUS_MINUS')
        clutch_pts_pg = clutch_pts  # Already per-game from NBA site.
        clutch_fga_pg = clutch_fga  # Already per-game from NBA site.
        clutch_adv_file = 'player_clutch_advanced_SEASON_regular_season.csv'
        clutch_usg = _pct_to_100(g(clutch_adv_file, 'USG_PCT'))
        clutch_ts = _pct_to_ratio(g(clutch_adv_file, 'TS_PCT'))
        clutch_net_rating = g(clutch_adv_file, 'NET_RATING')

        # Derived shooting helpers
        fg2m_pg = max(0.0, fgm_pg - fg3m_pg)
        fg2a_pg = max(0.0, fga_pg - fg3a_pg)
        fg2_pct = _safe_div(fg2m_pg, fg2a_pg, 0.5)
        efg_pct = _safe_div(fgm_pg + 0.5 * fg3m_pg, fga_pg, 0.5)

        # Post proxies: prefer tracking post-touch signals (full coverage),
        # fall back to playtype post-up where needed.
        post_up_pct_playtype = _pct_to_ratio(g('player_playtype_playtype_post_up_SEASON_regular_season.csv', 'POSS_PCT'))
        post_up_fg_playtype = _pct_to_ratio(g('player_playtype_playtype_post_up_SEASON_regular_season.csv', 'FG_PCT'))

        post_touches_total = g('player_tracking_tracking_post_ups_SEASON_regular_season.csv', 'POST_TOUCHES')
        touches_total = g('player_tracking_tracking_post_ups_SEASON_regular_season.csv', 'TOUCHES')
        post_touch_fga_total = g('player_tracking_tracking_post_ups_SEASON_regular_season.csv', 'POST_TOUCH_FGA')
        post_touch_fg_pct = _pct_to_ratio(g('player_tracking_tracking_post_ups_SEASON_regular_season.csv', 'POST_TOUCH_FG_PCT'))
        post_touch_pts_pct = _pct_to_ratio(g('player_tracking_tracking_post_ups_SEASON_regular_season.csv', 'POST_TOUCH_PTS_PCT'))

        post_touch_share = _safe_div(post_touches_total, max(1.0, touches_total), 0.0)
        post_shot_share = _safe_div(post_touch_fga_total, max(1.0, fga_pg * games), 0.0)

        post_up_pct = min(1.0, 0.55 * post_touch_share + 0.35 * post_shot_share + 0.10 * post_touch_pts_pct)
        if post_touches_total <= 0.0 and touches_total <= 0.0:
            post_up_pct = post_up_pct_playtype

        post_up_fg = post_touch_fg_pct
        if post_touch_fga_total <= 0.0:
            post_up_fg = post_up_fg_playtype

        iso_pct = _pct_to_ratio(g('player_playtype_isolation_SEASON_regular_season.csv', 'POSS_PCT'))
        iso_fg = _pct_to_ratio(g('player_playtype_isolation_SEASON_regular_season.csv', 'FG_PCT'))
        iso_ppp = g('player_playtype_isolation_SEASON_regular_season.csv', 'PPP')
        iso_percentile = g('player_playtype_isolation_SEASON_regular_season.csv', 'PERCENTILE')
        off_screen_pct = _pct_to_ratio(g('player_playtype_off_screen_SEASON_regular_season.csv', 'POSS_PCT'))
        off_screen_fg = _pct_to_ratio(g('player_playtype_off_screen_SEASON_regular_season.csv', 'FG_PCT'))
        spot_up_pct = _pct_to_ratio(g('player_playtype_spot_up_SEASON_regular_season.csv', 'POSS_PCT'))
        spot_up_fg = _pct_to_ratio(g('player_playtype_spot_up_SEASON_regular_season.csv', 'FG_PCT'))
        ball_handler_pct = _pct_to_ratio(g('player_playtype_ball_handler_SEASON_regular_season.csv', 'POSS_PCT'))
        ball_handler_fg = _pct_to_ratio(g('player_playtype_ball_handler_SEASON_regular_season.csv', 'FG_PCT'))
        ball_handler_ppp = g('player_playtype_ball_handler_SEASON_regular_season.csv', 'PPP')
        hand_off_pct = _pct_to_ratio(g('player_playtype_hand_off_SEASON_regular_season.csv', 'POSS_PCT'))
        hand_off_fg = _pct_to_ratio(g('player_playtype_hand_off_SEASON_regular_season.csv', 'FG_PCT'))

        # Scoring percentage breakdowns.
        scoring_pct_pts_paint = _pct_to_ratio(g('player_scoring_SEASON_regular_season.csv', 'PCT_PTS_PAINT'))
        scoring_pct_pts_fb = _pct_to_ratio(g('player_scoring_SEASON_regular_season.csv', 'PCT_PTS_FB'))
        scoring_pct_uast_2pm = _pct_to_ratio(g('player_scoring_SEASON_regular_season.csv', 'PCT_UAST_2PM'))
        scoring_pct_uast_3pm = _pct_to_ratio(g('player_scoring_SEASON_regular_season.csv', 'PCT_UAST_3PM'))
        scoring_pct_fga_2pt = _pct_to_ratio(g('player_scoring_SEASON_regular_season.csv', 'PCT_FGA_2PT'))
        scoring_pct_fga_3pt = _pct_to_ratio(g('player_scoring_SEASON_regular_season.csv', 'PCT_FGA_3PT'))

        # Individual zone FGA/FGM/FG_PCT breakdowns for sub-zone tendencies.
        zone_left_corner_3_fga = zone_corner_l
        zone_right_corner_3_fga = zone_corner_r
        zone_above_break_3_fga = zone_above_break
        zone_left_corner_3_fgm = g('player_shooting_by_zone_SEASON_regular_season.csv', 'left_corner_3_fgm')
        zone_right_corner_3_fgm = g('player_shooting_by_zone_SEASON_regular_season.csv', 'right_corner_3_fgm')
        zone_above_break_3_fgm = g('player_shooting_by_zone_SEASON_regular_season.csv', 'above_the_break_3_fgm')
        zone_mid_fgm = g('player_shooting_by_zone_SEASON_regular_season.csv', 'mid_range_fgm')
        zone_restricted_fgm = g('player_shooting_by_zone_SEASON_regular_season.csv', 'restricted_area_fgm')
        zone_paint_non_ra_fgm = g('player_shooting_by_zone_SEASON_regular_season.csv', 'in_the_paint_non_ra_fgm')
        zone_paint_non_ra_fg_pct = g('player_shooting_by_zone_SEASON_regular_season.csv', 'in_the_paint_non_ra_fg_pct')
        zone_left_corner_3_fg_pct = _safe_div(zone_left_corner_3_fgm, max(1.0, zone_left_corner_3_fga), 0.0)
        zone_right_corner_3_fg_pct = _safe_div(zone_right_corner_3_fgm, max(1.0, zone_right_corner_3_fga), 0.0)
        zone_above_break_3_fg_pct = _safe_div(zone_above_break_3_fgm, max(1.0, zone_above_break_3_fga), 0.0)

        # Use explicit position from the bio CSV when available; fall back to inference.
        bio_position = str(row.get(sf('player_bio_SEASON_regular_season.csv') + ':POSITION') or '').strip().upper()
        _VALID_POSITIONS = {'PG', 'SG', 'SF', 'PF', 'C'}
        if bio_position in _VALID_POSITIONS:
            position = bio_position
        else:
            position = _infer_position(height_in, ast_pg, blk_pct)

        # Estimate dunk volume from season total restricted-area makes.
        restricted_makes_total = g('player_shooting_by_zone_SEASON_regular_season.csv', 'restricted_area_fgm')
        if position == 'C':
            dunk_factor = 0.62
        elif position == 'PF':
            dunk_factor = 0.50
        elif position == 'SF':
            dunk_factor = 0.36
        else:
            dunk_factor = 0.22
        dunk_est_total = max(0.0, restricted_makes_total * dunk_factor)

        # Crude DBPM proxy when direct DBPM is unavailable in this scrape.
        def_rating = g('player_defense_SEASON_regular_season.csv', 'DEF_RATING', 114.0)
        dws = g('player_defense_SEASON_regular_season.csv', 'DEF_WS')
        dbpm_proxy = (
            0.38 * _safe_div((113.0 - def_rating), 3.0, 0.0)
            + 0.28 * _safe_div((stl_pct - 1.5), 0.7, 0.0)
            + 0.24 * _safe_div((blk_pct - 2.5), 1.2, 0.0)
            + 0.10 * _safe_div((dws - 2.0), 1.5, 0.0)
        )
        zone_total = max(
            1.0,
            zone_restricted
            + zone_paint_non_ra
            + zone_mid
            + zone_corner_l
            + zone_corner_r
            + zone_above_break
            + zone_backcourt,
        )

        canonical: Dict[str, Any] = {
            'player_id': pid,
            'player_name': row.get('PLAYER_NAME', ''),
            'team_id': row.get('TEAM_ID', ''),
            'team_abbr': row.get('TEAM_ABBREVIATION', ''),
            'season_label': season_tag,
            'position': position,
            '__source_file': 'NBA Site data (normalized)',
            '__row_index': len(out),

            # Legacy-compatible aliases used throughout generator formulas
            'age': _to_float(row.get(sf('player_bio_SEASON_regular_season.csv') + ':AGE'), _to_float(row.get('AGE'), 0.0)),
            'per_game_g': games,
            'totals_g': games,
            'advanced_g': games,
            'per_game_mp_per_game': mpg,
            'totals_mp': minutes_total,
            'per_game_pts_per_game': _to_float(row.get('PTS')),
            'per_game_ast_per_game': _to_float(row.get('AST')),
            'per_game_tov_per_game': _to_float(row.get('TOV')),
            'per_game_stl_per_game': _to_float(row.get('STL')),
            'per_game_blk_per_game': _to_float(row.get('BLK')),
            'per_game_fga_per_game': _to_float(row.get('FGA')),
            'per_game_fg_percent': _to_float(row.get('FG_PCT')),
            'per_game_x3pa_per_game': _to_float(row.get('FG3A')),
            'per_game_x3p_percent': _to_float(row.get('FG3_PCT')),
            'per_game_fta_per_game': _to_float(row.get('FTA')),
            'per_game_ft_percent': _to_float(row.get('FT_PCT')),
            'per_game_e_fg_percent': efg_pct,
            'per_game_x2p_percent': fg2_pct,

            'advanced_usg_percent': usg_pct,
            'advanced_ast_percent': ast_pct,
            'advanced_tov_percent': tov_pct,
            'advanced_orb_percent': orb_pct,
            'advanced_drb_percent': drb_pct,
            'advanced_stl_percent': stl_pct,
            'advanced_blk_percent': blk_pct,
            'advanced_ts_percent': g('player_advanced_SEASON_regular_season.csv', 'TS_PCT', g('player_bio_SEASON_regular_season.csv', 'TS_PCT')),
            'advanced_dws': dws,
            'advanced_dbpm': dbpm_proxy,
            'advanced_x3p_ar': _safe_div(fg3a_pg, max(1.0, fga_pg), 0.0),

            # per-36 and per-100 approximations
            'per_36_fga_per_36_min': _safe_div(fga_pg * 36.0, max(1.0, mpg), 0.0),
            'per_36_fta_per_36_min': _safe_div(fta_pg * 36.0, max(1.0, mpg), 0.0),
            'per_36_x3pa_per_36_min': _safe_div(fg3a_pg * 36.0, max(1.0, mpg), 0.0),
            'per_36_x3p_percent': _to_float(row.get('FG3_PCT')),
            'per_36_x2p_percent': fg2_pct,
            'per_36_ft_percent': _to_float(row.get('FT_PCT')),
            'per_36_e_fg_percent': efg_pct,

            'per_100_ast_per_100_poss': _safe_div(ast_pg * games * 100.0, poss_total, 0.0),
            'per_100_stl_per_100_poss': _safe_div(stl_pg * games * 100.0, poss_total, 0.0),
            'per_100_blk_per_100_poss': _safe_div(blk_pg * games * 100.0, poss_total, 0.0),
            'per_100_fta_per_100_poss': _safe_div(fta_pg * games * 100.0, poss_total, 0.0),
            'per_100_pf_per_100_poss': _safe_div(pf_pg * games * 100.0, poss_total, 0.0),

            # Tracking playmaking features.
            'tracking_passes_made_pg': passes_made_pg,
            'tracking_passes_received_pg': passes_received_pg,
            'tracking_potential_ast_pg': potential_ast_pg,
            'tracking_ast_adj_pg': ast_adj_pg,
            'tracking_secondary_ast_pg': secondary_ast_pg,
            'tracking_ft_ast_pg': ft_ast_pg,
            'tracking_ast_to_pass_pct': ast_to_pass_pct,
            'tracking_ast_to_pass_pct_adj': ast_to_pass_pct_adj,
            'tracking_touches_pg': touches_pg,
            'tracking_front_ct_touches_pg': front_ct_touches_pg,
            'tracking_time_of_poss_pg': time_of_poss_pg,
            'tracking_avg_sec_per_touch': avg_sec_per_touch,
            'tracking_avg_drib_per_touch': avg_drib_per_touch,
            'tracking_pts_per_touch': pts_per_touch,
            'tracking_drives_pg': drives_pg,
            'tracking_drive_passes_pg': drive_passes_pg,
            'tracking_drive_ast_pg': drive_ast_pg,
            'tracking_drive_pass_rate': drive_pass_rate,
            'tracking_drive_ast_rate': drive_ast_rate,
            'tracking_drive_passes_pct': drive_passes_pct,
            'tracking_drive_fg_pct': drive_fg_pct,
            'tracking_drive_tov_pct': drive_tov_pct,
            'tracking_avg_speed': tracking_avg_speed,
            'tracking_avg_speed_off': tracking_avg_speed_off,
            'tracking_avg_speed_def': tracking_avg_speed_def,
            'tracking_dist_miles': tracking_dist_miles,
            'tracking_dist_miles_off': tracking_dist_miles_off,
            'tracking_dist_miles_def': tracking_dist_miles_def,
            'tracking_dist_feet': tracking_dist_feet,
            'tracking_dist_miles_pg': tracking_dist_miles_pg,
            'tracking_dist_miles_off_pg': tracking_dist_miles_off_pg,
            'tracking_dist_miles_def_pg': tracking_dist_miles_def_pg,
            'tracking_dist_miles_per_min': tracking_dist_miles_per_min,
            'hustle_contested_shots_pg': contested_shots_pg,
            'hustle_contested_2pt_pg': contested_2pt_pg,
            'hustle_contested_3pt_pg': contested_3pt_pg,
            'hustle_deflections_pg': deflections_pg,
            'hustle_charges_drawn_pg': charges_drawn_pg,
            'hustle_loose_balls_recovered_def_pg': loose_balls_recovered_def_pg,
            'defense_dash_overall_stop_delta': dash_overall_stop_delta,
            'defense_dash_overall_plusminus': dash_overall_plusminus,
            'defense_dash_3pt_stop_delta': dash_3pt_stop_delta,
            'defense_dash_3pt_plusminus': dash_3pt_plusminus,
            'defense_dash_2pt_stop_delta': dash_2pt_stop_delta,
            'defense_dash_2pt_plusminus': dash_2pt_plusminus,
            'defense_dash_lt6_stop_delta': dash_lt6_stop_delta,
            'defense_dash_lt6_plusminus': dash_lt6_plusminus,

            # Rebounding tracking.
            'tracking_oreb_contest_pg': oreb_contest_pg,
            'tracking_oreb_chances_pg': oreb_chances_pg,
            'tracking_oreb_chance_pct': oreb_chance_pct,
            'tracking_oreb_chance_pct_adj': oreb_chance_pct_adj,
            'tracking_dreb_contest_pg': dreb_contest_pg,
            'tracking_dreb_chances_pg': dreb_chances_pg,
            'tracking_dreb_chance_pct': dreb_chance_pct,
            'tracking_dreb_chance_pct_adj': dreb_chance_pct_adj,

            # Box-out data.
            'tracking_box_outs_pg': box_outs_pg,
            'tracking_box_outs_def_pg': box_outs_def_pg,
            'tracking_box_outs_off_pg': box_outs_off_pg,

            # Finishing playtypes.
            'playtype_cut_fg_pct': cut_fg_pct,
            'playtype_cut_poss_pct': cut_poss_pct,
            'playtype_roll_man_fg_pct': roll_man_fg_pct,
            'playtype_roll_man_poss_pct': roll_man_poss_pct,

            # Additional playtype data for tendency rework.
            'playtype_iso_poss_pct': iso_pct,
            'playtype_iso_fg_pct': iso_fg,
            'playtype_iso_ppp': iso_ppp,
            'playtype_iso_percentile': iso_percentile,
            'playtype_spot_up_poss_pct': spot_up_pct,
            'playtype_spot_up_fg_pct': spot_up_fg,
            'playtype_ball_handler_poss_pct': ball_handler_pct,
            'playtype_ball_handler_fg_pct': ball_handler_fg,
            'playtype_ball_handler_ppp': ball_handler_ppp,
            'playtype_off_screen_poss_pct': off_screen_pct,
            'playtype_off_screen_fg_pct': off_screen_fg,
            'playtype_hand_off_poss_pct': hand_off_pct,
            'playtype_hand_off_fg_pct': hand_off_fg,
            'playtype_post_up_poss_pct': post_up_pct,
            'playtype_post_up_fg_pct': post_up_fg,

            # Scoring percentage breakdowns.
            'scoring_pct_pts_paint': scoring_pct_pts_paint,
            'scoring_pct_pts_fb': scoring_pct_pts_fb,
            'scoring_pct_uast_2pm': scoring_pct_uast_2pm,
            'scoring_pct_uast_3pm': scoring_pct_uast_3pm,
            'scoring_pct_fga_2pt': scoring_pct_fga_2pt,
            'scoring_pct_fga_3pt': scoring_pct_fga_3pt,

            # Zone FGA/FGM breakdowns for sub-zone tendencies.
            'zone_restricted_fga': zone_restricted,
            'zone_restricted_fgm': zone_restricted_fgm,
            'zone_paint_non_ra_fga': zone_paint_non_ra,
            'zone_paint_non_ra_fgm': zone_paint_non_ra_fgm,
            'zone_paint_non_ra_fg_pct': zone_paint_non_ra_fg_pct,
            'zone_mid_fga': zone_mid,
            'zone_mid_fgm': zone_mid_fgm,
            'zone_left_corner_3_fga': zone_left_corner_3_fga,
            'zone_left_corner_3_fgm': zone_left_corner_3_fgm,
            'zone_left_corner_3_fg_pct': zone_left_corner_3_fg_pct,
            'zone_right_corner_3_fga': zone_right_corner_3_fga,
            'zone_right_corner_3_fgm': zone_right_corner_3_fgm,
            'zone_right_corner_3_fg_pct': zone_right_corner_3_fg_pct,
            'zone_above_break_3_fga': zone_above_break_3_fga,
            'zone_above_break_3_fgm': zone_above_break_3_fgm,
            'zone_above_break_3_fg_pct': zone_above_break_3_fg_pct,

            # Paint touch data.
            'tracking_paint_touch_fg_pct': paint_touch_fg_pct,
            'tracking_paint_touches_pg': paint_touches_pg,

            # Catch-and-shoot data.
            'tracking_catch_shoot_fg3_pct': catch_shoot_fg3_pct,
            'tracking_catch_shoot_efg_pct': catch_shoot_efg_pct,
            'tracking_catch_shoot_fg3a_pg': catch_shoot_fg3a_pg,

            # Shot dashboard: dribble breakdown.
            'shot_dash_zero_drib_freq': zero_drib_freq,
            'shot_dash_zero_drib_fg_pct': zero_drib_fg_pct,
            'shot_dash_zero_drib_fg3_pct': zero_drib_fg3_pct,
            'shot_dash_off_dribble_freq': off_dribble_freq,
            'shot_dash_7p_drib_freq': seven_p_drib_freq,
            'shot_dash_7p_drib_fg_pct': seven_p_drib_fg_pct,

            # Shot dashboard: closest defender breakdown.
            'shot_dash_contested_freq': contested_freq,
            'shot_dash_contested_fg_pct': contested_fg_pct,
            'shot_dash_contested_delta': contested_delta,
            'shot_dash_very_tight_freq': very_tight_freq,
            'shot_dash_very_tight_fg_pct': very_tight_fg_pct,
            'shot_dash_tight_freq': tight_freq,
            'shot_dash_tight_fg_pct': tight_fg_pct,
            'shot_dash_open_fg_pct': open_fg_pct,
            'shot_dash_wide_open_fg_pct': wide_open_fg_pct,

            # Shot dashboard: touch time breakdown.
            'shot_dash_touch_lt2_freq': touch_lt2_freq,
            'shot_dash_touch_lt2_fg_pct': touch_lt2_fg_pct,
            'shot_dash_touch_lt2_efg': touch_lt2_efg,
            'shot_dash_touch_6p_freq': touch_6p_freq,
            'shot_dash_touch_6p_fg_pct': touch_6p_fg_pct,

            # Transition playtype data.
            'playtype_transition_poss_pct': transition_poss_pct,
            'playtype_transition_ppp': transition_ppp,
            'playtype_transition_fg_pct': transition_fg_pct,
            'playtype_transition_score_pct': transition_score_pct,
            'playtype_transition_poss': transition_poss,
            'playtype_transition_percentile': transition_percentile,

            # Misc data.
            'misc_pts_paint_pg': misc_pts_paint_pg,
            'misc_pts_fb_pg': misc_pts_fb_pg,
            'misc_pts_2nd_chance_pg': misc_pts_2nd_chance_pg,
            'misc_blka_pg': misc_blka_pg,
            'misc_pfd_pg': misc_pfd_pg,

            # Elbow touch data.
            'tracking_elbow_touches_pg': elbow_touches_pg,
            'tracking_elbow_touch_fg_pct': elbow_touch_fg_pct,
            'tracking_elbow_touch_ast_pg': elbow_touch_ast_pg,
            'tracking_elbow_touch_pts_pct': elbow_touch_pts_pct,

            # Clutch data.
            'clutch_pts_pg': clutch_pts_pg,
            'clutch_fga_pg': clutch_fga_pg,
            'clutch_fg_pct': clutch_fg_pct,
            'clutch_fg3_pct': clutch_fg3_pct,
            'clutch_ft_pct': clutch_ft_pct,
            'clutch_ast': clutch_ast,
            'clutch_tov': clutch_tov,
            'clutch_plus_minus': clutch_plus_minus,
            'clutch_usg': clutch_usg,
            'clutch_ts': clutch_ts,
            'clutch_net_rating': clutch_net_rating,
            'clutch_gp': clutch_gp,

            'player_info_ht_in_in': height_in,
            'height_in': height_in,
            'player_info_wt': weight_lbs,
            'weight_lbs': weight_lbs,
            'weight': weight_lbs,

            # Bio info for display
            'college': str(row.get(sf('player_bio_SEASON_regular_season.csv') + ':COLLEGE') or '').strip(),
            'country': str(row.get(sf('player_bio_SEASON_regular_season.csv') + ':COUNTRY') or '').strip(),
            'draft_year': str(row.get(sf('player_bio_SEASON_regular_season.csv') + ':DRAFT_YEAR') or '').strip(),
            'draft_round': str(row.get(sf('player_bio_SEASON_regular_season.csv') + ':DRAFT_ROUND') or '').strip(),
            'draft_number': str(row.get(sf('player_bio_SEASON_regular_season.csv') + ':DRAFT_NUMBER') or '').strip(),
            'height': str(row.get(sf('player_bio_SEASON_regular_season.csv') + ':PLAYER_HEIGHT') or '').strip(),

            # Per-game rebounds (not in traditional normalization)
            'per_game_reb_per_game': _to_float(row.get('REB')),
            'per_game_oreb_per_game': _to_float(row.get('OREB')),
            'per_game_dreb_per_game': _to_float(row.get('DREB')),

            'shooting_percent_fga_from_x0_3_range': zone_restricted / zone_total,
            'shooting_percent_fga_from_x3_10_range': zone_paint_non_ra / zone_total,
            'shooting_percent_fga_from_x10_16_range': zone_mid / zone_total,
            'shooting_percent_fga_from_x16_3p_range': _pct_to_ratio(g('player_scoring_SEASON_regular_season.csv', 'PCT_PTS_2PT_MR')),
            'shooting_percent_fga_from_x3p_range': (zone_corner_l + zone_corner_r + zone_above_break + zone_backcourt) / zone_total,
            'shooting_fg_percent_from_x0_3_range': g('player_shooting_by_zone_SEASON_regular_season.csv', 'restricted_area_fg_pct'),
            'shooting_fg_percent_from_x10_16_range': g('player_shooting_by_zone_SEASON_regular_season.csv', 'mid_range_fg_pct'),
            'shooting_percent_corner_3s_of_3pa': _safe_div(zone_corner_l + zone_corner_r, max(1.0, fg3a_pg), 0.0),
            'shooting_percent_assisted_x2p_fg': _pct_to_ratio(g('player_scoring_SEASON_regular_season.csv', 'PCT_AST_2PM')),
            'shooting_percent_assisted_x3p_fg': _pct_to_ratio(g('player_scoring_SEASON_regular_season.csv', 'PCT_AST_3PM')),
            'shooting_num_of_dunks': dunk_est_total,
            'shooting_percent_dunks_of_fga': _safe_div(dunk_est_total, max(1.0, fga_pg * games), 0.0),
            'shooting_avg_dist_fga': 0.0,

            # PBP-style placeholders, mapped to available tracking proxies.
            'pbp_features_pullup_3p_pct': g('player_tracking_pullup_SEASON_regular_season.csv', 'PULL_UP_FG3_PCT'),
            'pbp_features_pullup_3_freq': (
                g('player_tracking_pullup_SEASON_regular_season.csv', 'PULL_UP_FG3A') /
                max(1.0, _to_float(row.get('FG3A')))
            ),
            'pbp_features_pullup_freq': (
                g('player_tracking_pullup_SEASON_regular_season.csv', 'PULL_UP_FGA') /
                max(1.0, _to_float(row.get('FGA')))
            ),
            'pbp_features_stepback_3pa': g('player_tracking_pullup_SEASON_regular_season.csv', 'PULL_UP_FG3A'),
            'pbp_features_stepback_freq': _safe_div(g('player_tracking_pullup_SEASON_regular_season.csv', 'PULL_UP_FGA'), max(1.0, fga_pg), 0.0) * 0.40,
            'pbp_features_fadeaway_freq': post_up_pct * (0.35 if position in ('SF', 'SG', 'PG') else 0.28),
            'pbp_features_hook_freq': post_up_pct * (0.45 if position in ('C', 'PF') else 0.30),
            'pbp_features_fadeaway_fg_pct': max(
                0.0,
                min(
                    1.0,
                    0.70 * post_up_fg
                    + 0.30 * g('player_shooting_by_zone_SEASON_regular_season.csv', 'mid_range_fg_pct', 0.42),
                ),
            ),
            'pbp_features_hook_fg_pct': max(
                0.0,
                min(
                    1.0,
                    0.70 * post_up_fg
                    + 0.30 * g('player_shooting_by_zone_SEASON_regular_season.csv', 'in_the_paint_non_ra_fg_pct', g('player_shooting_by_zone_SEASON_regular_season.csv', 'restricted_area_fg_pct', 0.55)),
                ),
            ),

            # Additional legacy placeholders used by tendencies.
            'play_by_play_fga_blocked': _safe_div(g('player_defense_SEASON_regular_season.csv', 'BLK'), max(1.0, games), 0.0),
            'play_by_play_lost_ball_turnover': _safe_div(_to_float(row.get('TOV')) * 0.35, 1.0, 0.0),
            'play_by_play_shooting_foul_committed': _safe_div(pf_pg * 0.45, 1.0, 0.0),
        }

        out.append(canonical)

    return out


if __name__ == '__main__':
    rows = load_nba_site_rows('NBA Site data')
    print(f'Normalized rows: {len(rows)}')
    if rows:
        sample = rows[0]
        keys = sorted(sample.keys())[:30]
        print('Sample keys:', keys)
