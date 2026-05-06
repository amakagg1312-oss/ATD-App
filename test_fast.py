import sys, os, json
sys.path.insert(0, r'D:\project\nba2k26_generator')

# Set up argv before importing
sys.argv = ['gen_player_fast.py', 'LeBron James', '2024-25', r'D:\project', r'D:\project\NBA Site data', r'D:\project\Player Roles']

from gen_player_fast import (
    load_all_rows, normalize_name, repair_text, preferred_row, season_year
)

rows = load_all_rows(r'D:\project\NBA Site data')
print(f'Loaded {len(rows)} rows')

# Build name index
name_index = {}
for r in rows:
    name = normalize_name(repair_text(r.get("player_name", "")))
    if name:
        name_index.setdefault(name, []).append(r)

target_name = normalize_name("LeBron James")
target_season = "2024-25".strip().lower()

print(f'Target name: {target_name}')
print(f'Target season: {target_season}')

season_matches = []
for r in name_index.get(target_name, []):
    sl = str(r.get("season_label", "")).strip().lower()
    if sl == target_season:
        season_matches.append(r)

print(f'Season matches: {len(season_matches)}')

if not season_matches:
    # Show what seasons are available
    all_matches = name_index.get(target_name, [])
    print(f'All matches for LeBron: {len(all_matches)}')
    for r in all_matches[:5]:
        print(f'  season_label={repr(r.get("season_label", ""))} name={r.get("player_name", "")}')
