"""Extract exact feature column names by running feature engineering on test data."""
import json
import os
import sys

# We need pandas just once to extract feature names
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "nba2k26_generator"))

# Create a minimal test dataframe with the expected column structure
test_data = {
    "PLAYER_NAME": ["Test Player"],
    "TEAM_ABBREVIATION": ["LAL"],
    "POSITION": ["SG"],
    "GP": [70],
    "MIN": [34.0],
    "PTS": [20.0],
    "REB": [5.0],
    "AST": [4.0],
    "STL": [1.0],
    "BLK": [0.5],
    "TOV": [2.5],
    "OREB": [1.0],
    "DREB": [4.0],
    "FGM": [7.0],
    "FGA": [15.0],
    "FG3M": [2.5],
    "FG3A": [6.0],
    "FTM": [3.5],
    "FTA": [4.5],
    "PF": [2.0],
    "PFD": [3.0],
    "FG_PCT": [0.467],
    "FG3_PCT": [0.417],
    "FT_PCT": [0.778],
    "TS_PCT": [0.550],
    "EFG_PCT": [0.550],
    "USG_PCT": [25.0],
    "AST_PCT": [20.0],
    "REB_PCT": [10.0],
    "OREB_PCT": [5.0],
    "DREB_PCT": [15.0],
    "TOV_PCT": [12.0],
    "OFF_RATING": [110.0],
    "DEF_RATING": [105.0],
    "NET_RATING": [5.0],
    "PIE": [0.15],
    "PCT_STL": [2.0],
    "PCT_BLK": [1.0],
    "DRIVES": [350],
    "DRIVE_FG_PCT": [0.55],
    "DRIVE_AST_PCT": [0.15],
    "TOUCHES": [3500],
    "PAINT_TOUCHES": [200],
    "POST_TOUCHES": [100],
    "ELBOW_TOUCHES": [50],
    "PTS_PER_TOUCH": [0.4],
    "AVG_SEC_PER_TOUCH": [3.5],
    "PASSES_MADE": [2500],
    "POTENTIAL_AST": [500],
    "AST_TO_PASS_PCT": [0.15],
    "SECONDARY_AST": [30],
    "CATCH_SHOOT_FG3A": [150],
    "CATCH_SHOOT_FG_PCT": [0.40],
    "PULL_UP_FG3A": [100],
    "PULL_UP_FG3_PCT": [0.35],
    "AVG_SPEED": [4.0],
    "AVG_SPEED_OFF": [4.2],
    "DIST_MILE": [2.5],
    "SPOT_UP_POSS_PCT": [0.15],
    "SPOT_UP_PPP": [1.0],
    "BALL_HANDLER_POSS_PCT": [0.10],
    "BALL_HANDLER_PPP": [0.9],
    "ISOLATION_POSS_PCT": [0.12],
    "ISOLATION_PPP": [0.85],
    "TRANSITION_POSS_PCT": [0.10],
    "TRANSITION_PPP": [1.1],
    "OFF_SCREEN_POSS_PCT": [0.08],
    "OFF_SCREEN_PPP": [0.95],
    "CUT_POSS_PCT": [0.05],
    "CUT_PPP": [1.2],
    "ROLL_MAN_POSS_PCT": [0.03],
    "ROLL_MAN_PPP": [1.1],
    "DEFLECTIONS": [80],
    "CONTESTED_SHOTS": [150],
    "CONTESTED_SHOTS_3PT": [60],
    "BOX_OUTS": [50],
    "SCREEN_ASSISTS": [20],
    "PLAYER_HEIGHT_INCHES": [78],
    "PLAYER_WEIGHT": [200],
    "AGE": [27],
    "DD2": [10],
    "TD3": [5],
    "PLUS_MINUS": [4.0],
}

df = pd.DataFrame(test_data)

from ml.feature_engineering import engineer_features, get_feature_columns

engineered = engineer_features(df)
feat_cols = get_feature_columns(engineered)

print(f"Feature count: {len(feat_cols)}")
print(f"Features: {json.dumps(feat_cols, indent=2)}")

# Save
with open(os.path.join(os.path.dirname(__file__), "nba2k26_generator", "ml_feature_names.json"), "w") as f:
    json.dump(feat_cols, f)
