"""Debug attribute inputs for key players."""
import sys, os, math
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import load_rows, as_float

rows = load_rows('NBA Site data')
rows_season = [r for r in rows if '2025-26' in str(r.get('season_label', ''))]
print(f'2025-26 players: {len(rows_season)}')

def position_bucket(pos_text):
    p = (pos_text or '').upper()
    if 'C' in p and 'PF' not in p:
        return 'C'
    if 'PF' in p or 'SF' in p:
        return 'F'
    return 'G'

def pct(lst, val):
    vals = [v for v in lst if not math.isnan(v) and not math.isinf(v)]
    n = len(vals)
    if not n:
        return 0.0
    below = sum(v < val for v in vals)
    at = sum(v == val for v in vals)
    return (below + 0.5 * at) / n * 100.0

targets = ['Dončić', 'Garza', 'Gobert', 'Giannis', 'Curry', 'Tatum', 'Anunoby', 'Morant', 'Wembanyama', 'Kessler', 'Davis', 'Haliburton']

for r in rows_season:
    nm = r.get('player_name', '')
    for t in targets:
        if t.lower() in nm.lower():
            pos = r.get('position', '?')
            bucket = position_bucket(pos)
            bucket_players = [rx for rx in rows_season if position_bucket(str(rx.get('position', ''))) == bucket]

            ds = as_float(r, 'shooting_percent_dunks_of_fga')
            dunks = as_float(r, 'shooting_num_of_dunks')
            drives = as_float(r, 'tracking_drives_pg')
            rs = as_float(r, 'shooting_percent_fga_from_x0_3_range')
            three_pct = as_float(r, 'per_36_x3p_percent')
            fg3a36 = as_float(r, 'per_36_x3pa_per_36_min')
            three_share = as_float(r, 'shooting_percent_fga_from_x3p_range')

            p_ds = pct([as_float(rx, 'shooting_percent_dunks_of_fga') for rx in bucket_players], ds)
            p_dunks = pct([as_float(rx, 'shooting_num_of_dunks') for rx in bucket_players], dunks)
            p_rs = pct([as_float(rx, 'shooting_percent_fga_from_x0_3_range') for rx in bucket_players], rs)
            p_3pt = pct([as_float(rx, 'per_36_x3p_percent') for rx in bucket_players], three_pct)
            p_3pa36 = pct([as_float(rx, 'per_36_x3pa_per_36_min') for rx in bucket_players], fg3a36)
            p_3share = pct([as_float(rx, 'shooting_percent_fga_from_x3p_range') for rx in bucket_players], three_share)

            dunk_explosive = min(100, 0.55 * p_ds + 0.45 * p_dunks)
            raw_dd = 25 + 0.26 * dunk_explosive + 0.20 * p_dunks + 0.16 * p_ds
            raw_3pt = 25 + 0.38 * p_3pt + 0.28 * p_3pa36 + 0.20 * p_3share

            print(f'\n{nm} ({pos}) [bucket={bucket}, n={len(bucket_players)}]')
            print(f'  Dunks: share={ds:.3f}({p_ds:.0f}th) dunks={dunks:.0f}({p_dunks:.0f}th) drives/g={drives:.1f}')
            print(f'  3PT:  {three_pct:.3f}({p_3pt:.0f}th) 3pa36={fg3a36:.1f}({p_3pa36:.0f}th) 3share={three_share:.2f}({p_3share:.0f}th)')
            print(f'  raw_DD={raw_dd:.0f}  dunk_explosive={dunk_explosive:.0f}')
            print(f'  raw_3PT={raw_3pt:.0f}')
