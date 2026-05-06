import sys
sys.path.insert(0, r'D:\project\nba2k26_generator')
from gen_player_fast import load_all_rows

rows = load_all_rows(r'D:\project\NBA Site data')
# Find LeBron
for r in rows:
    if 'lebron' in str(r.get('player_name', '')).lower():
        print(f'Found: {r.get("player_name")} season={r.get("season_label")}')
        print(f'Keys ({len(r.keys())}):')
        for k in sorted(r.keys()):
            v = r[k]
            if v and str(v).strip() and str(v).strip() not in ('0', '0.0', ''):
                print(f'  {k}: {v}')
        break
