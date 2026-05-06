"""Check shot_dash data coverage in 2024-25."""
import sys
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import load_rows, as_float

rows = load_rows('NBA Site data')
missing = 0; total = 0
for r in rows:
    if '2024-25' not in r.get('season_label', ''): continue
    total += 1
    if as_float(r, 'shot_dash_zero_drib_freq') == 0.0 and as_float(r, 'shot_dash_off_dribble_freq') == 0.0:
        missing += 1

print(f'Players with ALL shot_dash=0 in 2024-25: {missing}/{total}')

count = 0
for r in rows:
    if '2024-25' not in r.get('season_label', ''): continue
    if as_float(r, 'shot_dash_zero_drib_freq') > 0:
        nm = r.get('player_name', '')
        zdf = r.get('shot_dash_zero_drib_freq')
        print(f'  Has data: {nm} zero_drib={zdf}')
        count += 1
        if count >= 3: break
if count == 0:
    print('  NO players have non-zero shot_dash data in 2024-25!')
