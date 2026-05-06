"""Find which 3 features are extra compared to model's expected 123."""
import json

# Features from engineering
feat_names = [
    "f_pg_pts", "f_pg_reb", "f_pg_ast", "f_pg_stl", "f_pg_blk", "f_pg_tov",
    "f_pg_oreb", "f_pg_dreb", "f_pg_fgm", "f_pg_fga", "f_pg_fg3m", "f_pg_fg3a",
    "f_pg_ftm", "f_pg_fta", "f_pg_pf", "f_pg_pfd",
    "f_36_pts", "f_36_reb", "f_36_ast", "f_36_blk", "f_36_stl",
    "f_fg_pct", "f_fg3_pct", "f_ft_pct", "f_ts_pct",
    "f_fg3a_rate", "f_ft_rate", "f_ast_tov_ratio",
    "f_usg", "f_ast_pct", "f_oreb_pct", "f_dreb_pct", "f_tov_pct",
    "f_drives_pg", "f_drive_fg_pct", "f_drive_ast_pct",
    "f_touches_pg", "f_paint_touch_pg", "f_elbow_touch_pg", "f_pts_per_touch", "f_sec_per_touch",
    "f_passes_pg", "f_pot_ast_pg", "f_ast_pass_pct", "f_sec_ast_pg",
    "f_cs_fg3a_pg", "f_cs_fg_pct",
    "f_pu_fg3a_pg", "f_pu_fg_pct",
    "f_avg_speed", "f_avg_speed_off", "f_dist_pg",
    "f_spot_up_poss_pct", "f_spot_up_ppp",
    "f_ball_handler_poss_pct", "f_ball_handler_ppp",
    "f_isolation_poss_pct", "f_isolation_ppp",
    "f_transition_poss_pct", "f_transition_ppp",
    "f_off_screen_poss_pct", "f_off_screen_ppp",
    "f_cut_poss_pct", "f_cut_ppp",
    "f_roll_man_poss_pct", "f_roll_man_ppp",
    "f_deflections_pg", "f_contested_pg", "f_contested3_pg", "f_boxouts_pg",
    "f_height", "f_weight", "f_age",
    "pct_f_pg_pts", "pct_f_pg_reb", "pct_f_pg_ast", "pct_f_pg_stl", "pct_f_pg_blk",
    "pct_f_pg_tov", "pct_f_pg_oreb", "pct_f_pg_dreb", "pct_f_pg_fgm", "pct_f_pg_fga",
    "pct_f_pg_fg3m", "pct_f_pg_fg3a", "pct_f_pg_ftm", "pct_f_pg_fta",
    "pct_f_36_pts", "pct_f_36_reb", "pct_f_36_ast", "pct_f_36_blk", "pct_f_36_stl",
    "pct_f_fg_pct", "pct_f_fg3_pct", "pct_f_ft_pct", "pct_f_ts_pct",
    "pct_f_fg3a_rate", "pct_f_ft_rate", "pct_f_ast_tov_ratio",
    "pct_f_usg", "pct_f_ast_pct", "pct_f_oreb_pct", "pct_f_dreb_pct", "pct_f_tov_pct",
    "pct_f_drives_pg", "pct_f_drive_fg_pct", "pct_f_drive_ast_pct",
    "pct_f_touches_pg", "pct_f_paint_touch_pg", "pct_f_pts_per_touch",
    "pct_f_passes_pg", "pct_f_pot_ast_pg", "pct_f_ast_pass_pct", "pct_f_sec_ast_pg",
    "pct_f_cs_fg3a_pg", "pct_f_cs_fg_pct",
    "pct_f_pu_fg3a_pg", "pct_f_pu_fg_pct",
    "pct_f_avg_speed", "pct_f_avg_speed_off",
    "pct_f_deflections_pg", "pct_f_contested_pg", "pct_f_contested3_pg",
    "pct_f_boxouts_pg", "pct_f_height", "pct_f_weight",
]

print(f"Total: {len(feat_names)}")

# The model expects 123 features. Let me check which ones might be missing.
# Looking at the feature engineering code, f_efg_pct is dropped.
# Also, f_elbow_touch_pg might not be in the percentile list.
# And f_dist_pg might not be in the percentile list.

