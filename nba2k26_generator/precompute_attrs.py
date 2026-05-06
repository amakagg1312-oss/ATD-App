"""Pre-compute ML attributes for all players. Run ONCE to create cache.

This takes ~40 min due to slow pandas/sklearn imports, but only needs to run once.
Output: precomputed_attrs.json mapping "player_name|season" -> {attributes, ovr, roles}
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

start = time.time()
print(f"[{time.time()-start:.0f}s] Starting pre-computation...")

from generator_cli import load_rows, compute_tendencies
from generator_cli_ml import compute_attributes_ml

project_root = os.path.join(os.path.dirname(__file__), "..")
db_dir = os.path.join(project_root, "NBA Site data")
roles_dir = os.path.join(project_root, "Player Roles")

print(f"[{time.time()-start:.0f}s] Loading rows...")
rows = load_rows(db_dir)
print(f"[{time.time()-start:.0f}s] Loaded {len(rows)} rows")

output = {}
for i, row in enumerate(rows):
    name = str(row.get("player_name", "")).strip()
    season = str(row.get("season_label", "")).strip()
    if not name or not season:
        continue
    
    key = f"{name.lower()}|{season.lower()}"
    if key in output:
        continue
    
    try:
        tendency_results = compute_tendencies(row)
        row_copy = dict(row)
        row_copy["season_label"] = season
        ml_result = compute_attributes_ml(row_copy, tendency_results, roles_dir, rows)
        
        output[key] = {
            "attributes": ml_result.get("attributes", {}),
            "ovr": ml_result.get("ovr", 75),
            "roles": ml_result.get("roles", []),
        }
        
        if (i + 1) % 100 == 0:
            print(f"[{time.time()-start:.0f}s] Processed {i+1}/{len(rows)} rows, {len(output)} unique players")
    except Exception as e:
        pass

out_path = os.path.join(os.path.dirname(__file__), "precomputed_attrs.json")
with open(out_path, "w") as f:
    json.dump(output, f)

print(f"[{time.time()-start:.0f}s] Saved {len(output)} player profiles to {out_path}")
