"""Retrain ML models using only NBA Site data - Standalone version."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import re
import importlib.util
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import sys

BASE_DIR = Path(__file__).parent.parent.parent
NBA_DATA_DIR = BASE_DIR / "NBA Site data"
PLAYER_ROLES_DIR = BASE_DIR / "Player Roles"
MODELS_DIR = Path(__file__).parent / "models"

SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]

ATTRIBUTE_NAMES = [
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

HEURISTIC_ATTRIBUTES = [
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

ML_ATTRIBUTES = [a for a in ATTRIBUTE_NAMES if a not in HEURISTIC_ATTRIBUTES]

POSITION_GROUPS = {
    "guard": ["PG", "SG", "SG-SF"],
    "wing": ["SF", "SF-SG"],
    "big": ["PF", "C", "PF-C", "C-PF"],
}

MODEL_PARAMS = {
    "n_estimators": 100,
    "max_depth": 4,
    "min_samples_split": 15,
    "min_samples_leaf": 8,
    "learning_rate": 0.1,
    "random_state": 42,
}

ENSEMBLE_SEEDS = [42, 123]


def load_nba_site_normalization():
    """Load the real nba_site_normalization module."""
    nba_norm_path = BASE_DIR / "nba2k26_generator" / "nba_site_normalization.py"
    spec = importlib.util.spec_from_file_location(
        "nba_site_normalization", nba_norm_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    if not isinstance(name, str):
        return ""
    name = name.upper().strip()
    name = re.sub(r"[^A-Z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _to_float(value, default=0.0):
    """Convert value to float safely."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("%", "")
    if not s:
        return default
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return default