# Let me check the pct_cols list from feature_engineering.py
pct_cols_from_code = [
    "f_pg_pts", "f_pg_reb", "f_pg_ast", "f_pg_stl", "f_pg_blk",
    "f_pg_tov", "f_pg_oreb", "f_pg_dreb", "f_pg_fgm", "f_pg_fga",
    "f_pg_fg3m", "f_pg_fg3a", "f_pg_ftm", "f_pg_fta",
    "f_36_pts", "f_36_reb", "f_36_ast", "f_36_blk", "f_36_stl",
    "f_fg_pct", "f_fg3_pct", "f_ft_pct", "f_ts_pct",
    "f_fg3a_rate", "f_ft_rate", "f_ast_tov_ratio",
    "f_usg", "f_ast_pct", "f_oreb_pct", "f_dreb_pct", "f_tov_pct",
    "f_drives_pg", "f_drive_fg_pct", "f_drive_ast_pct",
    "f_touches_pg", "f_paint_touch_pg", "f_pts_per_touch",
    "f_passes_pg", "f_pot_ast_pg", "f_ast_pass_pct", "f_sec_ast_pg",
    "f_cs_fg3a_pg", "f_cs_fg_pct",
    "f_pu_fg3a_pg", "f_pu_fg_pct",
    "f_avg_speed", "f_avg_speed_off",
    "f_deflections_pg", "f_contested_pg", "f_contested3_pg",
    "f_boxouts_pg", "f_height", "f_weight",
]

# These are the base features that should have percentiles
# Count: 53 percentile features

# But my feat_names has f_elbow_touch_pg and f_dist_pg as base features
# without corresponding percentiles. Let me check if they're in pct_cols.

elbow_in_pct = "f_elbow_touch_pg" in pct_cols_from_code
dist_in_pct = "f_dist_pg" in pct_cols_from_code

print(f"f_elbow_touch_pg in pct_cols: {elbow_in_pct}")
print(f"f_dist_pg in pct_cols: {dist_in_pct}")

# f_elbow_touch_pg is NOT in pct_cols_from_code, so no percentile for it
# f_dist_pg is NOT in pct_cols_from_code, so no percentile for it

# So the base features are:
# 16 + 5 + 4 + 3 + 5 + 3 + 5 + 4 + 2 + 2 + 3 + 14 + 4 + 3 = 73
# Percentile features: 53
# Total: 126

# But model expects 123. So 3 features are extra.
# The extras might be: f_elbow_touch_pg, f_dist_pg, and one more.

# Actually, looking at the pct_cols_from_code, it has 53 items.
# But the code says "Only compute percentiles for columns that exist"
# So if f_elbow_touch_pg or f_dist_pg don't exist in training data,
# they won't have percentiles.

# Let me check: the model has 123 features.
# If I remove f_elbow_touch_pg, f_dist_pg, and one more, I get 123.
# The third might be f_sec_per_touch or something else.

# Actually, let me just check which features are NOT in the percentile list
# but are in my base features.

base_features = [f for f in feat_names if not f.startswith("pct_")]
pct_features = [f for f in feat_names if f.startswith("pct_")]

base_without_pct = []
for bf in base_features:
    # Check if there's a corresponding pct_ feature
    pct_name = "pct_" + bf
    if pct_name not in pct_features:
        base_without_pct.append(bf)

print(f"Base features without percentiles: {base_without_pct}")
print(f"Count: {len(base_without_pct)}")

# These are the features that don't have percentiles
# f_elbow_touch_pg, f_dist_pg, f_age are the ones without percentiles
# That's 3 features. So 126 - 3 = 123. 

# Wait, but those 3 ARE in my feat_names. They're just base features without percentiles.
# So the total is still 126.

# The model expects 123. So 3 features from my list are NOT in the model.
# Let me check if f_elbow_touch_pg, f_dist_pg, and f_age are the extras.

# Actually, let me re-count. The model scaler has 123 values.
# My feature list has 126.
# The difference is 3.

# Looking at the feature engineering code, the drop_cols includes f_efg_pct.
# But f_efg_pct is not in my output (it was dropped correctly).

# The issue might be that during training, some features weren't available
# in all seasons, so the final feature count was 123.

# Let me just remove the 3 features that are least likely to be in the model:
# f_elbow_touch_pg (elbow touches might not be in all seasons)
# f_dist_pg (distance might not be in all seasons)
# f_age (might not be in all seasons)

# Actually, let me check the scaler values to see which features are missing.
# The scaler center values should give me a clue.

d = json.load(open(r"D:\project\nba2k26_generator\models_export.json"))
scaler_center = d["guard"]["Driving Layup"]["scaler"]["center"]
print(f"\nScaler center has {len(scaler_center)} values")
print(f"First 20: {scaler_center[:20]}")

# The first few values should correspond to f_pg_pts, f_pg_reb, etc.
# f_pg_pts median should be around 10-15
# f_pg_reb median should be around 3-5
# etc.

# Let me map the scaler values to feature names
# and see which ones don't match.
