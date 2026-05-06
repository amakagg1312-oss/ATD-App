"""Debug single player attribute computation."""
import sys, os
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import load_rows, compute_attributes, compute_tendencies, as_float

rows = load_rows('NBA Site data')
BADGES_TXT = 'Badges/NBA 2K26 Badges.txt'

targets = ['Tatum', 'Doncic', 'Dončić', 'Gobert', 'Giannis', 'Anunoby', 'Morant', 'Wembanyama', 'Kessler']

for r in rows:
    nm = r.get('player_name', '')
    season = r.get('season_label', '')
    if '2025-26' not in season:
        continue
    for t in targets:
        if t.lower() in nm.lower() and 'Seth' not in nm and 'Garza' not in nm:
            three_pct = as_float(r, 'per_36_x3p_percent')
            ds = as_float(r, 'shooting_percent_dunks_of_fga')
            dunks = as_float(r, 'shooting_num_of_dunks')
            tend = compute_tendencies(r)
            result = compute_attributes(r, tend, 'Player Roles', all_rows=rows, badges_txt_path=BADGES_TXT)
            attrs = result['attributes']
            pos = r.get('position','?')
            print(f'{nm} ({pos}) [{season}]: raw-3pt%={three_pct:.3f} raw-ds={ds:.3f} dunks={dunks:.0f}')
            print(f'  3PT={attrs["Three-Point Shot"]} DrDnk={attrs["Driving Dunk"]} StDnk={attrs["Standing Dunk"]} Layup={attrs["Driving Layup"]}')
