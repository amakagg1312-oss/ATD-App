"""Data loading and player matching for ML training."""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .config import (
    NBA_DATA_DIR,
    PLAYER_ROLES_DIR,
    MIN_GAMES_PLAYED,
    MIN_MINUTES_PLAYED,
    SEASONS,
)


def normalize_name(name: str) -> str:
    """Normalize player name for matching.

    Transliterates accented characters (ć→C, č→C, etc.) before stripping
    so names like Jokić match Jokic.
    """
    if not isinstance(name, str):
        return ""
    import unicodedata

    # Decompose accented characters and strip combining marks
    # e.g. ć -> c + combining acute -> c
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))

    ascii_name = ascii_name.upper().strip()
    ascii_name = re.sub(r"[^A-Z0-9\s]", "", ascii_name)
    ascii_name = re.sub(r"\s+", " ", ascii_name)
    return ascii_name


def _safe_read_csv(filepath: Path) -> pd.DataFrame:
    """Read CSV with error handling."""
    try:
        return pd.read_csv(filepath)
    except Exception:
        return pd.DataFrame()


def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find first matching column name (case-insensitive)."""
    col_map = {c.upper(): c for c in df.columns}
    for candidate in candidates:
        if candidate.upper() in col_map:
            return col_map[candidate.upper()]
    return None


def _add_name_norm(df: pd.DataFrame) -> pd.DataFrame:
    """Add _name_norm column to dataframe using best available name column."""
    name_col = _find_col(df, ["PLAYER_NAME", "player_name"])
    if not name_col:
        return df
    df["_name_norm"] = df[name_col].apply(normalize_name)
    return df


def _merge_by_name(
    base: pd.DataFrame, other: pd.DataFrame, suffix: str
) -> pd.DataFrame:
    """Merge two dataframes by normalized name, dropping duplicate name columns from other."""
    if other.empty or "_name_norm" not in other.columns:
        return base
    if "_name_norm" not in base.columns:
        return base

    # Drop name columns from other to avoid conflicts
    drop_cols = []
    for c in [
        "PLAYER_NAME",
        "player_name",
        "PLAYER_ID",
        "player_id",
        "TEAM_ID",
        "TEAM_ABBREVIATION",
        "TEAM_NAME",
        "team_abbreviation",
    ]:
        if c in other.columns:
            drop_cols.append(c)
    other_clean = other.drop(columns=drop_cols, errors="ignore")

    return base.merge(
        other_clean, on="_name_norm", how="left", suffixes=("", f"_{suffix}")
    )


def load_season_traditional(season: str) -> pd.DataFrame:
    filepath = NBA_DATA_DIR / season / f"player_traditional_{season}_regular_season.csv"
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_advanced(season: str) -> pd.DataFrame:
    filepath = NBA_DATA_DIR / season / f"player_advanced_{season}_regular_season.csv"
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_shooting(season: str) -> pd.DataFrame:
    filepath = NBA_DATA_DIR / season / f"player_shooting_{season}_regular_season.csv"
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_tracking_drives(season: str) -> pd.DataFrame:
    filepath = (
        NBA_DATA_DIR / season / f"player_tracking_drives_{season}_regular_season.csv"
    )
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_tracking_passing(season: str) -> pd.DataFrame:
    filepath = (
        NBA_DATA_DIR / season / f"player_tracking_passing_{season}_regular_season.csv"
    )
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_tracking_touches(season: str) -> pd.DataFrame:
    filepath = (
        NBA_DATA_DIR / season / f"player_tracking_touches_{season}_regular_season.csv"
    )
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_tracking_speed(season: str) -> pd.DataFrame:
    filepath = (
        NBA_DATA_DIR
        / season
        / f"player_tracking_speed_distance_{season}_regular_season.csv"
    )
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_hustle(season: str) -> pd.DataFrame:
    filepath = NBA_DATA_DIR / season / f"player_hustle_{season}_regular_season.csv"
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_bio(season: str) -> pd.DataFrame:
    filepath = NBA_DATA_DIR / season / f"player_bio_{season}_regular_season.csv"
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_defense(season: str) -> pd.DataFrame:
    filepath = NBA_DATA_DIR / season / f"player_defense_{season}_regular_season.csv"
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_playtype(season: str, playtype: str) -> pd.DataFrame:
    filename = f"player_playtype_{playtype}_{season}_regular_season.csv"
    filepath = NBA_DATA_DIR / season / filename
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_tracking_catch_shoot(season: str) -> pd.DataFrame:
    filepath = (
        NBA_DATA_DIR
        / season
        / f"player_tracking_catch_shoot_{season}_regular_season.csv"
    )
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_tracking_pullup(season: str) -> pd.DataFrame:
    filepath = (
        NBA_DATA_DIR / season / f"player_tracking_pullup_{season}_regular_season.csv"
    )
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_scoring_by_zone(season: str) -> pd.DataFrame:
    filepath = (
        NBA_DATA_DIR / season / f"player_scoring_by_zone_{season}_regular_season.csv"
    )
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def load_season_scoring(season: str) -> pd.DataFrame:
    filepath = NBA_DATA_DIR / season / f"player_scoring_{season}_regular_season.csv"
    if not filepath.exists():
        return pd.DataFrame()
    df = _safe_read_csv(filepath)
    if df.empty:
        return df
    df["season"] = season
    return _add_name_norm(df)


def merge_season_data(season: str) -> pd.DataFrame:
    """Merge all data sources for a single season into one row per player."""
    trad = load_season_traditional(season)
    if trad.empty:
        return pd.DataFrame()

    base = trad.copy()

    # Merge all additional data sources by normalized name
    loaders = [
        (load_season_advanced, "adv"),
        (load_season_shooting, "shoot"),
        (load_season_tracking_drives, "drv"),
        (load_season_tracking_passing, "tpas"),
        (load_season_tracking_touches, "ttch"),
        (load_season_tracking_speed, "tspd"),
        (load_season_hustle, "hus"),
        (load_season_defense, "defn"),
        (load_season_bio, "bio"),
        (load_season_tracking_catch_shoot, "cs"),
        (load_season_tracking_pullup, "pu"),
        (load_season_scoring_by_zone, "sz"),
        (load_season_scoring, "sc"),
    ]

    for loader, suffix in loaders:
        try:
            df = loader(season)
            if not df.empty:
                base = _merge_by_name(base, df, suffix)
        except Exception as e:
            print(f"  Warning: {suffix} merge failed: {e}")

    # Merge playtypes
    for pt in [
        "spot_up",
        "ball_handler",
        "isolation",
        "transition",
        "off_screen",
        "cut",
        "roll_man",
    ]:
        try:
            df = load_season_playtype(season, pt)
            if not df.empty:
                base = _merge_by_name(base, df, f"pt_{pt}")
        except Exception:
            pass

    return base


def load_excel_attributes(filepath: Path) -> pd.DataFrame:
    """Load player attributes from Excel file."""
    df_raw = pd.read_excel(filepath, header=None)

    attr_row_idx = None
    for i in range(min(10, len(df_raw))):
        val = df_raw.iloc[i, 1]
        if pd.notna(val) and isinstance(val, str) and "Attributes" in str(val):
            attr_row_idx = i
            break

    if attr_row_idx is None:
        return pd.DataFrame()

    data_start = attr_row_idx + 1
    while data_start < len(df_raw) and pd.isna(df_raw.iloc[data_start, 1]):
        data_start += 1

    # Map messy Excel column names to canonical attribute names
    _EXCEL_NAME_FIXES = {
        "Free Thow": "Free Throw",
        "Free Throw": "Free Throw",
    }

    attr_names = ["Player"]
    for i, a in enumerate(df_raw.iloc[attr_row_idx, 2:], start=2):
        if pd.notna(a):
            name = str(a).strip().replace("\n", " ").replace("  ", " ")
            # Strip parenthetical suffixes like "(Second To last)" or "(Last)"
            if "(" in name:
                name = name[: name.index("(")].strip()
            # Apply known fixes
            name = _EXCEL_NAME_FIXES.get(name, name)
            attr_names.append(name)
        else:
            attr_names.append(f"Attr_{i}")

    df_data = df_raw.iloc[data_start:].copy()
    df_data = df_data.reset_index(drop=True)

    player_names = df_data.iloc[:, 1].values
    first_attrs = (
        df_data.iloc[:, 2].values
        if len(df_data.columns) > 2
        else [np.nan] * len(df_data)
    )

    player_df = pd.DataFrame({"Player": player_names, "_first_attr": first_attrs})

    for i, attr_name in enumerate(attr_names[1:], start=2):
        player_df[attr_name] = (
            pd.to_numeric(df_data.iloc[:, i], errors="coerce")
            if i < len(df_data.columns)
            else np.nan
        )

    player_df = player_df[player_df["Player"].notna()]
    player_df = player_df[player_df["_first_attr"].notna()]
    player_df = player_df[player_df["Player"].astype(str).str.len() >= 3]
    player_df = player_df.drop(columns=["_first_attr"])

    # Fix Excel typo: "Free Thow" -> "Free Throw"
    player_df = player_df.rename(columns={"Free Thow": "Free Throw"})

    return player_df.reset_index(drop=True)


def load_all_label_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load and combine attributes from both Excel files."""
    excel1 = PLAYER_ROLES_DIR / "Attributes one.xlsx"
    excel2 = PLAYER_ROLES_DIR / "attributes two.xlsx"

    print(f"Loading {excel1}...")
    df1 = load_excel_attributes(excel1)
    print(f"  Loaded {len(df1)} players")

    print(f"Loading {excel2}...")
    df2 = load_excel_attributes(excel2)
    print(f"  Loaded {len(df2)} players")

    df1["source"] = "one"
    df2["source"] = "two"

    combined = pd.concat([df1, df2], ignore_index=True)
    combined["name_normalized"] = combined["Player"].apply(normalize_name)
    combined = combined.drop_duplicates(subset=["name_normalized"], keep="first")

    print(f"Combined unique players: {len(combined)}")
    return combined, df1


