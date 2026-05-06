"""Pure Python ML predictor - no sklearn/pandas needed.

Reads models_export.json and predicts attributes using tree traversal.
"""
import json
import math
import os

_MODELS_CACHE = None

def _load_models():
    global _MODELS_CACHE
    if _MODELS_CACHE is not None:
        return _MODELS_CACHE
    models_path = os.path.join(os.path.dirname(__file__), "models_export.json")
    if not os.path.exists(models_path):
        return None
    with open(models_path, "r") as f:
        _MODELS_CACHE = json.load(f)
    return _MODELS_CACHE

def _predict_tree(nodes, features):
    """Traverse a single tree and return leaf value."""
    idx = 0
    while True:
        if nodes["is_leaf"][idx]:
            return nodes["value"][idx]
        
        feat_idx = nodes["feature_idx"][idx]
        threshold = nodes["num_threshold"][idx]
        
        if feat_idx < 0 or feat_idx >= len(features):
            # Feature not available, go left (missing goes left)
            idx = nodes["left"][idx]
        elif math.isnan(features[feat_idx]):
            idx = nodes["left"][idx] if nodes["missing_go_to_left"][idx] else nodes["right"][idx]
        elif features[feat_idx] <= threshold:
            idx = nodes["left"][idx]
        else:
            idx = nodes["right"][idx]

def _predict_hgb_model(model_data, features):
    """Predict using one HistGradientBoostingRegressor model."""
    baseline = model_data["baseline"]
    if isinstance(baseline, list):
        if isinstance(baseline[0], list):
            pred = baseline[0][0]
        else:
            pred = baseline[0]
    else:
        pred = baseline
    
    lr = model_data["learning_rate"]
    
    for tree in model_data["trees"]:
        leaf_val = _predict_tree(tree, features)
        pred += lr * leaf_val
    
    return pred

def _scale_features(features, scaler_data):
    """Apply RobustScaler transformation."""
    if scaler_data is None or scaler_data.get("center") is None:
        return features
    
    center = scaler_data["center"]
    scale = scaler_data["scale"]
    
    scaled = []
    for i, v in enumerate(features):
        if math.isnan(v):
            scaled.append(0.0)
            continue
        c = center[i] if i < len(center) else 0
        s = scale[i] if i < len(scale) else 1
        if s == 0:
            scaled.append(0.0)
        else:
            scaled.append((v - c) / s)
    return scaled

def predict_attribute(pos_group, attr_name, features):
    """Predict one attribute for a player.
    
    Args:
        pos_group: "guard", "wing", or "big"
        attr_name: attribute name like "Driving Layup"
        features: list of feature values (must match model's expected order)
    
    Returns:
        Predicted attribute value (int, 25-99)
    """
    models = _load_models()
    if models is None:
        return 50
    
    pos_data = models.get(pos_group)
    if pos_data is None:
        return 50
    
    attr_data = pos_data.get(attr_name)
    if attr_data is None:
        return 50
    
    ensemble = attr_data.get("ensemble", [])
    scaler_data = attr_data.get("scaler")
    
    if not ensemble:
        return 50
    
    # Scale features
    scaled = _scale_features(features, scaler_data)
    
    # Average predictions across ensemble models
    preds = []
    for model_data in ensemble:
        p = _predict_hgb_model(model_data, scaled)
        preds.append(p)
    
    avg = sum(preds) / len(preds)
    return max(25, min(99, int(round(avg))))

def detect_position_group(position):
    """Detect position group from position string."""
    pos = str(position or "").upper()
    if "C" in pos and "PF" not in pos:
        return "big"
    if "PF" in pos or "C" in pos:
        return "big"
    if "SF" in pos or "SG" in pos or "PF" in pos:
        return "wing"
    return "guard"
