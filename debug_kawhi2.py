"""Debug Kawhi PerD - replicate CLI call exactly."""
import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from nba2k26_generator.generator_cli import (
    load_rows, compute_attributes, compute_tendencies,
    select_player_season_row, as_float, remap, clamp
)

# --- Test 1: exact CLI call (Generator Database dir) ---
rows_cli = load_rows('Generator Database')
row_cli = select_player_season_row(rows_cli, 'Kawhi Leonard', '2024-25')
print(f"=== CLI path ===")
print(f"  Name: {row_cli['player_name']}, pos: {row_cli.get('position','?')}")
print(f"  advanced_dws: {row_cli.get('advanced_dws','MISSING')}")
print(f"  advanced_stl_percent: {row_cli.get('advanced_stl_percent','MISSING')}")
dws = as_float(row_cli, 'advanced_dws')
stl = as_float(row_cli, 'advanced_stl_percent')
blk = as_float(row_cli, 'advanced_blk_percent')
mp  = as_float(row_cli, 'totals_mp')
stl_s = remap(stl, 0.8, 3.4, 0, 100)
blk_s = remap(blk, 0.2, 4.5, 0, 100)
dws_s = remap(dws, 0.08, 0.20, 0, 100)
mp_s  = remap(mp, 700, 3100, 0, 100)
peak = clamp(0.38*stl_s + 0.20*blk_s + 0.30*dws_s + 0.12*mp_s, 0, 100)
print(f"  defense_peak_signal={peak:.1f}  (stl_s={stl_s:.1f} dws_s={dws_s:.1f} dws={dws:.4f})")
print(f"  Gate: peak>=44? {peak>=44} | stl>=1.6? {stl>=1.6} | dws>=0.09? {dws>=0.09}")

t = compute_tendencies(row_cli)
result = compute_attributes(row_cli, t, 'Player Roles', all_rows=rows_cli, badges_txt_path='Badges/NBA 2K26 Badges.txt')
print(f"  PerD={result['attributes']['Perimeter Defense']} Stl={result['attributes']['Steal']}")

print()

# --- Test 2: naive rows (like debug_kawhi2.py did) ---
rows_nba = load_rows('NBA Site data')
kawhi_first = [r for r in rows_nba if 'kawhi' in str(r.get('player_name','')).lower()][0]
print(f"=== NBA Site data path (rows[0]) ===")
print(f"  Name: {kawhi_first['player_name']}, pos: {kawhi_first.get('position','?')}")
print(f"  advanced_dws: {kawhi_first.get('advanced_dws','MISSING')}")
t2 = compute_tendencies(kawhi_first)
result2 = compute_attributes(kawhi_first, t2, 'Player Roles', all_rows=rows_nba, badges_txt_path='Badges/NBA 2K26 Badges.txt')
print(f"  PerD={result2['attributes']['Perimeter Defense']} Stl={result2['attributes']['Steal']}")
