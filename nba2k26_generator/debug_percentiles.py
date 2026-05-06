"""Debug percentile values for Wembanyama vs Jokic."""
import sys
sys.path.insert(0, r'D:\project\nba2k26_generator')

from ml_predictor_pure import compute_features, _get_feature_names, _get_feature_stats, _compute_percentile
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

stats = _get_feature_stats() or {}

for pname in ["Victor Wembanyama", "Nikola Jokic"]:
    row = get_player_row(pname)
    if row is None:
        print(f"{pname}: No data")
        continue
    
    print(f"\n{pname}:")
    
    features = compute_features(row, rows)
    feat_names = _get_feature_names()
    
    # Show all features
    for i, (fname, fval) in enumerate(zip(feat_names, features)):
        if i < 70 or fval != 0:  # Show first 70 (raw) and non-zero percentiles
            print(f"  [{i:3d}] {fname}: {fval:.2f}")
