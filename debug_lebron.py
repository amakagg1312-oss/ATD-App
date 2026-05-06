"""Debug LeBron role signals."""
import sys
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import (
    load_rows, select_player_season_row, as_float, remap, clamp,
    select_player_roles_from_stats, load_role_catalog
)

rows = load_rows('Generator Database')
row = select_player_season_row(rows, 'LeBron James', '2024-25')

def n(v, lo, hi): return remap(v, lo, hi, 0.0, 1.0)

usg = as_float(row, 'advanced_usg_percent')
ast_pct = as_float(row, 'advanced_ast_percent')
tov_pct = as_float(row, 'advanced_tov_percent')
ts_pct = as_float(row, 'advanced_ts_percent')
fg3a_pg = as_float(row, 'per_game_x3pa_per_game')
three_pct = as_float(row, 'per_36_x3p_percent') or as_float(row, 'per_game_x3p_percent')
rim_share = as_float(row, 'shooting_percent_fga_from_x0_3_range')
close_share = as_float(row, 'shooting_percent_fga_from_x3_10_range')
stl_pct = as_float(row, 'advanced_stl_percent')
blk_pct = as_float(row, 'advanced_blk_percent')
orb_pct = as_float(row, 'advanced_orb_percent')
drb_pct = as_float(row, 'advanced_drb_percent')
mp = as_float(row, 'totals_mp')
assisted2 = as_float(row, 'shooting_percent_assisted_x2p_fg')
age = as_float(row, 'age', 27.0)
position = row.get('position', '?')

usage = n(usg, 12.0, 35.0)
passing = n(ast_pct, 5.0, 42.0)
shooting = 0.45 * n(three_pct, 0.30, 0.41) + 0.35 * n(fg3a_pg, 0.5, 8.0)
defense = 0.45 * n(stl_pct, 0.3, 3.5) + 0.35 * n(blk_pct, 0.2, 10.0) + 0.20 * n(orb_pct + drb_pct, 10.0, 48.0)
iq = 0.45 * n(ts_pct, 0.48, 0.68) + 0.35 * n(1.0 - n(tov_pct, 8.0, 20.0), 0.0, 1.0) + 0.20 * passing
workload = n(mp, 350.0, 3000.0)
rim_pressure = 0.45 * n(rim_share + close_share, 0.18, 0.72)
off_creation = 0.55 * usage + 0.45 * (1.0 - n(assisted2, 0.10, 0.85))
age_curve = n(1.0 - n(age, 19.0, 37.0), 0.0, 1.0)

hier_signal = clamp(0.58 * usage + 0.42 * passing, 0.0, 1.0)
hier_int = clamp(0.7 * usage + 0.3 * passing, 0.0, 1.0)
core_signal = clamp(0.45 * workload + 0.30 * iq + 0.25 * age_curve, 0.0, 1.0)

print(f"LeBron 2024-25 | pos={position} | age={age:.0f}")
print(f"  USG={usg:.1f}%  AST={ast_pct:.1f}%  TS={ts_pct:.3f}  TOV={tov_pct:.1f}%")
print(f"  Rim={rim_share:.2f}  RimClose={rim_share+close_share:.2f}")
print()
print(f"  usage={usage:.3f}  passing={passing:.3f}  shooting={shooting:.3f}")
print(f"  defense={defense:.3f}  iq={iq:.3f}  rim_pressure={rim_pressure:.3f}")
print(f"  off_creation={off_creation:.3f}  workload={workload:.3f}  age_curve={age_curve:.3f}")
print()
print(f"  HIERARCHY signal={hier_signal:.3f}  intensity={hier_int:.3f}")
print(f"  CORE signal={core_signal:.3f}")
print()

role_catalog = load_role_catalog('Player Roles')
roles = select_player_roles_from_stats(row, role_catalog)
print(f"  Assigned roles: {' · '.join(roles)}")
