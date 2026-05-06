"""Compare ML predictions vs formula-based for a few players."""
import sys
sys.path.insert(0, r'D:\project\nba2k26_generator')

from ml_predictor_pure import predict_attributes, compute_features
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

players = ["Victor Wembanyama", "LeBron James", "Stephen Curry", "Nikola Jokic", "Giannis Antetokounmpo"]

for pname in players:
    row = get_player_row(pname)
    if row is None:
        print(f"{pname}: No data found")
        continue
    
    attrs = predict_attributes(row, rows)
    print(f"\n{pname} ({row.get('position', '')}):")
    for attr in ["Close Shot", "Driving Layup", "Three-Point Shot", "Ball Handle", "Pass Vision",
                 "Interior Defense", "Perimeter Defense", "Steal", "Block", "Speed", "Strength", "Vertical"]:
        print(f"  {attr}: {attrs.get(attr, 0)}")
