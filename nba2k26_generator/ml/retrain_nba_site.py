"""Retrain ML models using only NBA Site data."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import sys
import importlib.util

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))


def load_nba_site_normalization():
    """Load nba_site_normalization module directly."""
    nba_norm_path = BASE_DIR / "nba2k26_generator" / "nba_site_normalization.py"
    spec = importlib.util.spec_from_file_location(
        "nba_site_normalization", nba_norm_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config():
    """Load config module directly."""
    config_path = BASE_DIR / "nba2k26_generator" / "ml" / "config.py"
    spec = importlib.util.spec_from_file_location("config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_models_module():
    """Load models module directly."""
    models_path = BASE_DIR / "nba2k26_generator" / "ml" / "models.py"
    spec = importlib.util.spec_from_file_location("models", models_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


nba_norm = load_nba_site_normalization()
config = load_config()
models_module = load_models_module()

MODELS_DIR = Path(__file__).parent / "models"
ATTRIBUTE_NAMES = config.ATTRIBUTE_NAMES
ML_ATTRIBUTES = config.ML_ATTRIBUTES
HEURISTIC_ATTRIBUTES = config.HEURISTIC_ATTRIBUTES
POSITION_GROUPS = config.POSITION_GROUPS
MODEL_PARAMS = config.MODEL_PARAMS
ENSEMBLE_SEEDS = config.ENSEMBLE_SEEDS

PositionSpecificModels = models_module.PositionSpecificModels
EnsembleModel = models_module.EnsembleModel

from sklearn.metrics import mean_absolute_error, r2_score


def normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    if not isinstance(name, str):
        return ""
    import re

    name = name.upper().strip()
    name = re.sub(r"[^A-Z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


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

    attr_names = ["Player"]
    for i, a in enumerate(df_raw.iloc[attr_row_idx, 2:], start=2):
        if pd.notna(a):
            name = str(a).strip().replace("\n", " ").replace("  ", " ")
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

    player_df["name_normalized"] = player_df["Player"].apply(normalize_name)

    return player_df.reset_index(drop=True)


def load_all_excel_attributes() -> pd.DataFrame:
    """Load attributes from both Excel files."""
    base_dir = Path(__file__).parent.parent.parent
    excel1 = base_dir / "Player Roles" / "Attributes one.xlsx"
    excel2 = base_dir / "Player Roles" / "attributes two.xlsx"

    print(f"Loading {excel1}...")
    df1 = load_excel_attributes(excel1)
    print(f"  Loaded {len(df1)} players")

    print(f"Loading {excel2}...")
    df2 = load_excel_attributes(excel2)
    print(f"  Loaded {len(df2)} players")

    df1["source"] = "one"
    df2["source"] = "two"

    combined = pd.concat([df1, df2], ignore_index=True)
    combined = combined.drop_duplicates(subset=["name_normalized"], keep="first")

    print(f"Combined unique players: {len(combined)}")
    return combined


def get_nba_site_features_for_training() -> pd.DataFrame:
    """Load and combine features from all NBA Site seasons."""
    base_dir = Path(__file__).parent.parent.parent
    seasons = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]

    all_rows = []

    for season in seasons:
        season_dir = base_dir / "NBA Site data" / season
        if not season_dir.exists():
            print(f"Season {season} not found, skipping...")
            continue

        print(f"Loading season {season}...")
        try:
            rows = load_nba_site_rows(str(season_dir))
            df = pd.DataFrame(rows)
            df["season"] = season
            all_rows.append(df)
            print(f"  Loaded {len(df)} players")
        except Exception as e:
            print(f"  Error loading {season}: {e}")

    if not all_rows:
        raise ValueError("No NBA Site data loaded!")

    combined = pd.concat(all_rows, ignore_index=True)
    print(f"\nTotal players loaded: {len(combined)}")

    # Normalize player name for matching
    combined["name_normalized"] = combined["player_name"].apply(normalize_name)

    # Aggregate across seasons - use most recent season data for each player
    # But average the per-game and per-36 stats
    agg_dict = {}
    for col in combined.columns:
        if col in [
            "player_id",
            "player_name",
            "name_normalized",
            "team_abbr",
            "position",
            "season",
            "__source_file",
            "__row_index",
            "college",
            "country",
            "draft_year",
            "draft_round",
            "draft_number",
            "height",
            "weight",
            "age",
        ]:
            continue
        if combined[col].dtype in [np.float64, np.int64]:
            agg_dict[col] = "mean"

    if agg_dict:
        aggregated = combined.groupby("name_normalized").agg(agg_dict).reset_index()
        # Keep other columns from most recent entry
        keep_cols = ["name_normalized", "player_name", "position"]
        for col in keep_cols:
            if col in combined.columns:
                temp = (
                    combined.sort_values("season", ascending=False)
                    .groupby("name_normalized")[col]
                    .first()
                    .reset_index()
                )
                aggregated = aggregated.merge(temp, on="name_normalized", how="left")
    else:
        aggregated = combined.drop_duplicates(subset=["name_normalized"], keep="first")

    print(f"Aggregated to {len(aggregated)} unique players")
    return aggregated


def match_players_to_attributes(
    nba_df: pd.DataFrame, attr_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Match NBA Site players to their Excel attributes."""
    matched = nba_df.merge(
        attr_df, on="name_normalized", how="inner", suffixes=("", "_attr")
    )
    print(f"Matched {len(matched)} players with attributes")
    return matched, attr_df


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    """Get feature column names from NBA Site data."""
    exclude_cols = {
        "player_id",
        "player_name",
        "team_id",
        "team_abbr",
        "position",
        "season_label",
        "__source_file",
        "__row_index",
        "name_normalized",
        "college",
        "country",
        "draft_year",
        "draft_round",
        "draft_number",
        "height",
        "weight",
        "age",
        "player_height_inches",
        "player_weight",
        "source",
        "Player",
        "name_normalized",
        "_first_attr",
        "source_attr",
    }

    exclude_prefixes = {"Attr_", "attr_"}

    feature_cols = []
    for col in df.columns:
        if col in exclude_cols:
            continue
        if any(col.startswith(p) for p in exclude_prefixes):
            continue
        if df[col].dtype not in [np.float64, np.int64, np.float32, np.int32]:
            continue
        if df[col].isna().all():
            continue
        feature_cols.append(col)

    return feature_cols