def load_nba_site_rows(data_dir: str) -> List[Dict]:
    """Load NBA Site CSVs for a single season."""
    base = Path(data_dir)
    files = sorted(base.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in: {data_dir}")

    import re as _re

    season_tag = None
    for f in files:
        m = _re.search(r"player_traditional_(\d{4}-\d{2})_regular_season\.csv", f.name)
        if m:
            season_tag = m.group(1)
            break
    if season_tag is None:
        raise FileNotFoundError(f"No player_traditional_*_regular_season.csv found")

    def sf(name: str) -> str:
        return name.replace("SEASON", season_tag)

    traditional_path = base / sf("player_traditional_SEASON_regular_season.csv")
    if not traditional_path.exists():
        raise FileNotFoundError(f"Base file not found: {traditional_path.name}")

    traditional_rows = []
    with open(traditional_path, "r", encoding="utf-8-sig") as f:
        import csv

        reader = csv.DictReader(f)
        for row in reader:
            traditional_rows.append(row)

    traditional_idx = {}
    for row in traditional_rows:
        pid = str(row.get("PLAYER_ID", "")).strip()
        if pid:
            traditional_idx[pid] = row

    merge_files = [
        sf("player_advanced_SEASON_regular_season.csv"),
        sf("player_usage_SEASON_regular_season.csv"),
        sf("player_shooting_by_zone_SEASON_regular_season.csv"),
        sf("player_tracking_speed_distance_SEASON_regular_season.csv"),
        sf("player_tracking_drives_SEASON_regular_season.csv"),
        sf("player_tracking_passing_SEASON_regular_season.csv"),
        sf("player_tracking_touches_SEASON_regular_season.csv"),
        sf("player_tracking_catch_shoot_SEASON_regular_season.csv"),
        sf("player_defense_SEASON_regular_season.csv"),
        sf("player_hustle_SEASON_regular_season.csv"),
        sf("player_defense_dash_overall_SEASON_regular_season.csv"),
        sf("player_defense_dash_3pt_SEASON_regular_season.csv"),
        sf("player_defense_dash_2pt_SEASON_regular_season.csv"),
        sf("player_bio_SEASON_regular_season.csv"),
        sf("player_playtype_spot_up_SEASON_regular_season.csv"),
        sf("player_playtype_ball_handler_SEASON_regular_season.csv"),
        sf("player_playtype_transition_SEASON_regular_season.csv"),
        sf("player_playtype_cut_SEASON_regular_season.csv"),
        sf("player_playtype_roll_man_SEASON_regular_season.csv"),
        sf("player_playtype_isolation_SEASON_regular_season.csv"),
        sf("player_misc_SEASON_regular_season.csv"),
    ]

    merged_idx = {pid: dict(row) for pid, row in traditional_idx.items()}

    for fname in merge_files:
        fp = base / fname
        if not fp.exists():
            continue
        rows = []
        with open(fp, "r", encoding="utf-8-sig") as f:
            import csv

            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        pid_col = "PLAYER_ID"
        if fname.startswith("player_defense_dash_"):
            pid_col = "CLOSE_DEF_PERSON_ID"
        idx = {}
        for row in rows:
            pid = str(row.get(pid_col, "")).strip()
            if pid:
                idx[pid] = row
        for pid, target in merged_idx.items():
            src = idx.get(pid)
            if not src:
                continue
            for k, v in src.items():
                if k in ("PLAYER_ID", pid_col):
                    continue
                target[f"{fname}:{k}"] = v

    out = []
    for pid, row in merged_idx.items():
        row["player_id"] = pid
        row["season"] = season_tag
        out.append(row)

    return out


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
    excel1 = PLAYER_ROLES_DIR / "Attributes one.xlsx"
    excel2 = PLAYER_ROLES_DIR / "attributes two.xlsx"

    print(f"Loading {excel1}...")
    df1 = load_excel_attributes(excel1)
    print(f"  Loaded {len(df1)} players")

    print(f"Loading {excel2}...")
    df2 = load_excel_attributes(excel2)
    print(f"  Loaded {len(df2)} players")

    combined = pd.concat([df1, df2], ignore_index=True)
    combined = combined.drop_duplicates(subset=["name_normalized"], keep="first")

    print(f"Combined unique players: {len(combined)}")
    return combined


def get_nba_site_dataframe() -> pd.DataFrame:
    """Load all NBA Site data into a DataFrame using proper normalization."""
    nba_norm = load_nba_site_normalization()
    all_rows = []
    all_positions = {}

    for season in SEASONS:
        season_dir = NBA_DATA_DIR / season
        if not season_dir.exists():
            print(f"Season {season} not found, skipping...")
            continue

        print(f"Loading season {season}...")
        try:
            # Use the real normalization function
            rows = nba_norm.load_nba_site_rows(str(season_dir))
            for row in rows:
                row["season"] = season
                all_rows.append(row)
            print(f"  Loaded {len(rows)} players")
        except Exception as e:
            print(f"  Error loading {season}: {e}")

    if not all_rows:
        raise ValueError("No NBA Site data loaded!")

    df = pd.DataFrame(all_rows)

    # Use position from normalized data
    if "position" in df.columns:
        df["POSITION"] = df["position"].fillna("SG")
    else:
        df["POSITION"] = "SG"

    # Normalize player name
    def get_player_name(row):
        for key in ["player_name", "PLAYER_NAME", "PLAYER_NAME_LAST_FIRST"]:
            if key in row and row[key]:
                return normalize_name(str(row[key]))
        return ""

    df["name_normalized"] = df.apply(get_player_name, axis=1)

    print(f"\nTotal players loaded: {len(df)}")
    print(f"Position distribution: {df['POSITION'].value_counts().head(10).to_dict()}")
    return df


def extract_numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract numeric features from NBA Site data - focusing on key stats."""
    exclude_cols = {
        "player_id",
        "PLAYER_ID",
        "player_name",
        "PLAYER_NAME",
        "team_id",
        "TEAM_ID",
        "team_abbr",
        "TEAM_ABBREVIATION",
        "season",
        "SEASON",
        "SEASON_TYPE",
        "MEASURE_TYPE",
        "name_normalized",
    }

    exclude_prefixes = {"Attr_", "attr_", "_"}
    exclude_patterns = {"_RANK", "WNBA", "NBA_FANTASY", "_rank"}

    # Key shooting features to prioritize
    key_shooting_features = [
        # Basic per-game
        "per_game_pts_per_game",
        "per_game_ast_per_game",
        "per_game_reb_per_game",
        "per_game_stl_per_game",
        "per_game_blk_per_game",
        "per_game_fga_per_game",
        "per_game_fg_per_game",
        "per_game_fg_percent",
        "per_game_x3pa_per_game",
        "per_game_x3p_per_game",
        "per_game_x3p_percent",
        "per_game_fta_per_game",
        "per_game_ft_per_game",
        "per_game_ft_percent",
        "per_game_oreb_per_game",
        "per_game_dreb_per_game",
        # Advanced
        "advanced_usg_percent",
        "advanced_ts_percent",
        "advanced_ast_percent",
        "advanced_orb_percent",
        "advanced_drb_percent",
        # Tracking - shooting
        "tracking_catch_shoot_fg3_pct",
        "tracking_catch_shoot_efg_pct",
        "tracking_catch_shoot_fg3a_pg",
        "tracking_drives_pg",
        "tracking_drive_fg_pct",
        # Playtype
        "playtype_spot_up_poss_pct",
        "playtype_spot_up_fg_pct",
        "playtype_ball_handler_poss_pct",
        "playtype_ball_handler_fg_pct",
        "playtype_iso_poss_pct",
        "playtype_iso_fg_pct",
        "playtype_transition_poss_pct",
        "playtype_transition_fg_pct",
        # Zone shooting
        "zone_restricted_fga",
        "zone_restricted_fgm",
        "zone_restricted_fg_pct",
        "zone_left_corner_3_fg_pct",
        "zone_right_corner_3_fg_pct",
        "zone_above_break_3_fg_pct",
        "zone_mid_fga",
        "zone_mid_fgm",
        "zone_mid_fg_pct",
        # Shot dashboard
        "shot_dash_zero_drib_fg3_pct",
        "shot_dash_7p_drib_fg_pct",
        "shot_dash_contested_fg_pct",
        "shot_dash_open_fg_pct",
        "shot_dash_wide_open_fg_pct",
    ]

    feature_df = pd.DataFrame()

    # Keep position and name
    if "POSITION" in df.columns:
        feature_df["POSITION"] = df["POSITION"]
    feature_df["name_normalized"] = df["name_normalized"]

    # Add key shooting features first
    for col in key_shooting_features:
        if col in df.columns:
            vals = df[col].apply(lambda x: _to_float(x, np.nan))
            feature_df[col] = pd.to_numeric(vals, errors="coerce").fillna(0)

    # Add other numeric columns
    for col in df.columns:
        if col in exclude_cols or col in feature_df.columns:
            continue
        if any(col.startswith(p) for p in exclude_prefixes):
            continue
        if any(p in col for p in exclude_patterns):
            continue

        vals = df[col].apply(lambda x: _to_float(x, np.nan))
        if vals.notna().sum() < 10:
            continue

        feature_df[col] = pd.to_numeric(vals, errors="coerce").fillna(0)

    return feature_df


def match_players(
    nba_df: pd.DataFrame, attr_df: pd.DataFrame
) -> Tuple[pd.DataFrame, List[str]]:
    """Match NBA Site players to their Excel attributes."""
    matched = nba_df.merge(
        attr_df, on="name_normalized", how="inner", suffixes=("", "_attr")
    )
    print(f"Matched {len(matched)} players with attributes")

    # Preserve position from NBA Site data (not from attributes)
    if "POSITION" in nba_df.columns:
        pos_map = nba_df.drop_duplicates("name_normalized").set_index(
            "name_normalized"
        )["POSITION"]
        matched["POSITION"] = matched["name_normalized"].map(pos_map)

    feature_cols = [
        c
        for c in matched.columns
        if c not in attr_df.columns
        and c
        not in [
            "name_normalized",
            "Player",
            "source",
            "_first_attr",
            "source_attr",
            "POSITION",
        ]
    ]

    print(
        f"Position distribution after match: {matched['POSITION'].value_counts().to_dict()}"
    )
    return matched, feature_cols


class EnsembleModel:
    def __init__(self, base_params=None, n_seeds=3):
        self.base_params = base_params or MODEL_PARAMS
        self.n_seeds = n_seeds
        self.seeds = ENSEMBLE_SEEDS[:n_seeds]
        self.models = []
        self.scaler = MinMaxScaler()
        self.is_fitted = False

    def fit(self, X, y, verbose=False):
        self.models = []
        X_scaled = self.scaler.fit_transform(X)

        for i, seed in enumerate(self.seeds):
            params = self.base_params.copy()
            params["random_state"] = seed
            model = MultiOutputRegressor(GradientBoostingRegressor(**params))
            model.fit(X_scaled, y)
            self.models.append(model)
            if verbose:
                print(f"  Model {i + 1}/{len(self.seeds)} trained (seed={seed})")

        self.is_fitted = True
        return self

    def predict(self, X):
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        X_scaled = self.scaler.transform(X)
        predictions = [model.predict(X_scaled) for model in self.models]
        return np.mean(predictions, axis=0)

    def save(self, filepath):
        joblib.dump(
            {
                "models": self.models,
                "scaler": self.scaler,
                "base_params": self.base_params,
                "seeds": self.seeds,
            },
            filepath,
        )

    @classmethod
    def load(cls, filepath):
        data = joblib.load(filepath)
        instance = cls(base_params=data["base_params"], n_seeds=len(data["seeds"]))
        instance.models = data["models"]
        instance.scaler = data["scaler"]
        instance.seeds = data["seeds"]
        instance.is_fitted = True
        return instance


def train_models(X, y, positions, feature_cols, attribute_cols):
    """Train position-specific models."""
    pos_map = {}
    for pos in ["PG", "SG", "SG-SF"]:
        pos_map[pos] = "guard"
    for pos in ["SF", "SF-SG"]:
        pos_map[pos] = "wing"
    for pos in ["PF", "C", "PF-C", "C-PF"]:
        pos_map[pos] = "big"

    trained_models = {}

    for pos_group in ["guard", "wing", "big"]:
        mask = np.array([pos_map.get(p, "guard") == pos_group for p in positions])
        X_pos = X[mask]
        y_pos = y[mask]

        if len(X_pos) < 20:
            print(f"Warning: {pos_group} has only {len(X_pos)} samples")
            continue

        print(f"\nTraining {pos_group} models ({len(X_pos)} samples)...")

        model = EnsembleModel(n_seeds=3)
        model.fit(X_pos, y_pos, verbose=True)
        trained_models[pos_group] = model

        y_pred = model.predict(X_pos)
        mae = mean_absolute_error(y_pos, y_pred)
        r2 = r2_score(y_pos, y_pred, multioutput="uniform_average")
        print(f"  {pos_group} - MAE: {mae:.2f}, R2: {r2:.3f}")

    return trained_models


def save_models(models, feature_cols, attribute_cols):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    for pos_group, model in models.items():
        filepath = MODELS_DIR / f"model_{pos_group}.joblib"
        model.save(filepath)
        print(f"  Saved {pos_group} model to {filepath}")

    # Only save feature columns (not attributes) for prediction
    with open(MODELS_DIR / "feature_columns.txt", "w") as f:
        for col in feature_cols:
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

    print("\n2. Loading NBA Site data...")
    nba_df = get_nba_site_dataframe()

    print("\n3. Extracting numeric features...")
    feature_df = extract_numeric_features(nba_df)

    print("\n4. Matching players...")
    matched, feature_cols = match_players(feature_df, attr_df)

    if len(matched) < 50:
        print("ERROR: Too few matched players. Check data loading.")
        return

    print(f"Found {len(feature_cols)} features")

    print("\n5. Preparing training matrices...")
    attribute_cols = [a for a in ATTRIBUTE_NAMES if a in matched.columns]
    print(f"Attribute columns found: {len(attribute_cols)}")

    # Limit features to avoid overfitting and speed up training
    MAX_FEATURES = 100
    if len(feature_cols) > MAX_FEATURES:
        print(f"Limiting features from {len(feature_cols)} to {MAX_FEATURES}")
        feature_cols = feature_cols[:MAX_FEATURES]

    X = matched[feature_cols].values
    y = matched[attribute_cols].values

    # Get positions from the data
    positions = []
    for _, row in matched.iterrows():
        pos = str(row.get("POSITION", row.get("position", "SG")))
        positions.append(pos)

    # Clean data
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(y, nan=50.0, posinf=50.0, neginf=50.0)

    print(f"X shape: {X.shape}")
    print(f"y shape: {y.shape}")
    print(f"Position distribution: {pd.Series(positions).value_counts().to_dict()}")

    print("\n6. Training models...")
    models = train_models(X, y, positions, feature_cols, attribute_cols)

    print("\n7. Saving models...")
    save_models(models, feature_cols, attribute_cols)

    print("\n" + "=" * 60)
    print("Training complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
