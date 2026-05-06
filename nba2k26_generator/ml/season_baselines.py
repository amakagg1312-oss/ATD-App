"""Season-level percentile baselines for within-season ranking at inference.

Problem being solved:
    During training, _compute_percentiles() in feature_engineering.py uses
    .rank(pct=True) on the full multi-season merged DataFrame — so each player
    is ranked against the entire training population.

    At inference, engineer_features() is called on a SINGLE-ROW DataFrame
    (one player), so .rank(pct=True) always returns 100% — every pct_* feature
    becomes meaningless noise and the model gets garbage inputs.

Fix:
    During training, compute and save the actual stat distributions for each
    season (full player population, not just matched players). At inference,
    look up the player's season, find where their stats fall in that season's
    distribution, and write correct pct_* values into the feature vector.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

# Percentile breakpoints to store per feature
_PCT_POINTS = [5, 10, 25, 50, 75, 90, 95]
_PCT_LABELS = [f"p{p}" for p in _PCT_POINTS]

# Features we compute baselines for — must match pct_cols in feature_engineering.py
BASELINE_FEATURES = [
    "f_pg_pts", "f_pg_reb", "f_pg_ast", "f_pg_stl", "f_pg_blk",
    "f_pg_tov", "f_pg_oreb", "f_pg_dreb", "f_pg_fgm", "f_pg_fga",
    "f_pg_fg3m", "f_pg_fg3a", "f_pg_ftm", "f_pg_fta",
    "f_36_pts", "f_36_reb", "f_36_ast", "f_36_blk", "f_36_stl",
    "f_fg_pct", "f_fg3_pct", "f_ft_pct", "f_ts_pct",
    "f_fg3a_rate", "f_ft_rate", "f_ast_tov_ratio",
    "f_usg", "f_ast_pct", "f_oreb_pct", "f_dreb_pct", "f_tov_pct",
    "f_drives_pg", "f_drive_fg_pct", "f_drive_ast_pct",
    "f_touches_pg", "f_paint_touch_pg", "f_pts_per_touch",
    "f_passes_pg", "f_pot_ast_pg", "f_ast_pass_pct", "f_sec_ast_pg",
    "f_cs_fg3a_pg", "f_cs_fg_pct",
    "f_pu_fg3a_pg", "f_pu_fg_pct",
    "f_avg_speed", "f_avg_speed_off",
    "f_deflections_pg", "f_contested_pg", "f_contested3_pg", "f_boxouts_pg",
    "f_height", "f_weight",
]


def compute_baselines_from_df(feature_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Compute percentile breakpoints for every f_* feature in a DataFrame.

    Args:
        feature_df: DataFrame already processed by engineer_features(), covering
                    the full player population for a season (not just matched players).

    Returns:
        Dict mapping feature name → {p5: x, p10: x, ..., p95: x}
    """
    baselines: Dict[str, Dict[str, float]] = {}

    for feat in BASELINE_FEATURES:
        if feat not in feature_df.columns:
            continue
        vals = pd.to_numeric(feature_df[feat], errors="coerce").dropna()
        # Need enough samples to be meaningful
        if len(vals) < 15:
            continue
        breakpoints: Dict[str, float] = {}
        for p, label in zip(_PCT_POINTS, _PCT_LABELS):
            breakpoints[label] = float(np.percentile(vals, p))
        baselines[feat] = breakpoints

    return baselines


def _interp_percentile(value: float, breakpoints: Dict[str, float]) -> float:
    """Linearly interpolate where `value` falls in the saved distribution.

    Returns a percentile rank on the 0–100 scale.
    """
    x = [breakpoints[label] for label in _PCT_LABELS]
    y = _PCT_POINTS

    if value <= x[0]:
        return float(y[0])
    if value >= x[-1]:
        return float(y[-1])

    for i in range(len(x) - 1):
        if x[i] <= value <= x[i + 1]:
            dx = x[i + 1] - x[i]
            if dx == 0:
                return float(y[i])
            t = (value - x[i]) / dx
            return y[i] + t * (y[i + 1] - y[i])

    return float(y[-1])