def prepare_training_data(
    matched_df: pd.DataFrame, feature_cols: List[str]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str], List[str]]:
    """Prepare X (features) and y (targets) for training."""
    attribute_cols = [a for a in ATTRIBUTE_NAMES if a in matched_df.columns]

    X = matched_df[feature_cols].copy()
    y = matched_df[attribute_cols].copy()

    positions = matched_df["position"].fillna("SG").values

    X = X.apply(pd.to_numeric, errors="coerce").fillna(0)
    y = y.apply(pd.to_numeric, errors="coerce").fillna(50)

    X = X.values
    y = y.values

    return X, y, positions, feature_cols, attribute_cols


def train_models(
    X: np.ndarray,
    y: np.ndarray,
    positions: np.ndarray,
    feature_cols: List[str],
    attribute_cols: List[str],
) -> PositionSpecificModels:
    """Train position-specific models."""
    models = PositionSpecificModels()
    models.attribute_names = attribute_cols

    position_map = {}
    for pos in ["PG", "SG", "SG-SF"]:
        position_map[pos] = "guard"
    for pos in ["SF", "SF-SG"]:
        position_map[pos] = "wing"
    for pos in ["PF", "C", "PF-C", "C-PF"]:
        position_map[pos] = "big"

    pos_groups = np.array([position_map.get(p, "guard") for p in positions])

    for pos_group in ["guard", "wing", "big"]:
        mask = pos_groups == pos_group
        X_pos = X[mask]
        y_pos = y[mask]

        if len(X_pos) < 20:
            print(f"Warning: {pos_group} has only {len(X_pos)} samples")
            continue

        print(f"\nTraining {pos_group} models ({len(X_pos)} samples)...")

        model = EnsembleModel(n_seeds=3)
        model.fit(X_pos, y_pos, verbose=True)
        models.position_models[pos_group] = model

        # Evaluate
        y_pred = model.predict(X_pos)
        mae = mean_absolute_error(y_pos, y_pred)
        r2 = r2_score(y_pos, y_pred, multioutput="uniform_average")
        print(f"  {pos_group} - MAE: {mae:.2f}, R2: {r2:.3f}")

    return models


def save_models_and_features(
    models: PositionSpecificModels, feature_cols: List[str], attribute_cols: List[str]
):
    """Save models and feature columns."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    models.save_all(MODELS_DIR)

    with open(MODELS_DIR / "feature_columns.txt", "w") as f:
        for col in attribute_cols + feature_cols:
            f.write(col + "\n")

    print(f"\nModels saved to {MODELS_DIR}")
    print(f"Features: {len(feature_cols)}")
    print(f"Attributes: {len(attribute_cols)}")


def main():
    print("=" * 60)
    print("NBA 2K26 ML Retraining - Using NBA Site Data Only")
    print("=" * 60)

    print("\n1. Loading Excel attributes...")
    attr_df = load_all_excel_attributes()

    print("\n2. Loading NBA Site data features...")
    nba_df = get_nba_site_features_for_training()

    print("\n3. Matching players...")
    matched, _ = match_players_to_attributes(nba_df, attr_df)

    if len(matched) < 50:
        print("ERROR: Too few matched players. Check data loading.")
        return

    print("\n4. Preparing features...")
    feature_cols = get_feature_columns(matched)
    print(f"Found {len(feature_cols)} features")

    # Show some key features
    key_features = [
        "per_game_pts_per_game",
        "per_game_ast_per_game",
        "per_game_reb_per_game",
        "per_game_x3pa_per_game",
        "per_game_x3p_percent",
        "per_game_fg_percent",
        "advanced_usg_percent",
        "advanced_ts_percent",
        "tracking_drives_pg",
    ]
    print("Key features available:")
    for f in key_features:
        if f in feature_cols:
            print(f"  - {f}")

    print("\n5. Preparing training matrices...")
    X, y, positions, feat_cols, attr_cols = prepare_training_data(matched, feature_cols)
    print(f"X shape: {X.shape}")
    print(f"y shape: {y.shape}")
    print(f"Position distribution: {np.unique(positions, return_counts=True)}")

    print("\n6. Training models...")
    models = train_models(X, y, positions, feat_cols, attr_cols)

    print("\n7. Saving models...")
    save_models_and_features(models, feat_cols, attr_cols)

    print("\n" + "=" * 60)
    print("Training complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
