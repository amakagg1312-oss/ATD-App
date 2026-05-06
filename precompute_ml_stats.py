"""Pre-compute ML feature statistics for pure Python inference.

Run ONCE with pandas/sklearn. Outputs:
- ml_feature_names.json: exact feature column names in order
- ml_feature_stats.json: sorted values for percentile computation
"""
import json
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "nba2k26_generator"))

from ml.data_loader import merge_season_data
from ml.feature_engineering import engineer_features, get_feature_columns

print("Loading training data...")
df = merge_season_data(r"D:\project\NBA Site data")
print(f"Merged: {df.shape}")

if df.empty:
    print("No data loaded. Trying direct CSV load...")
    # Load CSVs directly
    import csv
    from pathlib import Path
    
    all_rows = []
    for season in ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]:
        trad_path = Path(r"D:\project\NBA Site data") / season / f"player_traditional_{season}_regular_season.csv"
        if trad_path.exists():
            df_trad = pd.read_csv(trad_path)
            df_trad["SEASON"] = season
            all_rows.append(df_trad)
    
    if all_rows:
        df = pd.concat(all_rows, ignore_index=True)
        print(f"Loaded {len(df)} rows from CSVs")
    else:
        print("No data found!")
        sys.exit(1)

print("Engineering features...")
engineered = engineer_features(df)

print("Getting feature columns...")
feat_cols = get_feature_columns(engineered)
print(f"Feature columns: {len(feat_cols)}")

# Save feature names
with open(os.path.join(os.path.dirname(__file__), "nba2k26_generator", "ml_feature_names.json"), "w") as f:
    json.dump(feat_cols, f)

# Save feature statistics for percentile computation
# For each feature, save the sorted unique values (for binary search percentile)
print("Computing feature statistics...")
stats = {}
for col in feat_cols:
    if col in engineered.columns:
        vals = pd.to_numeric(engineered[col], errors="coerce").dropna().values
        if len(vals) > 0:
            stats[col] = {
                "sorted": np.sort(vals).tolist(),
                "median": float(np.median(vals)),
                "q1": float(np.percentile(vals, 25)),
                "q3": float(np.percentile(vals, 75)),
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "count": len(vals),
            }

stats_path = os.path.join(os.path.dirname(__file__), "nba2k26_generator", "ml_feature_stats.json")
with open(stats_path, "w") as f:
    json.dump(stats, f)

print(f"Saved {len(stats)} feature statistics to {stats_path}")
print(f"Features: {feat_cols[:10]}... ({len(feat_cols)} total)")
