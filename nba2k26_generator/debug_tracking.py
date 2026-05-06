"""Debug tracking feature values."""
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

row = get_player_row("Victor Wembanyama")
if row:
    print("Tracking keys in row:")
    for k in sorted(row.keys()):
        if 'tracking' in k.lower() or 'drive' in k.lower() or 'touch' in k.lower() or 'pass' in k.lower():
            v = row[k]
            if v and str(v).strip() and str(v).strip().lower() not in ("", "nan", "none"):
                print(f"  {k}: {v}")
