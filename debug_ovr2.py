from nba2k26_generator.generator_cli import load_rows, compute_attributes, compute_tendencies

rows = load_rows('NBA Site data')
season_rows = [r for r in rows if str(r.get('season_label','')).startswith('2025')]
by_player = {}
for r in season_rows:
    name = r.get('player_name','')
    mp = float(r.get('totals_mp', 0) or 0)
    if name not in by_player or mp > float(by_player[name].get('totals_mp', 0) or 0):
        by_player[name] = r

targets = ['Kevin Porter Jr.', 'Tyrese Maxey', 'Stephon Castle', 'Ryan Rollins',
           'Tim Hardaway Jr.', 'Luguentz Dort', 'Sam Hauser']
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
    ppg = float(r.get('per_game_pts_per_game', 0) or 0)
    apg = float(r.get('per_game_ast_per_game', 0) or 0)
    mpg = float(r.get('per_game_mp_per_game', 0) or 0)
    usg = float(r.get('advanced_usg_percent', 0) or 0)
    ts = float(r.get('advanced_ts_percent', 0) or 0)
    print(f'{name} OVR={ovr} ({r.get("position","")}) | {ppg:.1f}pts {apg:.1f}ast | {mpg:.1f}mpg USG={usg:.1f}% TS={ts:.1f}%')
    for k,v in family.items():
        print(f'  {k}: {v}')
    print()
