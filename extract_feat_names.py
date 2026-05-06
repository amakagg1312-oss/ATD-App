"""Extract exact feature column names from the trained models' scaler."""
import json
import os
import sys
import numpy as np
import joblib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "nba2k26_generator"))
from ml.data_loader import merge_season_data
from ml.feature_engineering import engineer_features, get_feature_columns

# Load training data
db_dir = r"D:\project\NBA Site data"
print("Loading training data...")
df = merge_season_data(db_dir)
print(f"Merged: {df.shape}")

print("Engineering features...")
engineered = engineer_features(df)

print("Getting feature columns...")
feat_cols = get_feature_columns(engineered)
print(f"Feature columns: {len(feat_cols)}")
print(f"Features: {feat_cols}")

# Save to JSON
with open(r"D:\project\nba2k26_generator\ml_feature_names.json", "w") as f:
    json.dump(feat_cols, f)
