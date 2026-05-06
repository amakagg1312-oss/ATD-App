"""ML Configuration for NBA 2K26 Attribute Generation."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
NBA_DATA_DIR = BASE_DIR / "NBA Site data"
PLAYER_ROLES_DIR = BASE_DIR / "Player Roles"
MODELS_DIR = Path(__file__).parent / "models"

MIN_GAMES_PLAYED = 15
MIN_MINUTES_PLAYED = 150

SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]

POSITION_GROUPS = {
    "guard": ["PG", "SG"],
    "wing": ["SF", "SG-SF", "SF-SG"],
    "big": ["PF", "C", "PF-C", "C-PF"],
}

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

# Intangibles is always 25 - not predicted by ML
CONSTANT_ATTRIBUTES = {
    "Intangibles": 25,
}

# These are NOT predicted - just set to constant
HEURISTIC_ATTRIBUTES = list(CONSTANT_ATTRIBUTES.keys())

# All attributes predicted by ML (everything except Intangibles)
ML_ATTRIBUTES = [a for a in ATTRIBUTE_NAMES if a not in HEURISTIC_ATTRIBUTES]

FEATURE_CSV_FILES = {
    "traditional": "player_traditional_{season}_regular_season.csv",
    "advanced": "player_advanced_{season}_regular_season.csv",
    "shooting": "player_shooting_{season}_regular_season.csv",
    "defense": "player_defense_{season}_regular_season.csv",
    "bio": "player_bio_{season}_regular_season.csv",
    "hustle": "player_hustle_{season}_regular_season.csv",
    "tracking_drives": "player_tracking_drives_{season}_regular_season.csv",
    "tracking_passing": "player_tracking_passing_{season}_regular_season.csv",
    "tracking_touches": "player_tracking_touches_{season}_regular_season.csv",
    "tracking_speed": "player_tracking_speed_distance_{season}_regular_season.csv",
    "defense_dash_overall": "player_defense_dash_overall_{season}_regular_season.csv",
    "defense_dash_lt6": "player_defense_dash_lt6_{season}_regular_season.csv",
    "playtype_spot_up": "player_playtype_spot_up_{season}_regular_season.csv",
    "playtype_ball_handler": "player_playtype_ball_handler_{season}_regular_season.csv",
    "playtype_post_up": "player_playtype_playtype_post_up_{season}_regular_season.csv",
    "playtype_isolation": "player_playtype_isolation_{season}_regular_season.csv",
    "playtype_transition": "player_playtype_transition_{season}_regular_season.csv",
    "playtype_off_screen": "player_playtype_off_screen_{season}_regular_season.csv",
    "playtype_cut": "player_playtype_cut_{season}_regular_season.csv",
    "playtype_roll": "player_playtype_roll_man_{season}_regular_season.csv",
    "tracking_catch_shoot": "player_tracking_catch_shoot_{season}_regular_season.csv",
    "tracking_pullup": "player_tracking_pullup_{season}_regular_season.csv",
}

# RandomForest params - fast and effective for multi-output regression
MODEL_PARAMS = {
    "n_estimators": 300,
    "max_depth": 12,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "max_features": 0.5,
    "random_state": 42,
    "n_jobs": -1,
}

ENSEMBLE_SEEDS = [42, 123, 456]
ENSEMBLE_SIZE = len(ENSEMBLE_SEEDS)

CROSS_VAL_FOLDS = 5
TEST_SIZE = 0.2
