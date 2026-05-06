"""Feature engineering for ML attribute prediction.

Creates features from raw merged data including percentile rankings
so the model can distinguish elite players from average ones.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from .config import ATTRIBUTE_NAMES, ML_ATTRIBUTES, HEURISTIC_ATTRIBUTES


# Attribute column names (including typo variant and parenthetical suffixes from Excel)
ATTRIBUTE_COL_NAMES = set(ATTRIBUTE_NAMES) | {
    "Free Thow",
    "Stamina (Second To last)",
    "Intangibles (Last)",
}

POSITION_MAPPING = {
    "PG": "guard",
    "SG": "guard",
    "SG-SF": "guard",
    "SF": "wing",
    "SF-SG": "wing",
    "PF": "big",
    "C": "big",
    "PF-C": "big",
    "C-PF": "big",
}


def detect_position_group(position: str) -> str:
    """Detect position group from position string."""
    if not position:
        return "guard"
    pos_upper = position.upper().strip()
    if "C" in pos_upper and "PF" not in pos_upper:
        return "big"
    if "PF" in pos_upper:
        return "big"
    if "SF" in pos_upper:
        return "wing"
    return "guard"


def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find first matching column name (case-insensitive)."""
    col_map = {c.upper(): c for c in df.columns}
    for candidate in candidates:
        if candidate.upper() in col_map:
            return col_map[candidate.upper()]
        # Check aliases
        for alias in _COLUMN_ALIASES.get(candidate.upper(), []):
            if alias.upper() in col_map:
                return col_map[alias.upper()]
    return None


# Aliases for columns from gen_player_fast.py merged data
_COLUMN_ALIASES = {
    "PTS": ["per_game_pts_per_game"],
    "REB": ["per_game_reb_per_game"],
    "TRB": ["per_game_reb_per_game"],
    "AST": ["per_game_ast_per_game"],
    "STL": ["per_game_stl_per_game"],
    "BLK": ["per_game_blk_per_game"],
    "TOV": ["per_game_tov_per_game"],
    "OREB": ["per_game_oreb_per_game"],
    "DREB": ["per_game_dreb_per_game"],
    "FGM": ["per_game_fg_per_game"],
    "FGA": ["per_game_fga_per_game"],
    "FG3M": ["per_game_x3p_per_game"],
    "FG3A": ["per_game_x3pa_per_game"],
    "FTM": ["per_game_ft_per_game"],
    "FTA": ["per_game_fta_per_game"],
    "PF": ["per_game_pf_per_game"],
    "PFD": ["per_game_pfd_per_game"],
    "MIN": ["per_game_mp_per_game"],
    "GP": ["per_game_g"],
    "FG_PCT": ["per_game_fg_percent"],
    "FG3_PCT": ["per_game_x3p_percent"],
    "FT_PCT": ["per_game_ft_percent"],
    "TS_PCT": ["advanced_ts_percent"],
    "EFG_PCT": ["per_game_e_fg_percent"],
    "USG_PCT": ["advanced_usg_percent"],
    "AST_PCT": ["advanced_ast_percent"],
    "OREB_PCT": ["advanced_orb_percent"],
    "DREB_PCT": ["advanced_drb_percent"],
    "TOV_PCT": ["advanced_tov_percent"],
    "PLAYER_HEIGHT_INCHES": ["player_info_ht_in_in"],
    "PLAYER_WEIGHT": ["player_info_wt"],
    "AGE": ["age"],
}


