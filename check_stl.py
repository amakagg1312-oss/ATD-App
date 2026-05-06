import sys; sys.path.insert(0,'.'); sys.stdout.reconfigure(encoding='utf-8')
from nba2k26_generator.nba_site_normalization import load_nba_site_rows
from nba2k26_generator.generator_cli import as_float

rows = load_nba_site_rows('NBA Site data')
# Check stl_pct values for known players
checks = ['Reaves', 'Gilgeous', 'Curry', 'Thybulle', 'Caruso', 'Herb Jones', 'Edwards']
for name in checks:
    for r in rows:
        if name.lower() in r.get('player_name','').lower():
            stl = as_float(r, "advanced_stl_percent")
            blk = as_float(r, "advanced_blk_percent")
            dws = as_float(r, "advanced_dws")
            mins = as_float(r, "bio_minutes_played")
            defl = as_float(r, "hustle_deflections_per_game")
            dash_3pt = as_float(r, "defense_dash_3pt_dfg_pct")
            dash_overall = as_float(r, "defense_dash_overall_dfg_pct")
            stl100 = as_float(r, "per_100_stl_per_100_poss")
            print(f"{r['player_name']}: stl%={stl:.1f} blk%={blk:.1f} dws={dws:.1f} mins={mins:.0f} defl={defl:.1f} dash_3pt={dash_3pt:.3f} dash_ovr={dash_overall:.3f} stl/100={stl100:.2f}")
            break
