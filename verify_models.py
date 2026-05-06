"""Verify exported models match sklearn predictions."""
import json
import os
import sys
import numpy as np
import joblib

sys.path.insert(0, os.path.dirname(__file__))

MODELS_DIR = os.path.join(os.path.dirname(__file__), "nba2k26_generator", "ml", "models")

# Load one model with sklearn
model_path = os.path.join(MODELS_DIR, "guard", "model_guard_Driving_Layup.joblib")
data = joblib.load(model_path)
sklearn_model = data["models"][0]
scaler = data["scaler"]

# Generate random test features
np.random.seed(42)
n_features = sklearn_model.n_features_in_
X_test = np.random.randn(5, n_features)

# Sklearn prediction
sklearn_preds = sklearn_model.predict(X_test)
print("Sklearn predictions:", sklearn_preds)

# Load exported model
with open(os.path.join(os.path.dirname(__file__), "models_export.json"), "r") as f:
    exported = json.load(f)

# Manual prediction using exported model
from ml_predictor import _scale_features, _predict_hgb_model

attr_data = exported["guard"]["Driving Layup"]
scaler_data = attr_data["scaler"]
ensemble = attr_data["ensemble"]

for i in range(len(X_test)):
    features = X_test[i].tolist()
    scaled = _scale_features(features, scaler_data)
    
    preds = []
    for model_data in ensemble:
        p = _predict_hgb_model(model_data, scaled)
        preds.append(p)
    
    avg = sum(preds) / len(preds)
    print(f"  Sample {i}: sklearn={sklearn_preds[i]:.4f}, exported={avg:.4f}, diff={abs(sklearn_preds[i] - avg):.4f}")
