import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from nba2k26_generator.nba_site_normalization import load_nba_site_rows
from nba2k26_generator.generator_cli import compute_attributes, compute_tendencies, as_float

rows = load_nba_site_rows('NBA Site data')

check = ['Reaves', 'Gilgeous', 'Luka', 'Giannis', 'Wemban', 'Edwards', 'Brunson', 'Caruso', 'Thybulle', 'Morant', 'LaVine', 'Fox', 'Brown']
key_tends = [
    'Drive', 'Standing Dunk', 'Driving Dunk', 'Alley-Oop', 'Flashy Dunk',
    'Floater', 'Eurostep', 'Putback',
]
for name in check:
    for r in rows:
        if name.lower() in r.get('player_name','').lower():
            tends = compute_tendencies(r)
            result = compute_attributes(r, tends, 'Player Roles', all_rows=rows)
            a = result['attributes']
            t_map = {t.name: t.final for t in tends}

            stl100 = as_float(r, "per_100_stl_per_100_poss")
            stl_pct = as_float(r, "advanced_stl_percent")
            blk_pct = as_float(r, "advanced_blk_percent")
            ds = as_float(r, "shooting_percent_dunks_of_fga")

            print(f"=== {r['player_name']} ({r['position']}) ===")
            print(f"  PerD={a['Perimeter Defense']} Stl={a['Steal']} PassPerc={a['Pass Perception']} "
                  f"HelpIQ={a['Help Defense IQ']} IntD={a['Interior Defense']} Blk={a['Block']} DefCon={a['Defensive Consistency']}")
            print(f"  stl_pct={stl_pct:.2f} (should ~= stl/100={stl100:.2f}) blk_pct={blk_pct:.2f} dunks_share={ds:.3f}")
            tend_str = "  Tends: " + ", ".join(f"{k}={t_map.get(k, '?')}" for k in key_tends)
            print(tend_str)
            print()
            break