def _safe_num(series, default=0.0):
    """Convert series to numeric safely."""
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _compute_percentiles(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Compute percentile rank for each column (0-100 scale)."""
    result = pd.DataFrame(index=df.index)
    for col in cols:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce")
            # Percentile rank: what % of players this player is better than
            result[f"pct_{col}"] = vals.rank(pct=True) * 100
    return result


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer features from raw merged data.

    Creates a rich feature set including:
    - Per-game stats
    - Per-36 stats
    - Shooting percentages
    - Derived ratios
    - Advanced stats
    - Tracking data
    - Playtype data
    - Hustle data
    - Bio data
    - Percentile rankings (critical for distinguishing elite players)
    """
    feature_df = df.copy()

    # Position
    pos_col = _find_col(feature_df, ["POSITION", "position", "pos"])
    if pos_col:
        positions = feature_df[pos_col].fillna("SG")
    else:
        positions = pd.Series("SG", index=feature_df.index)
    feature_df["position_group"] = positions.apply(detect_position_group)

    # Core stats
    gp_col = _find_col(feature_df, ["GP", "G"])
    min_col = _find_col(feature_df, ["MIN", "MP"])
    pts_col = _find_col(feature_df, ["PTS"])
    reb_col = _find_col(feature_df, ["REB", "TRB"])
    ast_col = _find_col(feature_df, ["AST"])
    stl_col = _find_col(feature_df, ["STL"])
    blk_col = _find_col(feature_df, ["BLK"])
    fgm_col = _find_col(feature_df, ["FGM"])
    fga_col = _find_col(feature_df, ["FGA"])
    fg3m_col = _find_col(feature_df, ["FG3M", "X3PM"])
    fg3a_col = _find_col(feature_df, ["FG3A", "X3PA"])
    ftm_col = _find_col(feature_df, ["FTM"])
    fta_col = _find_col(feature_df, ["FTA"])
    tov_col = _find_col(feature_df, ["TOV"])
    oreb_col = _find_col(feature_df, ["OREB"])
    dreb_col = _find_col(feature_df, ["DREB"])
    pf_col = _find_col(feature_df, ["PF"])
    pfd_col = _find_col(feature_df, ["PFD"])

    gp = (
        _safe_num(feature_df[gp_col])
        if gp_col
        else pd.Series(1.0, index=feature_df.index).replace(0, 1)
    )
    gp = gp.replace(0, 1)
    mins_pg = (
        _safe_num(feature_df[min_col])
        if min_col
        else pd.Series(30.0, index=feature_df.index)
    )

    # ── Per-game stats ──────────────────────────────────────────────────
    # NBA Site traditional data is already per-game, so we use values directly
    for src_col, feat_name in [
        (pts_col, "f_pg_pts"),
        (reb_col, "f_pg_reb"),
        (ast_col, "f_pg_ast"),
        (stl_col, "f_pg_stl"),
        (blk_col, "f_pg_blk"),
        (tov_col, "f_pg_tov"),
        (oreb_col, "f_pg_oreb"),
        (dreb_col, "f_pg_dreb"),
        (fgm_col, "f_pg_fgm"),
        (fga_col, "f_pg_fga"),
        (fg3m_col, "f_pg_fg3m"),
        (fg3a_col, "f_pg_fg3a"),
        (ftm_col, "f_pg_ftm"),
        (fta_col, "f_pg_fta"),
        (pf_col, "f_pg_pf"),
        (pfd_col, "f_pg_pfd"),
    ]:
        if src_col:
            feature_df[feat_name] = _safe_num(feature_df[src_col])

    # ── Per-36 stats ────────────────────────────────────────────────────
    mins_safe = mins_pg.replace(0, 1)
    for src_col, feat_name in [
        (pts_col, "f_36_pts"),
        (reb_col, "f_36_reb"),
        (ast_col, "f_36_ast"),
        (blk_col, "f_36_blk"),
        (stl_col, "f_36_stl"),
    ]:
        if src_col:
            feature_df[feat_name] = (
                _safe_num(feature_df[src_col]) / mins_safe.replace(0, 1) * 36
            )

    # ── Shooting percentages ────────────────────────────────────────────
    for src_col, feat_name in [
        (_find_col(feature_df, ["FG_PCT", "FG%"]), "f_fg_pct"),
        (_find_col(feature_df, ["FG3_PCT", "FG3%", "X3P_PERCENT"]), "f_fg3_pct"),
        (_find_col(feature_df, ["FT_PCT", "FT%"]), "f_ft_pct"),
        (_find_col(feature_df, ["TS_PCT"]), "f_ts_pct"),
        (_find_col(feature_df, ["EFG_PCT", "EFG%"]), "f_efg_pct"),
    ]:
        if src_col:
            feature_df[feat_name] = _safe_num(feature_df[src_col])

    # ── Derived ratios ──────────────────────────────────────────────────
    if fga_col:
        fga_v = _safe_num(feature_df[fga_col])
        if fg3a_col:
            fg3a_v = _safe_num(feature_df[fg3a_col])
            feature_df["f_fg3a_rate"] = np.where(fga_v > 0, fg3a_v / fga_v, 0.0)
        if fta_col:
            fta_v = _safe_num(feature_df[fta_col])
            feature_df["f_ft_rate"] = np.where(fga_v > 0, fta_v / fga_v, 0.0)
    if ast_col and tov_col:
        ast_v = _safe_num(feature_df[ast_col])
        tov_v = _safe_num(feature_df[tov_col])
        feature_df["f_ast_tov_ratio"] = np.where(tov_v > 0, ast_v / tov_v, ast_v)

    # ── Advanced stats ──────────────────────────────────────────────────
    for src_col, feat_name in [
        (_find_col(feature_df, ["USG_PCT", "USG%", "USG"]), "f_usg"),
        (_find_col(feature_df, ["AST_PCT", "AST%"]), "f_ast_pct"),
        (_find_col(feature_df, ["REB_PCT", "REB%"]), "f_reb_pct"),
        (_find_col(feature_df, ["OREB_PCT"]), "f_oreb_pct"),
        (_find_col(feature_df, ["DREB_PCT"]), "f_dreb_pct"),
        (_find_col(feature_df, ["TOV_PCT", "E_TOV_PCT"]), "f_tov_pct"),
        (_find_col(feature_df, ["OFF_RATING"]), "f_off_rtg"),
        (_find_col(feature_df, ["DEF_RATING"]), "f_def_rtg"),
        (_find_col(feature_df, ["NET_RATING"]), "f_net_rtg"),
        (_find_col(feature_df, ["PIE"]), "f_pie"),
        (_find_col(feature_df, ["PCT_STL", "STL%"]), "f_pct_stl"),
        (_find_col(feature_df, ["PCT_BLK", "BLK%"]), "f_pct_blk"),
    ]:
        if src_col:
            feature_df[feat_name] = _safe_num(feature_df[src_col])

    # ── Tracking: Drives ────────────────────────────────────────────────
    # NBA tracking drives data is totals, divide by GP
    drives_col = _find_col(feature_df, ["DRIVES"])
    if drives_col:
        feature_df["f_drives_pg"] = _safe_num(feature_df[drives_col]) / gp
    for src_col, feat_name in [
        (_find_col(feature_df, ["DRIVE_FG_PCT", "DRIVE_FG%"]), "f_drive_fg_pct"),
        (_find_col(feature_df, ["DRIVE_AST_PCT"]), "f_drive_ast_pct"),
    ]:
        if src_col:
            feature_df[feat_name] = _safe_num(feature_df[src_col])

    # ── Tracking: Touches ───────────────────────────────────────────────
    # NBA tracking touches data is totals, divide by GP
    touches_col = _find_col(feature_df, ["TOUCHES"])
    if touches_col:
        feature_df["f_touches_pg"] = _safe_num(feature_df[touches_col]) / gp
    for src_col, feat_name in [
        (_find_col(feature_df, ["PAINT_TOUCHES"]), "f_paint_touch_pg"),
        (_find_col(feature_df, ["POST_TOUCHES"]), "f_post_touch_pg"),
        (_find_col(feature_df, ["ELBOW_TOUCHES"]), "f_elbow_touch_pg"),
        (_find_col(feature_df, ["PTS_PER_TOUCH"]), "f_pts_per_touch"),
        (_find_col(feature_df, ["AVG_SEC_PER_TOUCH"]), "f_sec_per_touch"),
    ]:
        if src_col:
            val = _safe_num(feature_df[src_col])
            if "pg" in feat_name:
                feature_df[feat_name] = val / gp
            else:
                feature_df[feat_name] = val

    # ── Tracking: Passing ───────────────────────────────────────────────
    # NBA tracking passing data is totals, divide by GP
    passes_col = _find_col(feature_df, ["PASSES_MADE"])
    if passes_col:
        feature_df["f_passes_pg"] = _safe_num(feature_df[passes_col]) / gp
    pot_ast_col = _find_col(feature_df, ["POTENTIAL_AST"])
    if pot_ast_col:
        feature_df["f_pot_ast_pg"] = _safe_num(feature_df[pot_ast_col]) / gp
    for src_col, feat_name in [
        (_find_col(feature_df, ["AST_TO_PASS_PCT"]), "f_ast_pass_pct"),
        (_find_col(feature_df, ["SECONDARY_AST"]), "f_sec_ast_pg"),
    ]:
        if src_col:
            val = _safe_num(feature_df[src_col])
            if "pg" in feat_name:
                feature_df[feat_name] = val / gp
            else:
                feature_df[feat_name] = val

    # ── Tracking: Catch & Shoot ─────────────────────────────────────────
    for src_col, feat_name in [
        (_find_col(feature_df, ["CATCH_SHOOT_FG3A"]), "f_cs_fg3a_pg"),
        (
            _find_col(feature_df, ["CATCH_SHOOT_FG3_PCT", "CATCH_SHOOT_FG_PCT"]),
            "f_cs_fg_pct",
        ),
    ]:
        if src_col:
            val = _safe_num(feature_df[src_col])
            if "pg" in feat_name:
                feature_df[feat_name] = val / gp
            else:
                feature_df[feat_name] = val

    # ── Tracking: Pull-Up ───────────────────────────────────────────────
    for src_col, feat_name in [
        (_find_col(feature_df, ["PULL_UP_FG3A", "PULLUP_FG3A"]), "f_pu_fg3a_pg"),
        (_find_col(feature_df, ["PULL_UP_FG3_PCT", "PULLUP_FG3_PCT"]), "f_pu_fg_pct"),
    ]:
        if src_col:
            val = _safe_num(feature_df[src_col])
            if "pg" in feat_name:
                feature_df[feat_name] = val / gp
            else:
                feature_df[feat_name] = val

    # ── Tracking: Speed ─────────────────────────────────────────────────
    for src_col, feat_name in [
        (_find_col(feature_df, ["AVG_SPEED"]), "f_avg_speed"),
        (_find_col(feature_df, ["AVG_SPEED_OFF"]), "f_avg_speed_off"),
        (_find_col(feature_df, ["DIST_MILE", "DIST"]), "f_dist_pg"),
    ]:
        if src_col:
            val = _safe_num(feature_df[src_col])
            if "pg" in feat_name:
                feature_df[feat_name] = val / gp
            else:
                feature_df[feat_name] = val

    # ── Playtypes ───────────────────────────────────────────────────────
    # After merging, playtype-specific columns get suffixes like _pt_isolation
    for pt in [
        "spot_up",
        "ball_handler",
        "isolation",
        "transition",
        "off_screen",
        "cut",
        "roll_man",
    ]:
        for src_col, feat_name in [
            (
                _find_col(
                    feature_df,
                    [
                        f"{pt.upper()}_POSS_PCT",
                        f"POSS_PCT_pt_{pt}",
                        f"POSS_PCT_{pt}",
                    ],
                ),
                f"f_{pt}_poss_pct",
            ),
            (
                _find_col(
                    feature_df,
                    [f"{pt.upper()}_PPP", f"PPP_pt_{pt}", f"PPP_{pt}"],
                ),
                f"f_{pt}_ppp",
            ),
        ]:
            if src_col:
                feature_df[feat_name] = _safe_num(feature_df[src_col])

    # ── Hustle ──────────────────────────────────────────────────────────
    # NBA hustle data is totals, divide by GP
    for src_col, feat_name in [
        (_find_col(feature_df, ["DEFLECTIONS"]), "f_deflections_pg"),
        (_find_col(feature_df, ["CONTESTED_SHOTS"]), "f_contested_pg"),
        (_find_col(feature_df, ["CONTESTED_SHOTS_3PT"]), "f_contested3_pg"),
        (_find_col(feature_df, ["BOX_OUTS"]), "f_boxouts_pg"),
        (_find_col(feature_df, ["SCREEN_ASSISTS"]), "f_scr_ast_pg"),
    ]:
        if src_col:
            feature_df[feat_name] = _safe_num(feature_df[src_col]) / gp

    # ── Bio ─────────────────────────────────────────────────────────────
    for src_col, feat_name in [
        (_find_col(feature_df, ["PLAYER_HEIGHT_INCHES", "HEIGHT"]), "f_height"),
        (_find_col(feature_df, ["PLAYER_WEIGHT", "WEIGHT"]), "f_weight"),
        (_find_col(feature_df, ["AGE"]), "f_age"),
    ]:
        if src_col:
            feature_df[feat_name] = _safe_num(feature_df[src_col])

    # ── Misc ────────────────────────────────────────────────────────────
    for src_col, feat_name in [
        (_find_col(feature_df, ["DD2"]), "f_dd2_pg"),
        (_find_col(feature_df, ["TD3"]), "f_td3_pg"),
        (_find_col(feature_df, ["PLUS_MINUS"]), "f_plus_minus"),
    ]:
        if src_col:
            val = _safe_num(feature_df[src_col])
            if "pg" in feat_name:
                feature_df[feat_name] = val / gp
            else:
                feature_df[feat_name] = val

    # ── Drop features unavailable in generator DB at inference ───────────
    # These features have fundamentally different scales or are missing
    # in the generator database, causing train/inference mismatch.
    drop_cols = [
        "f_off_rtg",  # Not in generator DB, approximation unreliable
        "f_def_rtg",  # Not in generator DB
        "f_net_rtg",  # Not in generator DB (clutch_net_rating != net_rating)
        "f_pie",  # Not in generator DB
        "f_reb_pct",  # Not in generator DB
        "f_pct_stl",  # Scale mismatch (defense CSV percentile vs actual STL%)
        "f_pct_blk",  # Scale mismatch (defense CSV percentile vs actual BLK%)
        "f_efg_pct",  # Missing in some training seasons, available in inference
        "f_dd2_pg",  # Not in generator DB
        "f_td3_pg",  # Not in generator DB
        "f_plus_minus",  # Not in generator DB
        "f_scr_ast_pg",  # Not in generator DB
        "f_post_touch_pg",  # Not reliably in generator DB
    ]
    for col in drop_cols:
        if col in feature_df.columns:
            feature_df.drop(columns=[col], inplace=True)

    # ── Percentile rankings (CRITICAL for distinguishing elite players) ─
    # Only compute percentiles for features reliably available at inference
    pct_cols = [
        "f_pg_pts",
        "f_pg_reb",
        "f_pg_ast",
        "f_pg_stl",
        "f_pg_blk",
        "f_pg_tov",
        "f_pg_oreb",
        "f_pg_dreb",
        "f_pg_fgm",
        "f_pg_fga",
        "f_pg_fg3m",
        "f_pg_fg3a",
        "f_pg_ftm",
        "f_pg_fta",
        "f_36_pts",
        "f_36_reb",
        "f_36_ast",
        "f_36_blk",
        "f_36_stl",
        "f_fg_pct",
        "f_fg3_pct",
        "f_ft_pct",
        "f_ts_pct",
        "f_fg3a_rate",
        "f_ft_rate",
        "f_ast_tov_ratio",
        "f_usg",
        "f_ast_pct",
        "f_oreb_pct",
        "f_dreb_pct",
        "f_tov_pct",
        "f_drives_pg",
        "f_drive_fg_pct",
        "f_drive_ast_pct",
        "f_touches_pg",
        "f_paint_touch_pg",
        "f_pts_per_touch",
        "f_passes_pg",
        "f_pot_ast_pg",
        "f_ast_pass_pct",
        "f_sec_ast_pg",
        "f_cs_fg3a_pg",
        "f_cs_fg_pct",
        "f_pu_fg3a_pg",
        "f_pu_fg_pct",
        "f_avg_speed",
        "f_avg_speed_off",
        "f_deflections_pg",
        "f_contested_pg",
        "f_contested3_pg",
        "f_boxouts_pg",
        "f_height",
        "f_weight",
    ]
    # Only compute percentiles for columns that exist
    existing_pct_cols = [c for c in pct_cols if c in feature_df.columns]
    if existing_pct_cols:
        pct_df = _compute_percentiles(feature_df, existing_pct_cols)
        feature_df = pd.concat([feature_df, pct_df], axis=1)

    return feature_df


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    """Get list of feature column names, EXCLUDING all attribute/target columns."""
    # Only use engineered f_ and pct_ features
    feature_cols = [c for c in df.columns if c.startswith("f_") or c.startswith("pct_")]

    if not feature_cols:
        # Fallback: use all numeric columns except known exclusions
        exclude_cols = {
            "Player",
            "Team",
            "source",
            "name_normalized",
            "POSITION",
            "pos",
            "PLAYER_ID",
            "PLAYER_NAME",
            "TEAM_ID",
            "TEAM_ABBREVIATION",
            "NICKNAME",
            "SEASON",
            "SEASON_TYPE",
            "MEASURE_TYPE",
            "season",
            "SEASON_ID",
            "position_group",
            "_name_norm",
            "Player_feat",
            "Team_feat",
        }
        exclude_cols |= ATTRIBUTE_COL_NAMES

        for col in df.columns:
            if col in exclude_cols:
                continue
            if any(isinstance(v, str) for v in df[col].dropna().head(10)):
                continue
            feature_cols.append(col)

    return feature_cols


def prepare_training_data(df: pd.DataFrame) -> tuple:
    """Prepare X (features) and y (targets) for training."""
    feature_cols = get_feature_columns(df)
    attribute_cols = [a for a in ATTRIBUTE_NAMES if a in df.columns]

    X = df[feature_cols].copy()
    y = df[attribute_cols].copy()
    positions = (
        df["position_group"].copy()
        if "position_group" in df.columns
        else pd.Series("guard", index=df.index)
    )

    X = X.apply(pd.to_numeric, errors="coerce")
    y = y.apply(pd.to_numeric, errors="coerce")
    X = X.fillna(0)
    y = y.fillna(50)

    return X, y, positions, feature_cols, attribute_cols


if __name__ == "__main__":
    from .data_loader import load_training_data

    print("Loading training data...")
    matched, _ = load_training_data()

    print("\nEngineering features...")
    engineered = engineer_features(matched)

    print("Preparing training matrices...")
    X, y, positions, feat_cols, attr_cols = prepare_training_data(engineered)

    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Target matrix shape: {y.shape}")
    print(f"Feature columns: {len(feat_cols)}")
    print(f"Attribute columns: {len(attr_cols)}")
    print(f"\nPosition distribution:")
    print(positions.value_counts())
