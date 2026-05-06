import sys, os, json
sys.path.insert(0, 'nba2k26_generator')
from generator_cli import *
from generator_cli_ml import compute_attributes_ml

players = [
    ("Luka Doncic", "PG", 90),
    ("Jalen Brunson", "PG", 87),
    ("Karl-Anthony Towns", "C", 87),
    ("Jayson Tatum", "PF", 86),
    ("Jaylen Brown", "SF", 84),
    ("LaMelo Ball", "PG", 89),
    ("Austin Reaves", "SG", 82),
    ("Deandre Ayton", "C", 81),
    ("LeBron James", "SF", 89),
    ("CJ McCollum", "PG", 82),
]

rows = load_rows("NBA Site data")
results = []

for name, pos_2k, ovr_2k in players:
    row = select_player_season_row(rows, name, "2024-25")
    
    # Compute like main.cjs does
    tendencies = compute_tendencies(row)
    bundle = compute_attributes_ml(row, tendencies, "Player Roles", rows)
    attrs = bundle.get("attributes", {})
    family_scores = compute_attribute_family_averages(attrs)
    our_ovr = bundle.get("ovr", compute_overall_rating(row.get("position", ""), attrs, family_scores))
    
    results.append({
        "name": name,
        "pos_row": row.get("position", "N/A"),
        "pos_2k": pos_2k,
        "ovr_2k": ovr_2k,
        "our_ovr": our_ovr,
        "diff": our_ovr - ovr_2k,
        "family_scores": {k: int(v) for k, v in family_scores.items()},
    })

print(json.dumps(results, indent=2))