def save_baselines(baselines: Dict, filepath: Path) -> None:
    """Save baselines dict to JSON."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(baselines, f, indent=2)


def load_baselines(filepath: Path) -> Optional[Dict]:
    """Load baselines dict from JSON. Returns None if file missing or corrupt."""
    filepath = Path(filepath)
    if not filepath.exists():
        return None
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception:
        return None


def apply_baselines(
    engineered_df: pd.DataFrame,
    all_baselines: Dict,
    season: Optional[str] = None,
) -> pd.DataFrame:
    """Overwrite pct_* columns in an engineered DataFrame using saved baselines.

    This is the key inference-time fix: instead of relying on .rank(pct=True)
    computed on a single row (which is always 100%), we look up where the player's
    stats fall in the full season distribution.

    Args:
        engineered_df: Output of engineer_features() — may be a single-row df.
        all_baselines:  Dict loaded from season_baselines.json.
                        Keys are season strings ("2024-25") plus "__combined__".
        season:         The player's season (e.g. "2024-25"). If None or not in
                        baselines, falls back to __combined__.

    Returns:
        Copy of engineered_df with pct_* columns replaced by correct values.
    """
    if not all_baselines:
        return engineered_df

    # Pick the right baseline set
    if season and season in all_baselines:
        baselines = all_baselines[season]
    elif "__combined__" in all_baselines:
        baselines = all_baselines["__combined__"]
    else:
        return engineered_df

    result = engineered_df.copy()

    for feat, breakpoints in baselines.items():
        pct_col = f"pct_{feat}"
        if feat not in result.columns:
            continue
        # Overwrite the pct_ column row-by-row
        def _compute_pct(val):
            try:
                v = float(val)
                if np.isnan(v):
                    return 0.0
                return _interp_percentile(v, breakpoints)
            except Exception:
                return 0.0

        result[pct_col] = result[feat].apply(_compute_pct)

    return result


def compute_and_save_baselines(
    seasons,
    data_dir: Path,
    output_path: Path,
    min_games: int = 15,
    min_minutes: int = 150,
    verbose: bool = True,
) -> Dict:
    """Compute season baselines from scratch and save to disk.

    Loads the full (unmatched) player population for each season, engineers
    features, computes percentile breakpoints, then saves to JSON.

    Called once at the end of the training pipeline so the baselines are always
    in sync with the training data.
    """
    from .data_loader import merge_season_data, _find_col
    from .feature_engineering import engineer_features

    all_baselines: Dict[str, Dict] = {}
    all_season_frames = []

    for season in seasons:
        season_dir = Path(data_dir) / season
        if not season_dir.exists():
            if verbose:
                print(f"  [baselines] {season}: no data dir, skipping")
            continue

        if verbose:
            print(f"  [baselines] Loading {season}...")

        merged = merge_season_data(season)
        if merged.empty:
            continue

        # Apply same filters as training
        gp_col = _find_col(merged, ["GP", "G"])
        min_col = _find_col(merged, ["MIN", "MP"])

        if gp_col:
            merged[gp_col] = pd.to_numeric(merged[gp_col], errors="coerce").fillna(0)
            merged = merged[merged[gp_col] >= min_games]

        if min_col and gp_col:
            mins_pg = pd.to_numeric(merged[min_col], errors="coerce").fillna(0)
            gp_vals = pd.to_numeric(merged[gp_col], errors="coerce").fillna(0)
            merged = merged[(mins_pg * gp_vals) >= min_minutes]
        elif min_col:
            merged[min_col] = pd.to_numeric(merged[min_col], errors="coerce").fillna(0)
            merged = merged[merged[min_col] >= min_minutes]

        if merged.empty:
            continue

        if verbose:
            print(f"  [baselines] {season}: {len(merged)} players — engineering features...")

        feat_df = engineer_features(merged)
        season_baselines = compute_baselines_from_df(feat_df)
        all_baselines[season] = season_baselines
        all_season_frames.append(feat_df)

        if verbose:
            print(f"  [baselines] {season}: {len(season_baselines)} features baselined")

    # Combined baseline — used as fallback for historical seasons not in training data
    if all_season_frames:
        if verbose:
            print("  [baselines] Computing combined baseline...")
        combined_df = pd.concat(all_season_frames, ignore_index=True)
        all_baselines["__combined__"] = compute_baselines_from_df(combined_df)

    save_baselines(all_baselines, output_path)
    if verbose:
        seasons_saved = [s for s in all_baselines if s != "__combined__"]
        print(f"  [baselines] Saved {len(seasons_saved)} seasons + combined -> {output_path}")

    return all_baselines
