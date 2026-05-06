"""Training pipeline for NBA 2K26 attribute prediction models.

Trains per-attribute HistGradientBoostingRegressor models for each
position group, which properly captures elite player values instead
of regressing to the mean.
"""

import numpy as np
import pandas as pd
import time
from pathlib import Path
from typing import Dict, Tuple, Optional
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

from .data_loader import load_training_data
from .feature_engineering import (
    engineer_features,
    prepare_training_data,
    detect_position_group,
)
from .models import PositionSpecificModels, PositionAttributeModels, AttributeModel
from .config import MODELS_DIR, NBA_DATA_DIR, TEST_SIZE, ATTRIBUTE_NAMES, ML_ATTRIBUTES, SEASONS, MIN_GAMES_PLAYED, MIN_MINUTES_PLAYED
from .season_baselines import compute_and_save_baselines


def train_models(
    data: pd.DataFrame = None,
    test_size: float = TEST_SIZE,
    save_models: bool = True,
    verbose: bool = True,
) -> Tuple[PositionSpecificModels, Dict]:
    """Train position-specific per-attribute models."""
    start_time = time.time()

    if data is None:
        if verbose:
            print("Loading training data...")
        data, _ = load_training_data()

    if verbose:
        print("Engineering features...")
    engineered = engineer_features(data)

    if verbose:
        print("Preparing training matrices...")
    X, y_all, positions, feature_cols, attr_cols_all = prepare_training_data(engineered)

    # Only use ML_ATTRIBUTES for training (exclude heuristic-only attributes)
    ml_attr_indices = [
        i for i, attr in enumerate(attr_cols_all) if attr in ML_ATTRIBUTES
    ]
    y = y_all.iloc[:, ml_attr_indices].copy()

    if verbose:
        print(f"\nTraining data shape: X={X.shape}, y={y.shape}")
        print(f"Feature columns: {len(feature_cols)}")
        print(f"Attribute columns (ML): {len(ML_ATTRIBUTES)}")
        print(f"\nPosition distribution:")
        print(positions.value_counts())

    X_train, X_test, y_train, y_test, pos_train, pos_test = train_test_split(
        X, y, positions, test_size=test_size, random_state=42
    )

    if verbose:
        print(f"\nTrain/Test split: {len(X_train)}/{len(X_test)} samples")
        print("\nPosition distribution in training set:")
        print(pos_train.value_counts())

    if verbose:
        print("\n" + "=" * 60)
        print("Training Per-Attribute Models")
        print("=" * 60)

    model = PositionSpecificModels()
    model.fit(X_train, y_train, pos_train, verbose=verbose)

    if verbose:
        print("\n" + "=" * 60)
        print("Evaluating Models")
        print("=" * 60)

    eval_results = evaluate_models(model, X_test, y_test, pos_test, verbose=verbose)

    # Overall metrics
    overall_preds = np.zeros_like(y_test.values)
    for pos_group in model.position_models:
        mask = pos_test == pos_group
        if mask.sum() > 0:
            overall_preds[mask] = model.position_models[pos_group].predict(
                X_test[mask].values
            )

    overall_mae = mean_absolute_error(y_test.values, overall_preds)
    overall_r2 = r2_score(y_test.values, overall_preds, multioutput="uniform_average")

    if verbose:
        print(f"\nOverall Test MAE: {overall_mae:.2f}")
        print(f"Overall Test R²:  {overall_r2:.3f}")
        print(f"Training time: {time.time() - start_time:.1f}s")

        # Per-attribute MAE
        print("\nPer-attribute MAE:")
        for i, attr in enumerate(ML_ATTRIBUTES):
            if i < overall_preds.shape[1]:
                attr_mae = mean_absolute_error(y_test.values[:, i], overall_preds[:, i])
                print(f"  {attr}: {attr_mae:.2f}")

    if save_models:
        if verbose:
            print(f"\nSaving models to {MODELS_DIR}...")
        model.save_all(MODELS_DIR)
        # Save feature columns for inference
        feat_file = MODELS_DIR / "feature_columns.txt"
        with open(feat_file, "w") as f:
            for col in feature_cols:
                f.write(col + "\n")
        if verbose:
            print("Models saved successfully!")

        # Compute and save season-level percentile baselines.
        # These fix the train/inference mismatch where pct_* features computed
        # on a single-row DataFrame at inference are always meaningless (100%).
        if verbose:
            print("\nComputing season percentile baselines...")
        baselines_path = MODELS_DIR / "season_baselines.json"
        compute_and_save_baselines(
            seasons=SEASONS,
            data_dir=NBA_DATA_DIR,
            output_path=baselines_path,
            min_games=MIN_GAMES_PLAYED,
            min_minutes=MIN_MINUTES_PLAYED,
            verbose=verbose,
        )

    results = {
        "eval_results": eval_results,
        "overall_mae": overall_mae,
        "overall_r2": overall_r2,
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "feature_count": len(feature_cols),
        "training_time": time.time() - start_time,
    }

    return model, results


def evaluate_models(
    model: PositionSpecificModels,
    X: pd.DataFrame,
    y: pd.DataFrame,
    positions: pd.Series,
    verbose: bool = True,
) -> Dict:
    """Evaluate trained models on test set."""
    results = {}
    X_arr = X.values if hasattr(X, "values") else X
    y_arr = y.values if hasattr(y, "values") else y

    for pos_group in model.position_models.keys():
        mask = positions == pos_group
        X_pos = X_arr[mask]
        y_pos = y_arr[mask]

        if len(X_pos) < 10:
            continue

        predictions = model.position_models[pos_group].predict(X_pos)

        mae = mean_absolute_error(y_pos, predictions)
        r2 = r2_score(y_pos, predictions, multioutput="uniform_average")

        attr_maes = {}
        for i, attr in enumerate(ML_ATTRIBUTES):
            if i < predictions.shape[1]:
                attr_mae = mean_absolute_error(y_pos[:, i], predictions[:, i])
                attr_maes[attr] = attr_mae

        results[pos_group] = {
            "mae": mae,
            "r2": r2,
            "sample_count": len(X_pos),
            "attribute_maes": attr_maes,
        }

        if verbose:
            print(f"\n{pos_group.upper()} ({len(X_pos)} samples):")
            print(f"  MAE: {mae:.2f}")
            print(f"  R²:  {r2:.3f}")

    return results


def train_and_save_models(verbose: bool = True):
    """Main entry point for training."""
    print("=" * 60)
    print("NBA 2K26 Attribute Prediction - Training Pipeline")
    print("=" * 60)

    model, results = train_models(save_models=True, verbose=verbose)

    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    print(f"Models saved to: {MODELS_DIR}")
    print(f"Overall Test MAE: {results['overall_mae']:.2f}")
    print(f"Overall Test R²:  {results['overall_r2']:.3f}")

    return model, results


if __name__ == "__main__":
    train_and_save_models()