def load_training_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load and prepare all training data.

    Returns:
        matched: DataFrame with features + attributes for training
        labels_df: Original labels DataFrame
    """
    print("Loading Excel attribute labels...")
    labels_df, df_one = load_all_label_data()

    all_matched_rows = []

    for season in SEASONS:
        season_dir = NBA_DATA_DIR / season
        if not season_dir.exists():
            continue

        print(f"\nProcessing season {season}...")
        merged = merge_season_data(season)
        if merged.empty:
            continue

        print(f"  {len(merged)} players loaded")

        # Filter by minimum games/minutes
        gp_col = _find_col(merged, ["GP", "G"])
        min_col = _find_col(merged, ["MIN", "MP"])
        if gp_col:
            merged[gp_col] = pd.to_numeric(merged[gp_col], errors="coerce").fillna(0)
            merged = merged[merged[gp_col] >= MIN_GAMES_PLAYED]
        # MIN column is per-game minutes (e.g. 22.7), not total.
        # Compute total minutes for filtering.
        if min_col and gp_col:
            mins_pg = pd.to_numeric(merged[min_col], errors="coerce").fillna(0)
            gp_vals = pd.to_numeric(merged[gp_col], errors="coerce").fillna(0)
            total_mins = mins_pg * gp_vals
            merged = merged[total_mins >= MIN_MINUTES_PLAYED]
        elif min_col:
            merged[min_col] = pd.to_numeric(merged[min_col], errors="coerce").fillna(0)
            merged = merged[merged[min_col] >= MIN_MINUTES_PLAYED]

        print(f"  {len(merged)} players after filtering")

        # Ensure name_normalized exists for merge with labels
        if "name_normalized" not in merged.columns and "_name_norm" in merged.columns:
            merged["name_normalized"] = merged["_name_norm"]

        if "name_normalized" not in merged.columns:
            print("  WARNING: No name_normalized column, skipping")
            continue

        # Match to labels
        matched = labels_df.merge(
            merged, on="name_normalized", how="inner", suffixes=("", f"_feat")
        )
        print(f"  {len(matched)} matched to labels")

        if len(matched) > 0:
            matched["season"] = season
            # Ensure name_normalized exists (labels uses this name)
            if (
                "name_normalized" not in matched.columns
                and "_name_norm" in matched.columns
            ):
                matched["name_normalized"] = matched["_name_norm"]
            all_matched_rows.append(matched)

    if not all_matched_rows:
        print("ERROR: No matched data found!")
        return pd.DataFrame(), labels_df

    combined = pd.concat(all_matched_rows, ignore_index=True)
    print(f"\nTotal training samples (per-season): {len(combined)}")

    combined = combined.drop_duplicates(
        subset=["name_normalized", "season"], keep="first"
    )
    print(f"After dedup: {len(combined)}")

    return combined, labels_df


def load_positions_from_bio() -> pd.DataFrame:
    """Load positions for all players from bio files."""
    all_positions = []
    for season in SEASONS:
        bio_path = NBA_DATA_DIR / season / f"player_bio_{season}_regular_season.csv"
        if not bio_path.exists():
            continue
        try:
            df = pd.read_csv(bio_path)
            pos_col = _find_col(df, ["POSITION", "position"])
            name_col = _find_col(df, ["PLAYER_NAME", "player_name"])
            if not pos_col or not name_col:
                continue
            df["name_normalized"] = df[name_col].apply(normalize_name)
            positions = df[["name_normalized", pos_col]].copy()
            positions = positions.rename(columns={pos_col: "POSITION"})
            all_positions.append(positions)
        except Exception:
            continue

    if not all_positions:
        return pd.DataFrame()

    combined = pd.concat(all_positions, ignore_index=True)
    combined = combined.drop_duplicates(subset=["name_normalized"], keep="first")
    return combined


if __name__ == "__main__":
    matched, labels = load_training_data()
    print(f"\nFinal training set: {len(matched)} samples")
    if len(matched) > 0:
        print(f"Columns: {len(matched.columns)}")
