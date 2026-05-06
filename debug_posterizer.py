"""Debug: check raw stats for Posterizer badge."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from nba2k26_generator.generator_cli import load_rows

rows = load_rows(os.path.join(os.getcwd(), "Generator Database"))

def as_float(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except:
        return default

targets = ['Anthony Edwards', 'Victor Wembanyama', 'Shai Gilgeous-Alexander',
           'LeBron James', 'Jayson Tatum', 'Giannis Antetokounmpo', 'Ja Morant']
for name in targets:
    target = name.lower()
    row = None
    for r in rows:
        pname = str(r.get("player_name", "")).strip().lower()
        if pname == target:
            row = r
            break
    if not row:
        print("{}: NOT FOUND".format(name))
        continue

    dunks_share = as_float(row, "shooting_percent_dunks_of_fga")
    fga_pg = as_float(row, "per_game_fga_per_game")
    dunks_pg = dunks_share * fga_pg if fga_pg > 0 else 0
    driving_dunk = as_float(row, "driving_dunk", -1)
    drives_pg = as_float(row, "tracking_drives_pg")
    vertical = as_float(row, "vertical", -1)

    print("{}: dunks_share={:.4f}  fga_pg={:.1f}  dunks_pg={:.2f}  drives_pg={:.1f}".format(
        name, dunks_share, fga_pg, dunks_pg, drives_pg))
