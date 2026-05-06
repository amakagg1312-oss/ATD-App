"""Debug: check Three-Point Shot attributes for a wide range of players."""
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

targets = [
    # Elite shooters (should be 90-95)
    'Stephen Curry', 'Klay Thompson', 'Damian Lillard',
    # Great shooters (should be 85-92)
    'Kevin Durant', 'Trae Young', 'Donovan Mitchell',
    # Good shooters (should be 78-88)
    'Jayson Tatum', 'Luka Doncic', 'Jamal Murray', 'Devin Booker',
    'Paul George', 'Kyrie Irving', 'Tyrese Haliburton',
    # Average/streaky shooters (should be 72-82)
    'Anthony Edwards', 'LeBron James', 'Jalen Brunson',
    'De\'Aaron Fox', 'Darius Garland',
    # Below average/non-shooters (should be 55-72)
    'Shai Gilgeous-Alexander', 'Ja Morant', 'Cade Cunningham',
    'Zion Williamson',
    # Non-shooters (should be 30-55)
    'Giannis Antetokounmpo', 'Victor Wembanyama',
    # Role player snipers (should be 85-92)
    'Buddy Hield', 'Duncan Robinson', 'Malik Beasley',
]

print(f"{'Player':<28} {'Pos':<5} {'3P%':<6} {'3PA':<6} {'3Shr':<7} {'FT%':<6} {'Cre3':<5} {'CS%':<5} {'CSpg':<5} {'3PT':<5} {'OVR'}")
print("-" * 100)

for name in targets:
    row = None
    for r in rows:
        if str(r.get("player_name","")).strip().lower() == name.lower():
            row = r; break
    if not row:
        print(f"{name:<30} NOT FOUND"); continue

    bundle = compute_attributes(row, compute_tendencies(row), roles_dir, rows, badges_txt_path=badges_txt)
    attrs = bundle.get("attributes", {})
    pos = str(row.get("position",""))

    three_pct = as_float(row, "per_36_x3p_percent")
    fg3a36 = as_float(row, "per_36_x3pa_per_36_min")
    three_share = as_float(row, "shooting_percent_fga_from_x3p_range")
    ft_pct = as_float(row, "per_36_ft_percent")
    fg3a_pg = as_float(row, "per_game_x3pa_per_game")
    assisted3 = as_float(row, "shooting_percent_assisted_x3p_fg")
    three_pct_abs = as_float(row, "per_game_x3p_percent", three_pct)
    three_pa_pg = as_float(row, "per_game_x3pa_per_game", max(0.0, fg3a36 * 0.74))
    creation3 = 1.0 - assisted3
    trk_cs_pct = as_float(row, "tracking_catch_shoot_fg3_pct")
    trk_cs_pg = as_float(row, "tracking_catch_shoot_fg3a_pg")

    three_attr = attrs.get("Three-Point Shot", "?")
    ovr = bundle.get("ovr", "?")

    print(f"{name:<28} {pos:<5} {three_pct_abs:<6.3f} {three_pa_pg:<6.1f} {three_share:<7.3f} {ft_pct:<6.3f} {creation3:<5.2f} {trk_cs_pct:<5.3f} {trk_cs_pg:<5.1f} {three_attr:<5} {ovr}")
