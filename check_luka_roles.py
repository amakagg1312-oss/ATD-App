"""Quick check of Luka and Brown roles after fix."""
import sys
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import load_rows, compute_attributes, compute_tendencies

rows = load_rows('NBA Site data')
targets = ['oncic', 'Jaylen Brown']
for r in rows:
    nm = r.get('player_name', '')
    season = r.get('season_label', '')
    if '2024-25' not in season:
        continue
    nm_ascii = nm.encode('ascii', 'replace').decode()
    hit = any(t in nm for t in targets) or any(t in nm_ascii for t in targets)
    if not hit:
        continue
    tend = compute_tendencies(r)
    result = compute_attributes(r, tend, 'Player Roles', all_rows=rows, badges_txt_path='Badges/NBA 2K26 Badges.txt')
    print(f"{nm_ascii} ({r.get('position','?')}): roles={result['roles']}")
