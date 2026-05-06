"""
Targeted deep-dives: players/attributes where something smells off.
"""
import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from nba2k26_generator.generator_cli import load_rows, compute_attributes, compute_tendencies

rows = load_rows('NBA Site data')
season_rows = [r for r in rows if str(r.get('season_label','  ')).startswith('2025')]
by_player = {}
for r in season_rows:
    name = r.get('player_name','')
    mp = float(r.get('totals_mp', 0) or 0)
    if name not in by_player or mp > float(by_player[name].get('totals_mp', 0) or 0):
        by_player[name] = r

def fv(r, k):
    return float(r.get(k, 0) or 0)

# Players to check with known issues from the report
targets = [
    # Driving Dunk inflated for non-dunkers
    'Anthony Edwards', 'Stephon Castle', 'Cade Cunningham', 'Tyrese Maxey',
    'Desmond Bane', 'Jaylen Brown', 'Kon Knueppel',
    # BH high for bigs
    'Matas Buzelis', 'Zion Williamson',
    # BH low for guards
    'Tim Hardaway Jr.', 'Keon Ellis',
    # ORB high for guards
    'Amen Thompson', 'Dyson Daniels', 'Jordan Goodwin', 'Gary Payton II',
    # Speed for bigs (check legitimacy)
    'Zion Williamson', 'Giannis Antetokounmpo', 'Scottie Barnes',
    # 3PT inflated: sorting showed fg3pct shown as 0.5 for many – need to verify
    'Bobby Portis', 'Jaylon Tyson', 'Cam Spencer',
    # Tim Hardaway with speed 53
    'Tim Hardaway Jr.',
]

print(f'{"Name":<30} {"Pos":<4} {"OVR":>3}  {"DD":>3}/{"SD":>3}  {"BH":>3}/{"SWB":>3}  {"ORB":>3}  {"Spd":>3}  {"3PT":>3}  {"FT":>3}  | raw: dunk% apg fg3pa@fg3% ftpa@ft%')
print('-'*120)

for name in dict.fromkeys(targets):  # dedup while preserving order
    r = by_player.get(name)
    if not r:
        continue
    t = compute_tendencies(r)
    result = compute_attributes(r, t, 'Player Roles', all_rows=rows,
                                badges_txt_path='Badges/NBA 2K26 Badges.txt')
    a = result['attributes']
    ovr = result['ovr']
    pos = r.get('position','')
    dd    = a.get('Driving Dunk', 0)
    sd    = a.get('Standing Dunk', 0)
    bh    = a.get('Ball Handle', 0)
    swb   = a.get('Speed with Ball', 0)
    orb   = a.get('Offensive Rebound', 0)
    spd   = a.get('Speed', 0)
    a3pt  = a.get('Three-Point Shot', 0)
    aft   = a.get('Free Throw', 0)
    dunk  = fv(r, 'shooting_percent_dunks_of_fga')
    apg   = fv(r, 'per_game_ast_per_game')
    fg3pa = fv(r, 'per_game_x3pa_per_game')
    fg3pct= fv(r, 'per_game_x3p_percent')
    ftpa  = fv(r, 'per_game_fta_per_game')
    ftpct = fv(r, 'per_game_ft_percent')
    orb_pct= fv(r, 'advanced_orb_percent')
    print(f'{name:<30} {pos:<4} {ovr:>3}  {dd:>3}/{sd:>3}  {bh:>3}/{swb:>3}  {orb:>3}  {spd:>3}  {a3pt:>3}  {aft:>3}  | {dunk:.1%}  {apg:.1f}apg  {fg3pa:.1f}@{fg3pct:.0%}  {ftpa:.1f}@{ftpct:.0%}  orb%={orb_pct:.1f}')
