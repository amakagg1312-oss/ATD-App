import sys; sys.path.insert(0,'.'); sys.stdout.reconfigure(encoding='utf-8')
from nba2k26_generator.nba_site_normalization import load_nba_site_rows
from nba2k26_generator.generator_cli import compute_tendencies, as_float, scale_0_100

rows = load_nba_site_rows('NBA Site data')
for r in rows:
    if 'luka' in r.get('player_name','').lower():
        # Trace dunk inputs
        dunks_share = as_float(r, "shooting_percent_dunks_of_fga")
        dunk_count = as_float(r, "shooting_num_of_dunks")
        scoring_pct_pts_paint = as_float(r, "scoring_pct_pts_paint")
        tracking_drives_pg = as_float(r, "tracking_drives_per_game")
        print(f"=== Luka Doncic dunk trace ===")
        print(f"dunks_share={dunks_share:.4f}")
        print(f"dunk_count={dunk_count:.1f}")
        print(f"scoring_pct_pts_paint={scoring_pct_pts_paint:.3f}")
        print(f"tracking_drives_pg={tracking_drives_pg:.1f}")

        # Compute the actual drive signal value
        tends = compute_tendencies(r)
        t_map = {t.name: t for t in tends}
        drive_t = t_map.get('Drive')
        dd_t = t_map.get('Driving Dunk')
        sd_t = t_map.get('Standing Dunk')
        ao_t = t_map.get('Alley-Oop')
        print(f"Drive: pre_cap={drive_t.pre_cap:.1f} final={drive_t.final} rec_cap={drive_t.recommended_cap} abs_cap={drive_t.absolute_cap}")
        print(f"DrivingDunk: pre_cap={dd_t.pre_cap:.1f} final={dd_t.final} rec_cap={dd_t.recommended_cap} abs_cap={dd_t.absolute_cap}")
        print(f"StandingDunk: pre_cap={sd_t.pre_cap:.1f} final={sd_t.final} rec_cap={sd_t.recommended_cap} abs_cap={sd_t.absolute_cap}")
        print(f"AlleyOop: pre_cap={ao_t.pre_cap:.1f} final={ao_t.final} rec_cap={ao_t.recommended_cap} abs_cap={ao_t.absolute_cap}")

        # Manual calc
        s1 = scale_0_100(dunks_share, 0.00, 0.25)
        s2 = scale_0_100(scoring_pct_pts_paint, 0.15, 0.70)
        s3 = scale_0_100(tracking_drives_pg, 2.0, 20.0)
        print(f"\nManual standing_dunk: 0.55*{s1:.1f} + 0.25*20(non-guard) + 0.20*{s2:.1f} = {0.55*s1 + 0.25*20 + 0.20*s2:.1f}")
        print(f"Manual driving_dunk: 0.45*{s1:.1f} + 0.30*scale(drive/100) + 0.25*{s3:.1f}")
        # Also check what `drive` variable is (the 0-100 raw signal)
        # drive in the formula is the raw pre_cap of 'Drive' tendency... let's check
        print(f"drive raw value used in driving_dunk formula is likely drive_creation_signal-based")
        break

# Also check Reaves
for r in rows:
    if 'reaves' in r.get('player_name','').lower():
        tends = compute_tendencies(r)
        t_map = {t.name: t for t in tends}
        result_keys = ['Perimeter Defense', 'Contest Shot', 'On-Ball Steal', 'Pass Interception', 'Block']
        print(f"\n=== Reaves tends ===")
        for k in result_keys:
            t = t_map.get(k)
            if t:
                print(f"  {k}: pre_cap={t.pre_cap:.1f} final={t.final} rec={t.recommended_cap} abs={t.absolute_cap}")
        stl_pct = as_float(r, "advanced_stl_percent")
        print(f"  stl_pct={stl_pct}")

        # Check per_100 stats
        stl100 = as_float(r, "per_100_stl_per_100_poss")
        print(f"  stl_per100={stl100:.2f}")
        break
