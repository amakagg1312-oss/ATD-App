"""Debug: check Driving Dunk signals for SGA vs Ant."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from nba2k26_generator.generator_cli import load_rows, compute_tendencies, compute_attributes

db_dir = os.path.join(os.getcwd(), "Generator Database")
roles_dir = os.path.join(os.getcwd(), "Player Roles")
badges_txt = os.path.join(os.getcwd(), "Badges", "NBA 2K26 Badges.txt")
rows = load_rows(db_dir)

def as_float(row, key, default=0.0):
    try: return float(row.get(key, default))
    except: return default

def remap(v, lo, hi, out_lo, out_hi):
    if hi == lo: return out_lo
    return out_lo + (out_hi - out_lo) * ((v - lo) / (hi - lo))

targets = ['Anthony Edwards', 'Shai Gilgeous-Alexander', 'Giannis Antetokounmpo',
           'LeBron James', 'Ja Morant', 'Victor Wembanyama', 'Zion Williamson',
           'Jalen Green', 'De\'Aaron Fox', 'Derrick Jones Jr.']
for name in targets:
    row = None
    for r in rows:
        if str(r.get("player_name","")).strip().lower() == name.lower():
            row = r; break
    if not row:
        print("{}: NOT FOUND".format(name)); continue

    bundle = compute_attributes(row, compute_tendencies(row), roles_dir, rows, badges_txt_path=badges_txt)
    attrs = bundle.get("attributes", {})

    dunks = as_float(row, "shooting_num_of_dunks")
    dunks_share = as_float(row, "shooting_percent_dunks_of_fga")
    rim_share = as_float(row, "shooting_percent_fga_from_x0_3_range")
    fta36 = as_float(row, "per_36_fta_per_36_min")
    usg = as_float(row, "advanced_usg_percent")
    drives_pg = as_float(row, "tracking_drives_pg")
    pos = str(row.get("position",""))

    ht = as_float(row, "player_info_ht_in_in", as_float(row, "height_in", 78.0))
    wt = as_float(row, "player_info_wt", as_float(row, "weight_lbs", as_float(row, "weight", 220.0)))
    age = as_float(row, "age", 27.0)

    print("{} [{}]".format(name, pos))
    print("  dunks={:.0f}  dunks_share={:.4f}  rim_share={:.3f}  fta36={:.1f}  usg={:.1f}  drives_pg={:.1f}".format(
        dunks, dunks_share, rim_share, fta36, usg, drives_pg))
    print("  ht={:.0f}in  wt={:.0f}lbs  power_build={:.2f}  age={:.0f}".format(ht, wt, wt/max(ht,70), age))
    print("  Driving Dunk attr = {}".format(attrs.get("Driving Dunk", "?")))
    print("  Standing Dunk attr = {}".format(attrs.get("Standing Dunk", "?")))
    print("  Vertical attr = {}".format(attrs.get("Vertical", "?")))
    print("  Strength attr = {}".format(attrs.get("Strength", "?")))
    roles = bundle.get("roles", [])
    print("  Roles: {}".format(", ".join(roles) if roles else "n/a"))
    print()
