import json

d = json.load(open(r'D:\project\nba2k26_generator\models_export.json'))
guard_data = d['guard']['Driving Layup']
scaler = guard_data['scaler']
print(f'Features per model: {len(scaler["center"])}')

feat_names = [
    # Per-game stats (16)
    'f_pg_pts', 'f_pg_reb', 'f_pg_ast', 'f_pg_stl', 'f_pg_blk', 'f_pg_tov',
    'f_pg_oreb', 'f_pg_dreb', 'f_pg_fgm', 'f_pg_fga', 'f_pg_fg3m', 'f_pg_fg3a',
    'f_pg_ftm', 'f_pg_fta', 'f_pg_pf', 'f_pg_pfd',
    # Per-36 stats (5)
    'f_36_pts', 'f_36_reb', 'f_36_ast', 'f_36_blk', 'f_36_stl',
    # Shooting percentages (5)
    'f_fg_pct', 'f_fg3_pct', 'f_ft_pct', 'f_ts_pct', 'f_efg_pct',
    # Derived ratios (3)
    'f_fg3a_rate', 'f_ft_rate', 'f_ast_tov_ratio',
    # Advanced stats (5)
    'f_usg', 'f_ast_pct', 'f_oreb_pct', 'f_dreb_pct', 'f_tov_pct',
    # Tracking: Drives (3)
    'f_drives_pg', 'f_drive_fg_pct', 'f_drive_ast_pct',
    # Tracking: Touches (5)
    'f_touches_pg', 'f_paint_touch_pg', 'f_pts_per_touch', 'f_sec_per_touch', 'f_elbow_touch_pg',
    # Tracking: Passing (4)
    'f_passes_pg', 'f_pot_ast_pg', 'f_ast_pass_pct', 'f_sec_ast_pg',
    # Tracking: Catch & Shoot (2)
    'f_cs_fg3a_pg', 'f_cs_fg_pct',
    # Tracking: Pull-Up (2)
    'f_pu_fg3a_pg', 'f_pu_fg_pct',
    # Tracking: Speed (3)
    'f_avg_speed', 'f_avg_speed_off', 'f_dist_pg',
    # Playtypes (14)
    'f_spot_up_poss_pct', 'f_spot_up_ppp',
    'f_ball_handler_poss_pct', 'f_ball_handler_ppp',
    'f_isolation_poss_pct', 'f_isolation_ppp',
    'f_transition_poss_pct', 'f_transition_ppp',
    'f_off_screen_poss_pct', 'f_off_screen_ppp',
    'f_cut_poss_pct', 'f_cut_ppp',
    'f_roll_man_poss_pct', 'f_roll_man_ppp',
    # Hustle (4)
    'f_deflections_pg', 'f_contested_pg', 'f_contested3_pg', 'f_boxouts_pg',
    # Bio (3)
    'f_height', 'f_weight', 'f_age',
    # Percentile rankings (46)
    'pct_f_pg_pts', 'pct_f_pg_reb', 'pct_f_pg_ast', 'pct_f_pg_stl', 'pct_f_pg_blk',
    'pct_f_pg_tov', 'pct_f_pg_oreb', 'pct_f_pg_dreb', 'pct_f_pg_fgm', 'pct_f_pg_fga',
    'pct_f_pg_fg3m', 'pct_f_pg_fg3a', 'pct_f_pg_ftm', 'pct_f_pg_fta',
    'pct_f_36_pts', 'pct_f_36_reb', 'pct_f_36_ast', 'pct_f_36_blk', 'pct_f_36_stl',
    'pct_f_fg_pct', 'pct_f_fg3_pct', 'pct_f_ft_pct', 'pct_f_ts_pct',
    'pct_f_fg3a_rate', 'pct_f_ft_rate', 'pct_f_ast_tov_ratio',
    'pct_f_usg', 'pct_f_ast_pct', 'pct_f_oreb_pct', 'pct_f_dreb_pct', 'pct_f_tov_pct',
    'pct_f_drives_pg', 'pct_f_drive_fg_pct', 'pct_f_drive_ast_pct',
    'pct_f_touches_pg', 'pct_f_paint_touch_pg', 'pct_f_pts_per_touch',
    'pct_f_passes_pg', 'pct_f_pot_ast_pg', 'pct_f_ast_pass_pct', 'pct_f_sec_ast_pg',
    'pct_f_cs_fg3a_pg', 'pct_f_cs_fg_pct',
    'pct_f_pu_fg3a_pg', 'pct_f_pu_fg_pct',
    'pct_f_avg_speed', 'pct_f_avg_speed_off',
    'pct_f_deflections_pg', 'pct_f_contested_pg', 'pct_f_contested3_pg',
    'pct_f_boxouts_pg', 'pct_f_height', 'pct_f_weight',
]

print(f'Total features: {len(feat_names)}')
print(f'Expected: {len(scaler["center"])}')

# Save to JSON
with open(r'D:\project\nba2k26_generator\ml_feature_names.json', 'w') as f:
    json.dump(feat_names, f)
