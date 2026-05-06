import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import load_rows

rows = load_rows('NBA Site data')
targets = ['Gobert', 'Giannis', 'Zion', 'Aaron Gordon', 'Anthony Davis', 'Doncic', 'Kessler', 'Luka', 'Morant', 'Curry']

seen = set()
for r in rows:
    n = r.get('player_name', '')
    for t in targets:
        if t.lower() in n.lower() and n not in seen:
            seen.add(n)
            drives = r.get('tracking_drives_pg', 0)
            usg = r.get('advanced_usg_percent', 0)
            pos = r.get('position', '')
            ds = r.get('tracking_dunks_share', 0)
            dunks = r.get('tracking_total_dunks', 0)
            three_pa = r.get('per_game_x3pa_per_game', 0)
            three_pct = r.get('per_game_x3p_percent', 0)
            print(f"{n[:25]:25} {pos:3} drives/g={drives:.1f} usg={usg:.1f} dunks={dunks:.0f} dunk_share={ds:.3f} 3PA={three_pa:.1f} 3PCT={three_pct:.3f}")
            break
