"""Export sklearn HistGradientBoostingRegressor models to pure Python JSON.

Run ONCE with sklearn available. Output: models_export.json
This allows prediction without importing sklearn/pandas at runtime.
"""
import json
import os
import numpy as np
import joblib

MODELS_DIR = os.path.join(os.path.dirname(__file__), "ml", "models")
POSITION_GROUPS = ["guard", "wing", "big"]
ML_ATTRIBUTES = [
    "Driving Layup", "Standing Dunk", "Driving Dunk", "Close Shot",
    "Mid-Range Shot", "Three-Point Shot", "Free Throw", "Shot IQ",
    "Draw Foul", "Post Hook", "Post Fade", "Post Control",
    "Ball Handle", "Speed with Ball", "Hands", "Pass Accuracy",
    "Pass IQ", "Pass Vision", "Offensive Consistency", "Defensive Consistency",
    "Interior Defense", "Perimeter Defense", "Steal", "Block",
    "Help Defense IQ", "Pass Perception",
    "Offensive Rebound", "Defensive Rebound",
    "Speed", "Agility", "Strength", "Vertical", "Stamina",
    "Hustle", "Overall Durability", "Potential",
]

def extract_tree_predictor(tp):
    """Extract TreePredictor nodes to serializable format."""
    nodes = tp.nodes
    return {
        "value": nodes["value"].tolist(),
        "count": nodes["count"].tolist(),
        "feature_idx": nodes["feature_idx"].tolist(),
        "num_threshold": nodes["num_threshold"].tolist(),
        "missing_go_to_left": nodes["missing_go_to_left"].tolist(),
        "left": nodes["left"].tolist(),
        "right": nodes["right"].tolist(),
        "is_leaf": nodes["is_leaf"].tolist(),
        "is_categorical": nodes["is_categorical"].tolist(),
        "bitset_idx": nodes["bitset_idx"].tolist(),
        "raw_left_cat_bitsets": tp.raw_left_cat_bitsets.tolist() if len(tp.raw_left_cat_bitsets) > 0 else [],
    }

def extract_hgb_model(model):
    """Extract a single HistGradientBoostingRegressor model."""
    trees = []
    for pred_list in model._predictors:
        # pred_list is a list of TreePredictor (one per tree in this iteration)
        for tp in pred_list:
            trees.append(extract_tree_predictor(tp))
    
    # Get baseline prediction
    baseline = model._baseline_prediction
    if hasattr(baseline, 'tolist'):
        baseline = baseline.tolist()
    
    return {
        "trees": trees,
        "n_trees": len(trees),
        "baseline": baseline,
        "learning_rate": model.learning_rate,
        "n_features": model.n_features_in_,
    }

def main():
    export = {}
    
    for pos_group in POSITION_GROUPS:
        pos_dir = os.path.join(MODELS_DIR, pos_group)
        if not os.path.isdir(pos_dir):
            print(f"Skipping {pos_group} - directory not found")
            continue
        
        pos_export = {}
        
        for attr in ML_ATTRIBUTES:
            attr_file = attr.replace(" ", "_")
            model_path = os.path.join(pos_dir, f"model_{pos_group}_{attr_file}.joblib")
            
            if not os.path.exists(model_path):
                print(f"  {pos_group}/{attr}: not found")
                continue
            
            print(f"  Loading {pos_group}/{attr}...")
            data = joblib.load(model_path)
            
            models = data.get("models", [])
            scaler = data.get("scaler")
            
            # Extract scaler params
            scaler_data = None
            if scaler is not None:
                scaler_data = {
                    "center": scaler.center_.tolist() if hasattr(scaler, 'center_') and scaler.center_ is not None else None,
                    "scale": scaler.scale_.tolist() if hasattr(scaler, 'scale_') and scaler.scale_ is not None else None,
                }
            
            # Extract all ensemble models
            ensemble = []
            for m in models:
                ensemble.append(extract_hgb_model(m))
            
            pos_export[attr] = {
                "ensemble": ensemble,
                "scaler": scaler_data,
                "n_models": len(ensemble),
            }
        
        export[pos_group] = pos_export
        print(f"Exported {pos_group}: {len(pos_export)} attributes")
    
    out_path = os.path.join(os.path.dirname(__file__), "models_export.json")
    with open(out_path, "w") as f:
        json.dump(export, f)
    
    print(f"\nSaved to {out_path}")
    print(f"Total: {sum(len(v) for v in export.values())} attributes across {len(export)} position groups")

if __name__ == "__main__":
    main()
