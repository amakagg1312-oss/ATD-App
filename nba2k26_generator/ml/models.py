"""ML Models for NBA 2K26 Attribute Prediction.

Uses per-attribute HistGradientBoostingRegressor models instead of
MultiOutputRegressor to avoid regression-to-the-mean and properly
capture elite player attribute values.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
from pathlib import Path
from .config import (
    MODELS_DIR,
    ATTRIBUTE_NAMES,
    ML_ATTRIBUTES,
    HEURISTIC_ATTRIBUTES,
    CONSTANT_ATTRIBUTES,
    POSITION_GROUPS,
)

# Per-attribute model params - fast and accurate
MODEL_PARAMS = {
    "max_iter": 500,
    "max_depth": 6,
    "learning_rate": 0.05,
    "min_samples_leaf": 5,
    "max_leaf_nodes": 31,
    "l2_regularization": 1.0,
    "random_state": 42,
    "early_stopping": True,
    "validation_fraction": 0.15,
    "n_iter_no_change": 20,
}

ENSEMBLE_SEEDS = [42, 123, 456]


class AttributeModel:
    """Single model for one attribute, with ensemble."""

    def __init__(self, attr_name: str, base_params: Dict = None, n_seeds: int = 3):
        self.attr_name = attr_name
        self.base_params = base_params or MODEL_PARAMS
        self.n_seeds = n_seeds
        self.seeds = ENSEMBLE_SEEDS[:n_seeds]
        self.models = []
        self.scaler = RobustScaler()
        self.is_fitted = False

    def fit(
        self, X: np.ndarray, y: np.ndarray, verbose: bool = False
    ) -> "AttributeModel":
        """Fit ensemble of models for this attribute."""
        self.models = []
        X_scaled = self.scaler.fit_transform(X)

        for i, seed in enumerate(self.seeds):
            params = self.base_params.copy()
            params["random_state"] = seed

            model = HistGradientBoostingRegressor(**params)
            model.fit(X_scaled, y)
            self.models.append(model)

            if verbose:
                score = model.score(X_scaled, y)
                print(
                    f"    {self.attr_name}: model {i + 1}/{len(self.seeds)} (R²={score:.3f})"
                )

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict using ensemble average."""
        if not self.is_fitted:
            raise ValueError(f"Model for {self.attr_name} not fitted")

        X_scaled = self.scaler.transform(X)
        predictions = []
        for model in self.models:
            pred = model.predict(X_scaled)
            predictions.append(pred)

        return np.mean(predictions, axis=0)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Evaluate model performance."""
        y_pred = self.predict(X)
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        return {"mae": mae, "r2": r2}

    def save(self, filepath: Path):
        """Save model to file."""
        joblib.dump(
            {
                "models": self.models,
                "scaler": self.scaler,
                "base_params": self.base_params,
                "seeds": self.seeds,
                "attr_name": self.attr_name,
            },
            filepath,
        )

    @classmethod
    def load(cls, filepath: Path) -> "AttributeModel":
        """Load model from file."""
        data = joblib.load(filepath)
        instance = cls(
            attr_name=data["attr_name"],
            base_params=data["base_params"],
            n_seeds=len(data["seeds"]),
        )
        instance.models = data["models"]
        instance.scaler = data["scaler"]
        instance.seeds = data["seeds"]
        instance.is_fitted = True
        return instance


class PositionAttributeModels:
    """Collection of per-attribute models for one position group."""

    def __init__(self, position_group: str, attribute_names: List[str] = None):
        self.position_group = position_group
        self.attr_names = attribute_names or ML_ATTRIBUTES
        self.models: Dict[str, AttributeModel] = {}

    def fit(
        self, X: np.ndarray, y: np.ndarray, verbose: bool = False
    ) -> "PositionAttributeModels":
        """Train per-attribute models."""
        for i, attr in enumerate(self.attr_names):
            if verbose:
                print(
                    f"  [{self.position_group}] Training {attr} ({i + 1}/{len(self.attr_names)})"
                )

            y_attr = y[:, i]
            model = AttributeModel(attr, n_seeds=3)
            model.fit(X, y_attr, verbose=verbose)
            self.models[attr] = model

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict all attributes for a player."""
        results = np.zeros((X.shape[0], len(self.attr_names)))
        for i, attr in enumerate(self.attr_names):
            if attr in self.models:
                results[:, i] = self.models[attr].predict(X)
            else:
                results[:, i] = 50  # default
        return results

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Dict[str, float]]:
        """Evaluate all attribute models."""
        results = {}
        for attr, model in self.models.items():
            idx = self.attr_names.index(attr)
            y_attr = y[:, idx]
            results[attr] = model.evaluate(X, y_attr)
        return results

    def save(self, directory: Path):
        """Save all attribute models."""
        directory.mkdir(parents=True, exist_ok=True)
        for attr, model in self.models.items():
            filepath = (
                directory
                / f"model_{self.position_group}_{attr.replace(' ', '_')}.joblib"
            )
            model.save(filepath)

    @classmethod
    def load(
        cls, position_group: str, attribute_names: List[str], directory: Path
    ) -> "PositionAttributeModels":
        """Load all attribute models for a position group."""
        instance = cls(position_group, attribute_names)
        for attr in attribute_names:
            filepath = (
                directory / f"model_{position_group}_{attr.replace(' ', '_')}.joblib"
            )
            if filepath.exists():
                instance.models[attr] = AttributeModel.load(filepath)
        return instance


