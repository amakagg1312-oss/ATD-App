"""Trace 3PT formula for specific players."""
import sys, os, math
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import load_rows, as_float

rows = load_rows('NBA Site data')
rows2526 = [r for r in rows if '2025-26' in str(r.get('season_label', ''))]

def position_bucket(pos_text):
    p = (pos_text or '').upper()
    if 'C' in p and 'PF' not in p:
        return 'C'
    if 'PF' in p or 'SF' in p:
        return 'F'
    return 'G'

def pct(key, val, bucket_players):
    vals = [as_float(r, key) for r in bucket_players]
    vals = [v for v in vals if not math.isnan(v) and not math.isinf(v)]
    n = len(vals)
    if not n:
        return 0.0
    below = sum(v < val for v in vals)
    at = sum(v == val for v in vals)
    return (below + 0.5 * at) / n * 100.0

targets = ['Tatum', 'Dončić', 'Gobert', 'Anunoby']

for r in rows2526:
    nm = r.get('player_name', '')
    for t in targets:
        if t.lower() in nm.lower():
            pos = r.get('position', '?')
            bucket = position_bucket(pos)
            bucket_players = [rx for rx in rows2526 if position_bucket(str(rx.get('position', ''))) == bucket]

            three_pct = as_float(r, 'per_36_x3p_percent')
            fg3a36 = as_float(r, 'per_36_x3pa_per_36_min')
            three_share = as_float(r, 'shooting_percent_fga_from_x3p_range')
            ft_pct = as_float(r, 'per_36_ft_percent')

            p_3pt = pct('per_36_x3p_percent', three_pct, bucket_players)
            p_3pa36 = pct('per_36_x3pa_per_36_min', fg3a36, bucket_players)
            p_3share = pct('shooting_percent_fga_from_x3p_range', three_share, bucket_players)
            p_ft = pct('per_36_ft_percent', ft_pct, bucket_players)

            raw_3pt = 25 + 0.38*p_3pt + 0.28*p_3pa36 + 0.20*p_3share + 0.14*p_ft
            
            # remap(val, 15, 90, 25, 100)
            def remap(v, in_lo, in_hi, out_lo, out_hi):
                t = (v - in_lo) / (in_hi - in_lo) if (in_hi - in_lo) != 0 else 0
                t = max(0, min(1, t))
                return out_lo + t * (out_hi - out_lo)

            final_3pt = remap(raw_3pt, 15, 90, 25, 100)

            print(f'\n{nm} ({pos}) bucket={bucket}:')
            print(f'  3PT%={three_pct:.3f} 3pa36={fg3a36:.1f} 3share={three_share:.2f} ft%={ft_pct:.3f}')
            print(f'  p_3pt={p_3pt:.0f} p_3pa36={p_3pa36:.0f} p_3share={p_3share:.0f} p_ft={p_ft:.0f}')
            print(f'  raw_3pt_formula={raw_3pt:.1f}  after_remap={final_3pt:.1f}')
            print(f'  Expected final (~): {min(95, max(25, round(final_3pt)))}')
