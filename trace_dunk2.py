import sys; sys.path.insert(0,'.'); sys.stdout.reconfigure(encoding='utf-8')
from nba2k26_generator.nba_site_normalization import load_nba_site_rows
from nba2k26_generator.generator_cli import scale_0_100, as_float, clamp

rows = load_nba_site_rows('NBA Site data')
for r in rows:
    if 'luka' not in r.get('player_name','').lower():
        continue

    # Reproduce the exact computation
    dunks_share = as_float(r, "shooting_percent_dunks_of_fga")
    dunk_count = as_float(r, "shooting_num_of_dunks")
    scoring_pct_pts_paint = as_float(r, "scoring_pct_pts_paint")
    tracking_drives_pg = as_float(r, "tracking_drives_per_game")
    fta36 = as_float(r, "per_36_fta_per_36_min")
    rim_share = as_float(r, "shooting_percent_fga_from_x0_3_range")
    usg = as_float(r, "advanced_usg_percent")
    fg3ar = as_float(r, "shooting_percent_fga_from_x3p_range")
    pullup_freq = as_float(r, "pbp_features_pullup_freq")
    assisted2 = clamp(as_float(r, "shooting_percent_2_pt_fga_ast"), 0.0, 1.0)

    print(f"dunks_share={dunks_share:.4f}")
    print(f"tracking_drives_pg={tracking_drives_pg:.2f}")
    print(f"fta36={fta36:.2f}")
    print(f"rim_share={rim_share:.4f}")
    print(f"usg={usg:.1f}")
    print(f"scoring_pct_pts_paint={scoring_pct_pts_paint:.3f}")

    # drive_creation_signal
    stepback_freq = as_float(r, "pbp_features_stepback_freq")
    fade_freq = as_float(r, "pbp_features_fade_freq")
    pt_ball_handler_poss = as_float(r, "pt_ball_handler_poss_pct")
    tracking_avg_drib = as_float(r, "tracking_avg_dribbles_per_touch")

    drive_creation_signal_val = (
        0.30 * scale_0_100(tracking_drives_pg, 1.0, 22.0)
        + 0.20 * scale_0_100(pullup_freq, 0.02, 0.24)
        + 0.18 * scale_0_100(1.0 - assisted2, 0.10, 0.85)
        + 0.12 * scale_0_100(fta36, 0.5, 9.0)
        + 0.10 * (65.0 if True else 35.0)  # is_guard check simplified
        + 0.10 * scale_0_100(usg, 10.0, 35.0)
    )
    print(f"drive_creation_signal={drive_creation_signal_val:.1f} (estimated)")

    # drive signal
    contact_finish = (
        0.32 * scale_0_100(fta36, 0.8, 10.0)
        + 0.25 * scale_0_100(rim_share, 0.08, 0.75)
        + 0.18 * scale_0_100(drive_creation_signal_val, 20.0, 85.0)
        + 0.15 * scale_0_100(tracking_drives_pg, 2.0, 22.0)
        + 0.10 * scale_0_100(usg, 10.0, 35.0)
    )
    print(f"contact_finish_signal={contact_finish:.1f}")

    drive = (
        0.28 * scale_0_100(tracking_drives_pg, 1.0, 22.0)
        + 0.22 * scale_0_100(fta36, 0.5, 9.0)
        + 0.18 * scale_0_100(rim_share, 0.05, 0.70)
        + 0.12 * scale_0_100(scoring_pct_pts_paint, 0.10, 0.70)
        + 0.10 * scale_0_100(usg, 10, 35)
        + 0.10 * drive_creation_signal_val
    )
    drive += 0.10 * contact_finish
    print(f"drive_before_mult={drive:.1f}")

    # SF: drive *= 0.90 + 0.18 * (drive_creation_signal / 100.0)
    drive *= 0.90 + 0.18 * (drive_creation_signal_val / 100.0)
    print(f"drive_after_mult={drive:.1f}")

    # Now driving_dunk
    s1 = scale_0_100(dunks_share, 0.00, 0.25)
    s2 = scale_0_100(drive / 100.0, 0.20, 0.70)
    s3 = scale_0_100(tracking_drives_pg, 2.0, 20.0)
    print(f"\ndriving_dunk components: 0.45*{s1:.1f} + 0.30*{s2:.1f} + 0.25*{s3:.1f}")
    dd = 0.45 * s1 + 0.30 * s2 + 0.25 * s3
    print(f"driving_dunk = {dd:.1f}")

    break
