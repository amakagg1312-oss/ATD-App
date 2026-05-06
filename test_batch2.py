import sys
import time

project_root = r"D:\project"
db_dir = r"D:\project\NBA Site data"
roles_dir = r"D:\project\Player Roles"

sys.path.insert(0, r"D:\project\nba2k26_generator")

print(f"t=0: starting imports", flush=True)
t0 = time.time()

print(f"t={time.time()-t0:.1f}: importing generator_cli...", flush=True)
from generator_cli import (
    load_rows,
    select_player_season_row,
    compute_tendencies,
    compute_attribute_family_averages,
    compute_overall_rating,
    compute_badge_groups,
    ATTRIBUTE_FAMILIES,
    THREE_POINT_RULES,
    MID_POST_RULES,
    DRIBBLE_RULES,
    DEFENSE_RULES,
    repair_mojibake_text,
)
print(f"t={time.time()-t0:.1f}: generator_cli imported", flush=True)

print(f"t={time.time()-t0:.1f}: importing generator_cli_ml...", flush=True)
from generator_cli_ml import compute_attributes_ml
print(f"t={time.time()-t0:.1f}: generator_cli_ml imported", flush=True)

print(f"t={time.time()-t0:.1f}: calling load_rows...", flush=True)
rows = load_rows(db_dir)
print(f"t={time.time()-t0:.1f}: load_rows returned, {len(rows)} rows", flush=True)

print(f"t={time.time()-t0:.1f}: calling select_player_season_row...", flush=True)
row = select_player_season_row(rows, "LeBron James", "2025-26")
print(f"t={time.time()-t0:.1f}: found row: {row.get('player_name')}", flush=True)

print(f"t={time.time()-t0:.1f}: calling compute_tendencies...", flush=True)
tendency_results = compute_tendencies(row)
print(f"t={time.time()-t0:.1f}: computed {len(tendency_results)} tendencies", flush=True)

print(f"t={time.time()-t0:.1f}: calling compute_attributes_ml...", flush=True)
ml_result = compute_attributes_ml(row, tendency_results, roles_dir, rows)
print(f"t={time.time()-t0:.1f}: ML result keys: {list(ml_result.keys())}", flush=True)

print("DONE")
