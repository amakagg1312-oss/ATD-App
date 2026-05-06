"""Debug feature values for Wembanyama vs Jokic."""
import sys
sys.path.insert(0, r'D:\project\nba2k26_generator')

from ml_predictor_pure import compute_features, _get_feature_names, _get_nested, sf
from gen_player_fast import load_all_rows, normalize_name, repair_text, preferred_row, season_year

db_dir = r'D:\project\NBA Site data'
rows = load_all_rows(db_dir)

name_index = {}
for r in rows:
    name = normalize_name(repair_text(r.get("player_name", "")))
    if name:
        name_index.setdefault(name, []).append(r)

def get_player_row(name, season="2024-25"):
    target = normalize_name(name)
    matches = [r for r in name_index.get(target, []) if str(r.get("season_label", "")).strip().lower() == season.lower()]
    if not matches:
        matches = [r for r in name_index.get(target, []) if season_year(r.get("season_label", "")) == 2024]
    return preferred_row(matches)

for pname in ["Victor Wembanyama", "Nikola Jokic"]:
    row = get_player_row(pname)
    if row is None:
        print(f"{pname}: No data")
        continue
    
    print(f"\n{pname} ({row.get('position', '')}):")
    
    # Check what _get_nested returns for key stats
    for keys in [
        ("PTS", "pts", "per_game_pts_per_game"),
        ("REB", "reb", "per_game_reb_per_game"),
        ("AST", "ast", "per_game_ast_per_game"),
        ("BLK", "blk", "per_game_blk_per_game"),
        ("FG_PCT", "fg_pct", "per_game_fg_percent"),
        ("USG_PCT", "usg_pct", "advanced_usg_percent"),
        ("DRIVES",),
        ("TOUCHES",),
        ("AVG_SPEED",),
        ("PLAYER_HEIGHT_INCHES", "player_info_ht_in_in"),
        ("PLAYER_WEIGHT", "player_info_wt"),
        ("AGE",),
    ]:
        val = _get_nested(row, *keys)
        print(f"  {keys}: {val}")
    
    # Compute features and show key ones
    features = compute_features(row, rows)
    feat_names = _get_feature_names()
    
    # Show bio features and a few key ones
    key_feats = ["f_pg_pts", "f_pg_reb", "f_pg_ast", "f_pg_blk", "f_usg", "f_height", "f_weight", "f_age"]
    for kf in key_feats:
        if kf in feat_names:
            idx = feat_names.index(kf)
            print(f"  Feature {kf}: {features[idx]}")