class PositionSpecificModels:
    """Collection of position-specific per-attribute models."""

    def __init__(self):
        self.position_models: Dict[str, PositionAttributeModels] = {}
        self.attribute_names = ML_ATTRIBUTES
        self.position_groups = list(POSITION_GROUPS.keys())

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.DataFrame,
        positions: pd.Series,
        verbose: bool = False,
    ) -> "PositionSpecificModels":
        """Train models for each position group."""
        X_arr = X.values if hasattr(X, "values") else X
        y_arr = y.values if hasattr(y, "values") else y

        for pos_group in self.position_groups:
            mask = positions == pos_group
            X_pos = X_arr[mask]
            y_pos = y_arr[mask]

            if len(X_pos) < 20:
                if verbose:
                    print(
                        f"  Warning: {pos_group} has only {len(X_pos)} samples, skipping"
                    )
                continue

            if verbose:
                print(
                    f"\nTraining {pos_group} models ({len(X_pos)} samples, {len(self.attribute_names)} attributes)..."
                )

            pos_models = PositionAttributeModels(pos_group, self.attribute_names)
            pos_models.fit(X_pos, y_pos, verbose=verbose)
            self.position_models[pos_group] = pos_models

        return self

    def predict(
        self, X: np.ndarray, position_group: str = None, default_group: str = "guard"
    ) -> np.ndarray:
        """Predict attributes for a player."""
        if len(X.shape) == 1:
            X = X.reshape(1, -1)

        if position_group and position_group in self.position_models:
            return self.position_models[position_group].predict(X)

        if default_group in self.position_models:
            return self.position_models[default_group].predict(X)

        if self.position_models:
            first_model = next(iter(self.position_models.values()))
            return first_model.predict(X)

        raise ValueError("No models available")

    def evaluate_all(
        self, X: pd.DataFrame, y: pd.DataFrame, positions: pd.Series
    ) -> Dict:
        """Evaluate all position models."""
        results = {}
        X_arr = X.values if hasattr(X, "values") else X
        y_arr = y.values if hasattr(y, "values") else y

        for pos_group, pos_models in self.position_models.items():
            mask = positions == pos_group
            X_pos = X_arr[mask]
            y_pos = y_arr[mask]

            if len(X_pos) < 10:
                continue

            eval_results = pos_models.evaluate(X_pos, y_pos)

            # Aggregate metrics
            avg_mae = np.mean([r["mae"] for r in eval_results.values()])
            avg_r2 = np.mean([r["r2"] for r in eval_results.values()])

            results[pos_group] = {
                "avg_mae": avg_mae,
                "avg_r2": avg_r2,
                "sample_count": len(X_pos),
                "attribute_results": eval_results,
            }

        return results

    def save_all(self, directory: Path = None):
        """Save all position models."""
        directory = directory or MODELS_DIR
        directory.mkdir(parents=True, exist_ok=True)

        for pos_group, pos_models in self.position_models.items():
            pos_models.save(directory / pos_group)

    @classmethod
    def load_all(cls, directory: Path = None) -> "PositionSpecificModels":
        """Load all position models."""
        directory = directory or MODELS_DIR
        instance = cls()

        for pos_group in POSITION_GROUPS.keys():
            pos_dir = directory / pos_group
            if pos_dir.exists():
                pos_models = PositionAttributeModels.load(
                    pos_group, instance.attribute_names, pos_dir
                )
                if pos_models.models:
                    instance.position_models[pos_group] = pos_models

        return instance


class AttributePredictor:
    """Main predictor combining ML and heuristics."""

    def __init__(self):
        self.ml_models: Optional[PositionSpecificModels] = None
        self.models_loaded = False

    def load_models(self, directory: Path = None) -> bool:
        """Load trained models."""
        try:
            self.ml_models = PositionSpecificModels.load_all(directory)
            self.models_loaded = True
            return True
        except Exception as e:
            print(f"Failed to load models: {e}")
            self.models_loaded = False
            return False

    def predict_attributes(
        self,
        X: np.ndarray,
        position_group: str = None,
    ) -> Dict[str, float]:
        """Predict all attributes using ML (except constants like Intangibles=25)."""
        if not self.models_loaded or self.ml_models is None:
            raise ValueError("Models not loaded")

        if len(X.shape) == 1:
            X = X.reshape(1, -1)

        ml_predictions = self.ml_models.predict(X, position_group)

        attributes = {}

        for i, attr in enumerate(ML_ATTRIBUTES):
            pred_val = (
                ml_predictions[0][i]
                if len(ml_predictions.shape) > 1
                else ml_predictions[i]
            )
            attributes[attr] = max(25, min(99, int(round(pred_val))))

        # Set constant attributes
        for attr, val in CONSTANT_ATTRIBUTES.items():
            attributes[attr] = val

        return attributes

    def predict_overall(self, attributes: Dict[str, float]) -> int:
        """Calculate overall rating from attributes."""
        finishing = ["Driving Layup", "Standing Dunk", "Driving Dunk", "Close Shot"]
        shooting = ["Mid-Range Shot", "Three-Point Shot", "Free Throw", "Shot IQ"]
        playmaking = [
            "Ball Handle",
            "Speed with Ball",
            "Pass Accuracy",
            "Pass IQ",
            "Pass Vision",
        ]
        defense = ["Interior Defense", "Perimeter Defense", "Steal", "Block"]
        physical = ["Speed", "Agility", "Strength", "Vertical"]

        def avg(attrs):
            vals = [attributes[a] for a in attrs if a in attributes]
            return sum(vals) / len(vals) if vals else 50

        ovr = (
            avg(finishing) * 0.15
            + avg(shooting) * 0.25
            + avg(playmaking) * 0.15
            + avg(defense) * 0.20
            + avg(physical) * 0.10
            + attributes.get("Intangibles", 50) * 0.10
            + attributes.get("Hustle", 50) * 0.05
        )

        return max(60, min(99, int(round(ovr))))


if __name__ == "__main__":
    print("Testing model classes...")
    print("AttributePredictor ready for use")
