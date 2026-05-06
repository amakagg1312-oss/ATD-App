import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from nba2k26_generator.nba_site_normalization import load_nba_site_rows
from nba2k26_generator.generator_cli import compute_attributes, compute_tendencies

rows = load_nba_site_rows('NBA Site data')

# Pre-compute everything once
all_data = []
for r in rows:
    tends = compute_tendencies(r)
    result = compute_attributes(r, tends, 'Player Roles', all_rows=rows)
    a = result['attributes']
    t_map = {t.name: t.final for t in tends}
    all_data.append((r, a, t_map))

# --- Reaves ---
for r, a, t_map in all_data:
    if 'reaves' in r.get('player_name','').lower():
        print(f"=== {r['player_name']} ({r['position']}) ===")
        print(f"  PerD={a['Perimeter Defense']} Stl={a['Steal']} "
              f"PassPerc={a['Pass Perception']} IntD={a['Interior Defense']} "
              f"Blk={a['Block']} HelpIQ={a['Help Defense IQ']} DefCon={a['Defensive Consistency']}")
        for k in ['advanced_stl_percent','advanced_blk_percent','per_100_stl_per_100_poss',
                   'hustle_deflections_per_game','hustle_contested_shots_per_game']:
            print(f"  {k}: {r.get(k, 'N/A')}")
        print()
        break

# --- Doncic ---
for r, a, t_map in all_data:
    if 'luka' in r.get('player_name','').lower():
        print(f"=== {r['player_name']} ({r['position']}) ===")
        print(f"  StDnk attr={a['Standing Dunk']} DrDnk attr={a['Driving Dunk']}")
        print(f"  Standing Dunk tend={t_map.get('Standing Dunk','?')} "
              f"Driving Dunk tend={t_map.get('Driving Dunk','?')} "
              f"Alley-Oop tend={t_map.get('Alley-Oop','?')} "
              f"Flashy Dunk tend={t_map.get('Flashy Dunk','?')}")
        for k in ['shooting_percent_fga_from_dunks','scoring_pct_pts_paint','tracking_drives_per_game']:
            print(f"  {k}: {r.get(k, 'N/A')}")
        print()
        break

# --- Suspect scans ---
print("=== SUSPECT: High PerD (>=82) but low stl% (<1.8) ===")
for r, a, t_map in all_data:
    stl_pct = float(r.get('advanced_stl_percent', 0) or 0)
    if a['Perimeter Defense'] >= 82 and stl_pct < 1.8:
        print(f"  {r['player_name']} ({r['position']}): PerD={a['Perimeter Defense']} Stl={a['Steal']} stl%={stl_pct:.1f}")

print("\n=== SUSPECT: High Steal (>=80) but low stl% (<1.5) ===")
for r, a, t_map in all_data:
    stl_pct = float(r.get('advanced_stl_percent', 0) or 0)
    if a['Steal'] >= 80 and stl_pct < 1.5:
        print(f"  {r['player_name']} ({r['position']}): Stl={a['Steal']} stl%={stl_pct:.1f}")

print("\n=== SUSPECT: DrDnk tend >=40 or StDnk tend >=35 but dunks_share < 0.02 ===")
for r, a, t_map in all_data:
    dunk_share = float(r.get('shooting_percent_fga_from_dunks', 0) or 0)
    dd = t_map.get('Driving Dunk', 0)
    sd = t_map.get('Standing Dunk', 0)
    ao = t_map.get('Alley-Oop', 0)
    if (dd >= 40 or sd >= 35) and dunk_share < 0.02:
        print(f"  {r['player_name']} ({r['position']}): DrDnk={dd} StDnk={sd} AlleyOop={ao} dunks_share={dunk_share:.3f}")

print("\n=== SUSPECT: PassPerc >= 82 but ast% < 15 ===")
for r, a, t_map in all_data:
    ast_pct = float(r.get('advanced_ast_percent', 0) or 0)
    if a['Pass Perception'] >= 82 and ast_pct < 15:
        print(f"  {r['player_name']} ({r['position']}): PassPerc={a['Pass Perception']} ast%={ast_pct:.1f}")

print("\n=== SUSPECT: High Floater (>=45) for bigs with low drives ===")
for r, a, t_map in all_data:
    pos = r.get('position','')
    is_big = 'C' in pos or 'PF' in pos
    drives = float(r.get('tracking_drives_per_game', 0) or 0)
    fl = t_map.get('Floater', 0)
    if is_big and fl >= 40 and drives < 5:
        print(f"  {r['player_name']} ({pos}): Floater={fl} drives_pg={drives:.1f}")

print("\n=== SUSPECT: Eurostep/Spin >= 35 for bigs who dont create ===")
for r, a, t_map in all_data:
    pos = r.get('position','')
    is_big = 'C' in pos or 'PF' in pos
    eu = t_map.get('Eurostep', 0)
    sp = t_map.get('Spin Layup', 0)
    drives = float(r.get('tracking_drives_per_game', 0) or 0)
    uast2 = float(r.get('shooting_pct_uast_2pm', 0) or 0)
    if is_big and (eu >= 35 or sp >= 35) and drives < 4:
        print(f"  {r['player_name']} ({pos}): Euro={eu} Spin={sp} drives_pg={drives:.1f}")

