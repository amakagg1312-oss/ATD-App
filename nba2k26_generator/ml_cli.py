"""CLI for ML-based attribute generation."""

import argparse
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba2k26_generator.ml import (
    train_and_save_models,
    AttributeGenerator,
    load_training_data,
)
from nba2k26_generator.ml.feature_engineering import engineer_features


def cmd_train(args):
    """Train ML models."""
    print("=" * 60)
    print("Training NBA 2K26 Attribute Prediction Models")
    print("=" * 60)

    model, results = train_and_save_models(verbose=True)

    print("\n" + "=" * 60)
    print("Training Summary")
    print("=" * 60)
    print(f"Training samples: {results['training_samples']}")
    print(f"Test samples: {results['test_samples']}")
    print(f"Feature count: {results['feature_count']}")
    print(f"Overall MAE: {results['overall_mae']:.2f}")
    print(f"Training time: {results['training_time']:.1f}s")

    return 0


def cmd_predict(args):
    """Predict attributes for a player."""
    generator = AttributeGenerator()

    if not generator.load_models():
        print("Error: Models not found. Run 'train' command first.")
        return 1

    stats = {}
    if args.stats:
        for pair in args.stats:
            key, val = pair.split("=")
            stats[key.strip()] = float(val.strip())

    if not stats:
        print("Error: No stats provided. Use --stats KEY=VALUE")
        return 1

    position = args.position or "SG"

    attrs = generator.generate_attributes(
        player_stats=stats,
        position=position,
        height_inches=args.height or 78,
        weight_lbs=args.weight or 200,
        experience_years=args.experience or 3,
    )

    print("\n" + "=" * 60)
    print(f"Generated Attributes ({position})")
    print("=" * 60)
    print(f"Overall: {attrs.get('Overall', 'N/A')}")
    print()

    categories = {
        "Finishing": ["Driving Layup", "Standing Dunk", "Driving Dunk", "Close Shot"],
        "Shooting": ["Mid-Range Shot", "Three-Point Shot", "Free Throw", "Shot IQ"],
        "Playmaking": [
            "Ball Handle",
            "Speed with Ball",
            "Pass Accuracy",
            "Pass IQ",
            "Pass Vision",
        ],
        "Defense": [
            "Interior Defense",
            "Perimeter Defense",
            "Steal",
            "Block",
            "Help Defense IQ",
        ],
        "Rebounding": ["Offensive Rebound", "Defensive Rebound"],
        "Physical": ["Speed", "Agility", "Strength", "Vertical", "Stamina"],
    }

    for cat, attrs_list in categories.items():
        print(f"\n{cat}:")
        for attr in attrs_list:
            if attr in attrs:
                val = attrs[attr]
                bar = "#" * (val // 5) + "-" * ((99 - val) // 5)
                print(f"  {attr:20} {bar} {val}")

    print(f"\nOther:")
    for attr in ["Intangibles", "Hustle", "Overall Durability", "Potential"]:
        if attr in attrs:
            val = attrs[attr]
            bar = "#" * (val // 5) + "-" * ((99 - val) // 5)
            print(f"  {attr:20} {bar} {val}")

    return 0


def cmd_evaluate(args):
    """Evaluate model performance."""
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error

    print("Loading training data...")
    data, _ = load_training_data()

    print("Engineering features...")
    engineered = engineer_features(data)

    print("Preparing data...")
    X, y, positions, feature_cols, attr_cols = prepare_training_data(engineered)

    from nba2k26_generator.ml.models import PositionSpecificModels

    X_train, X_test, y_train, y_test, pos_train, pos_test = train_test_split(
        X, y, positions, test_size=0.2, random_state=42
    )

    print("Loading models...")
    model = PositionSpecificModels.load_all()

    print("\n" + "=" * 60)
    print("Model Evaluation Results")
    print("=" * 60)

    for pos_group in model.position_models.keys():
        mask = pos_test == pos_group
        X_pos = X_test[mask].values
        y_pos = y_test[mask].values

        if len(X_pos) < 10:
            continue

        predictions = model.position_models[pos_group].predict(X_pos)
        mae = mean_absolute_error(y_pos, predictions)

        print(f"\n{pos_group.upper()} ({len(X_pos)} test samples):")
        print(f"  MAE: {mae:.2f}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="NBA 2K26 ML Attribute Generator")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    train_parser = subparsers.add_parser("train", help="Train ML models")
    train_parser.set_defaults(func=cmd_train)

    predict_parser = subparsers.add_parser("predict", help="Predict player attributes")
    predict_parser.add_argument("--stats", nargs="+", help="Stats as KEY=VALUE pairs")
    predict_parser.add_argument(
        "--position", "-p", default="SG", help="Player position"
    )
    predict_parser.add_argument("--height", type=float, help="Height in inches")
    predict_parser.add_argument("--weight", type=float, help="Weight in lbs")
    predict_parser.add_argument(
        "--experience", type=int, default=3, help="Years of experience"
    )
    predict_parser.set_defaults(func=cmd_predict)

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate trained models")
    eval_parser.set_defaults(func=cmd_evaluate)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
