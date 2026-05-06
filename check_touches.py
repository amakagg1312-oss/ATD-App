import sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from nba2k26_generator.generator_cli import load_rows, compute_tendencies, as_float

rows = load_rows("d:/project/Generator Database")
p25 = [r for r in rows if r.get("season_label") == "2024-25"]

targets = [
    "Luka Dončić", "Devin Booker", "LeBron James", "Stephen Curry",
    "Shai Gilgeous-Alexander", "Jaxson Hayes", "Mark Williams",
    "Rudy Gobert", "Alex Caruso", "Draymond Green", "Isaiah Hartenstein",
    "Giannis Antetokounmpo", "Nikola Jokić",
]

print(f"{'PLAYER':<28} {'USG':>5} {'3PAr':>5} {'TTIdle':>8} {'TTShoot':>9}")
print("-" * 58)
for name in targets:
    r = next((x for x in p25 if x.get("player_name","") == name), None)
    if not r:
        print(f"{name:<28}  NOT FOUND"); continue
    tends_list = compute_tendencies(r)
    tends = {t.name: t.final for t in tends_list}
    usg = as_float(r, "advanced_usg_percent")
    fg3ar = as_float(r, "advanced_x3p_ar")
    tt_idle  = tends.get("Triple Threat Idle", 0)
    tt_shoot = tends.get("Triple Threat Shoot", 0)
    print(f"{name:<28} {usg:>5.1f} {fg3ar:>5.2f} {tt_idle:>8} {tt_shoot:>9}")







