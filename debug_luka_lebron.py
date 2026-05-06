"""Debug LeBron PD and Luka 3PT + badges."""
import sys
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import (
    load_rows, compute_attributes, compute_tendencies, as_float
)

rows = load_rows('NBA Site data')
BADGES_TXT = 'Badges/NBA 2K26 Badges.txt'

targets = ['LeBron James', 'Luka Doncic', 'Luka Dončić']

for r in rows:
    nm = r.get('player_name', '')
    season = r.get('season_label', '')
    if not any(t.lower() in nm.lower() for t in targets):
        continue
    if '2024-25' not in season:
        continue
    tend = compute_tendencies(r)
    result = compute_attributes(r, tend, 'Player Roles', all_rows=rows, badges_txt_path=BADGES_TXT)
    attrs = result['attributes']
    badge_groups = result.get('badges', {})
    pos = r.get('position', '?')
    # raw defensive stats
    stl_pct = as_float(r, 'advanced_stl_percent')
    blk_pct = as_float(r, 'advanced_blk_percent')
    dws = as_float(r, 'advanced_dws')
    three_pct = as_float(r, 'per_game_x3p_percent')
    usg = as_float(r, 'advanced_usg_percent')
    print(f'\n=== {nm} ({pos}) [{season}] ===')
    print(f'  Raw: STL%={stl_pct:.2f}  BLK%={blk_pct:.2f}  DWS={dws:.3f}  3P%={three_pct:.3f}  USG={usg:.1f}%')
    print(f'  PD={attrs["Perimeter Defense"]}  Steal={attrs["Steal"]}  HelpIQ={attrs["Help Defense IQ"]}')
    print(f'  3PT={attrs["Three-Point Shot"]}  MR={attrs["Mid-Range Shot"]}')
    all_badges = []
    badges_dict = result.get('badges', {})
    for grp, grp_items in badges_dict.items():
        for b in (grp_items or []):
            v = b.get('value', '')
            if v and v != 'None':
                all_badges.append(f'{b["name"]}({v})')
    print(f'  Badges ({len(all_badges)}): {", ".join(all_badges)}')
