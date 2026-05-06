"""Check what keys are available after merge fix."""
import sys
sys.path.insert(0, r'D:\project\nba2k26_generator')

from gen_player_fast import load_all_rows, normalize_name, repair_text, preferred_row, season_year

db_dir = r'D:\project\NBA Site data'
rows = load_all_rows(db_dir)

name_index = {}
for r in rows:
    name = normalize_name(repair_text(r.get("player_name", "")))
    if name:
        name_index.setdefault(name, []).append(r)

target = normalize_name("Victor Wembanyama")
matches = [r for r in name_index.get(target, []) if str(r.get("season_label", "")).strip().lower() == "2024-25"]
row = preferred_row(matches)

if row:
    print("Keys with pts/PTS in them:")
    for k in sorted(row.keys()):
        if 'pts' in k.lower() or 'pts' in k:
            v = row[k]
            if v and str(v).strip() and str(v).strip().lower() not in ("", "nan", "none"):
                print(f"  {k}: {v}")
    print("\nPTS value:", row.get("pts", "N/A"))
    print("PTS (uppercase):", row.get("PTS", "N/A"))
    print("per_game_pts_per_game:", row.get("per_game_pts_per_game", "N/A"))
    print("points:", row.get("points", "N/A"))
else:
    print("No row found")
