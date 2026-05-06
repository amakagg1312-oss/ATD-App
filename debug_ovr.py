from nba2k26_generator.generator_cli import load_rows, compute_attributes, compute_tendencies

rows = load_rows('NBA Site data')
season_rows = [r for r in rows if str(r.get('season_label','')).startswith('2025')]
by_player = {}
for r in season_rows:
    name = r.get('player_name','')
    mp = float(r.get('totals_mp', 0) or 0)
    if name not in by_player or mp > float(by_player[name].get('totals_mp', 0) or 0):
        by_player[name] = r

targets = ['Nikola Jokic', 'Giannis Antetokounmpo', 'Victor Wembanyama',
           'Shai Gilgeous-Alexander', 'Dyson Daniels', 'Cason Wallace',
           'LeBron James', 'Kevin Durant']
for name in targets:
    r = by_player.get(name)
    if not r:
        print(f'{name}: not found')
        continue
    t = compute_tendencies(r)
    result = compute_attributes(r, t, 'Player Roles', all_rows=rows,
                                badges_txt_path='Badges/NBA 2K26 Badges.txt')
    family = result['family_scores']
    attrs = result['attributes']
    ovr = result['ovr']
    print(f'{name} OVR={ovr}  pos={r.get("position","")}')
    for k,v in family.items():
        print(f'  {k}: {v}')
    print(f'  STL={attrs.get("Steal",0)}, BLK={attrs.get("Block",0)}, PD={attrs.get("Perimeter Defense",0)}, ID={attrs.get("Interior Defense",0)}')
    print()
