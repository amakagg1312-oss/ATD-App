"""Sanity check: PD, 3PT, and badges for several stars in 2024-25."""
import sys
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import load_rows, compute_attributes, compute_tendencies

rows = load_rows('NBA Site data')
BADGES_TXT = 'Badges/NBA 2K26 Badges.txt'
targets = ['Kevin Durant', 'Jaylen Brown', 'Donovan Mitchell', 'Kawhi Leonard', 'Stephen Curry']

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
    badges = result.get('badges', {})
    all_b = []
    shoot_b = []
    for g in badges.values():
        for b in (g or []):
            if b.get('value') and b['value'] != 'None':
                entry = b['name'] + '(' + b['value'] + ')'
                all_b.append(entry)
                if any(x in b.get('name', '') for x in ['Set Shot', 'Shifty', 'Deadeye', 'Limitless', 'Mini', 'Catch']):
                    shoot_b.append(entry)
    print(f'{nm}: PD={attrs["Perimeter Defense"]} 3PT={attrs["Three-Point Shot"]} badges={len(all_b)}')
    if shoot_b:
        print(f'  Shooting badges: {shoot_b}')
