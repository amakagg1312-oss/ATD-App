"""
Systematic attribute analysis: compare generated attributes against raw NBA stats
to find players where the attribute doesn't reflect real performance.
"""
import sys, os, csv
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from nba2k26_generator.generator_cli import load_rows, compute_attributes, compute_tendencies

rows = load_rows('NBA Site data')
season_rows = [r for r in rows if str(r.get('season_label','')).startswith('2025')]

by_player = {}
for r in season_rows:
    name = r.get('player_name','')
    mp = float(r.get('totals_mp', 0) or 0)
    if name not in by_player or mp > float(by_player[name].get('totals_mp', 0) or 0):
        by_player[name] = r

players = sorted(by_player.values(), key=lambda r: r.get('player_name', ''))
print(f'Analyzing {len(players)} players...\n')

def fv(r, k, default=0.0):
    return float(r.get(k, default) or default)

issues = []

for r in players:
    name = r.get('player_name', '')
    pos  = r.get('position', '')
    mp   = fv(r, 'totals_mp')
    if mp < 300:
        continue  # skip tiny samples

    try:
        t = compute_tendencies(r)
        result = compute_attributes(r, t, 'Player Roles', all_rows=rows,
                                    badges_txt_path='Badges/NBA 2K26 Badges.txt')
    except Exception as e:
        print(f'ERROR {name}: {e}')
        continue

    attrs = result['attributes']
    ovr   = result['ovr']
    is_guard  = any(x in pos.upper() for x in ('PG', 'SG'))
    is_big    = any(x in pos.upper() for x in ('PF', 'C'))
    is_wing   = 'SF' in pos.upper()

    # raw stats
    ppg     = fv(r, 'per_game_pts_per_game')
    apg     = fv(r, 'per_game_ast_per_game')
    rpg     = fv(r, 'per_game_trb_per_game')
    spg     = fv(r, 'per_game_stl_per_game')
    bpg     = fv(r, 'per_game_blk_per_game')
    mpg     = fv(r, 'per_game_mp_per_game')
    fg3pa   = fv(r, 'per_game_x3pa_per_game')
    fg3pct  = fv(r, 'per_game_x3p_percent')
    fg2pct  = fv(r, 'per_game_x2p_percent')
    fgpct   = fv(r, 'per_game_fg_percent')
    ftpct   = fv(r, 'per_game_ft_percent')
    ftpa    = fv(r, 'per_game_fta_per_game')
    usg     = fv(r, 'advanced_usg_percent')
    ts      = fv(r, 'advanced_ts_percent')
    orb_pct = fv(r, 'advanced_orb_percent')
    drb_pct = fv(r, 'advanced_drb_percent')
    ast_pct = fv(r, 'advanced_ast_percent')
    stl_pct = fv(r, 'advanced_stl_percent')
    blk_pct = fv(r, 'advanced_blk_percent')
    tov_pct = fv(r, 'advanced_tov_percent')

    a = attrs

    player_issues = []

    # ── 3PT SHOT ────────────────────────────────────────────────────────────
    # High 3pt attr but almost never shoots 3s
    if a.get('Three-Point Shot', 0) >= 78 and fg3pa < 1.0:
        player_issues.append(f'3PT={a["Three-Point Shot"]} but {fg3pa:.1f} 3pa/g')
    # Low 3pt attr but is a legitimate 3pt shooter
    if a.get('Three-Point Shot', 0) <= 55 and fg3pa >= 4.0 and fg3pct >= 0.36:
        player_issues.append(f'3PT={a["Three-Point Shot"]} but {fg3pa:.1f} 3pa @ {fg3pct:.0%}')
    # Good shooter rated too low
    if a.get('Three-Point Shot', 0) <= 65 and fg3pa >= 5.0 and fg3pct >= 0.38:
        player_issues.append(f'3PT={a["Three-Point Shot"]} low for {fg3pa:.1f}@{fg3pct:.0%}')

    # ── MID-RANGE ─────────────────────────────────────────────────────────
    mid_pct = fv(r, 'shooting_pct_2pt_mid_range')
    mid_fg  = fv(r, 'shooting_fga_2pt_mid_range')
    if a.get('Mid-Range Shot', 0) <= 55 and mid_fg >= 2.0 and mid_pct >= 0.44:
        player_issues.append(f'MID={a["Mid-Range Shot"]} low for {mid_fg:.1f}fga@{mid_pct:.0%}')
    if a.get('Mid-Range Shot', 0) >= 80 and ppg < 6 and usg < 10:
        player_issues.append(f'MID={a["Mid-Range Shot"]} very high for low-usage player')

    # ── BALL HANDLE ──────────────────────────────────────────────────────
    # Bigs (C/PF) with too high BH
    if a.get('Ball Handle', 0) >= 75 and is_big and ast_pct < 15:
        player_issues.append(f'BH={a["Ball Handle"]} very high for big (ast_pct={ast_pct:.1f}%)')
    # Guards/wings rated too low on BH when they clearly handle the ball
    if a.get('Ball Handle', 0) <= 55 and is_guard and apg >= 4.0:
        player_issues.append(f'BH={a["Ball Handle"]} low for guard with {apg:.1f}apg')
    # Bigs shouldn't have high BH unless they're a point forward
    if a.get('Ball Handle', 0) >= 80 and is_big:
        player_issues.append(f'BH={a["Ball Handle"]} extremely high for big')

    # ── DRIVING DUNK ──────────────────────────────────────────────────────
    dunk_pct = fv(r, 'shooting_percent_dunks_of_fga')
    if a.get('Driving Dunk', 0) >= 80 and is_guard and dunk_pct < 0.05:
        player_issues.append(f'DrDnk={a["Driving Dunk"]} high for guard (dunk%={dunk_pct:.1%})')
    if a.get('Driving Dunk', 0) >= 85 and dunk_pct < 0.02 and not is_big:
        player_issues.append(f'DrDnk={a["Driving Dunk"]} very high but only {dunk_pct:.1%} of FGA are dunks')
    # Rim-running big with low driving dunk
    if a.get('Driving Dunk', 0) <= 50 and is_big and dunk_pct >= 0.25:
        player_issues.append(f'DrDnk={a["Driving Dunk"]} low for rim runner ({dunk_pct:.0%} dunks)')

    # ── STANDING DUNK ─────────────────────────────────────────────────────
    if a.get('Standing Dunk', 0) >= 75 and is_guard:
        player_issues.append(f'StDnk={a["Standing Dunk"]} very high for guard')
    if a.get('Standing Dunk', 0) <= 40 and is_big and dunk_pct >= 0.20:
        player_issues.append(f'StDnk={a["Standing Dunk"]} low for rim-running big')

    # ── BLOCK ─────────────────────────────────────────────────────────────
    if a.get('Block', 0) >= 70 and is_guard and bpg < 0.3:
        player_issues.append(f'BLK={a["Block"]} high for guard ({bpg:.1f} bpg)')
    if a.get('Block', 0) >= 80 and is_guard:
        player_issues.append(f'BLK={a["Block"]} very high for guard')
    # Rim protectors rated too low
    if a.get('Block', 0) <= 55 and is_big and blk_pct >= 4.0:
        player_issues.append(f'BLK={a["Block"]} low for shot blocker (blk%={blk_pct:.1f}%)')

    # ── STEAL ─────────────────────────────────────────────────────────────
    # Too high for minimal steal producers
    if a.get('Steal', 0) >= 85 and stl_pct < 1.0:
        player_issues.append(f'STL={a["Steal"]} but stl%={stl_pct:.1f}% very low')
    # Too low for elite steal producers
    if a.get('Steal', 0) <= 55 and stl_pct >= 2.5 and spg >= 1.5:
        player_issues.append(f'STL={a["Steal"]} low for {spg:.1f}spg ({stl_pct:.1f}%)')

    # ── FREE THROW ────────────────────────────────────────────────────────
    if a.get('Free Throw', 0) <= 50 and ftpct >= 0.80 and ftpa >= 2.0:
        player_issues.append(f'FT={a["Free Throw"]} low for {ftpct:.0%} FT shooter')
    if a.get('Free Throw', 0) >= 80 and ftpct <= 0.60 and ftpa >= 2.0:
        player_issues.append(f'FT={a["Free Throw"]} high for {ftpct:.0%} FT shooter')

    # ── SPEED ─────────────────────────────────────────────────────────────
    if a.get('Speed', 0) >= 88 and is_big and mpg >= 15:
        player_issues.append(f'Speed={a["Speed"]} very high for big')
    if a.get('Speed', 0) <= 45 and is_guard and mpg >= 15:
        player_issues.append(f'Speed={a["Speed"]} very low for guard')

    # ── STRENGTH ────────────────────────────────────────────────────────
    if a.get('Strength', 0) >= 80 and is_guard and mpg >= 15:
        player_issues.append(f'Strength={a["Strength"]} very high for guard')
    # Bigs should have decent strength
    if a.get('Strength', 0) <= 40 and is_big and mpg >= 15:
        player_issues.append(f'Strength={a["Strength"]} low for big')

    # ── PERIMETER DEFENSE ────────────────────────────────────────────────
    if a.get('Perimeter Defense', 0) >= 85 and stl_pct < 0.8:
        player_issues.append(f'PD={a["Perimeter Defense"]} high for stl%={stl_pct:.1f}%')

    # ── INTERIOR DEFENSE ─────────────────────────────────────────────────
    if a.get('Interior Defense', 0) >= 85 and is_guard:
        player_issues.append(f'ID={a["Interior Defense"]} very high for guard')
    if a.get('Interior Defense', 0) <= 45 and is_big and blk_pct >= 2.0 and mpg >= 15:
        player_issues.append(f'ID={a["Interior Defense"]} low for rim protector big')

    # ── PASS ACCURACY / IQ / VISION ──────────────────────────────────────
    # Very high passing for non-playmakers
    if a.get('Pass IQ', 0) >= 85 and apg < 2.0 and ast_pct < 10:
        player_issues.append(f'PassIQ={a["Pass IQ"]} high for {apg:.1f}apg ({ast_pct:.1f}% ast%)')
    if a.get('Pass Vision', 0) >= 85 and ast_pct < 8:
        player_issues.append(f'PassVision={a["Pass Vision"]} high for ast%={ast_pct:.1f}%')

    # ── OFFENSIVE REBOUND ────────────────────────────────────────────────
    if a.get('Offensive Rebound', 0) >= 80 and is_guard:
        player_issues.append(f'ORB={a["Offensive Rebound"]} very high for guard')
    if a.get('Offensive Rebound', 0) <= 45 and is_big and orb_pct >= 8.0 and mpg >= 15:
        player_issues.append(f'ORB={a["Offensive Rebound"]} low for big (orb%={orb_pct:.1f}%)')

    # ── DEFENSIVE REBOUND ────────────────────────────────────────────────
    if a.get('Defensive Rebound', 0) >= 85 and is_guard:
        player_issues.append(f'DRB={a["Defensive Rebound"]} very high for guard')
    if a.get('Defensive Rebound', 0) <= 50 and is_big and drb_pct >= 20.0 and mpg >= 15:
        player_issues.append(f'DRB={a["Defensive Rebound"]} low for big (drb%={drb_pct:.1f}%)')

    # ── CLOSE SHOT ───────────────────────────────────────────────────────
    at_rim_pct  = fv(r, 'shooting_pct_less_than_5ft')
    if a.get('Close Shot', 0) >= 85 and at_rim_pct > 0 and at_rim_pct < 0.48 and ppg >= 8:
        player_issues.append(f'CloseShot={a["Close Shot"]} high for {at_rim_pct:.0%} at-rim%')

    if player_issues:
        issues.append((name, pos, ovr, int(mp), player_issues, attrs, r))

# Sort by minutes descending (most relevant players first)
issues.sort(key=lambda x: -x[3])

print(f'=== PLAYERS WITH ATTRIBUTE ISSUES ({len(issues)}) ===\n')
for name, pos, ovr, mp, p_issues, attrs, r in issues:
    print(f'{name:<30} {pos:<5} OVR={ovr:<3}  MP={mp}')
    for iss in p_issues:
        print(f'   ! {iss}')

# Print a separate stat-comparison table for the worst offenders
print('\n\n=== HIGH-MP PLAYERS WITH 3+ ISSUES ===')
multi = [(n,p,o,mp,pi,a,r) for n,p,o,mp,pi,a,r in issues if len(pi) >= 3 and mp >= 1000]
for name, pos, ovr, mp, p_issues, attrs, r in multi[:20]:
    print(f'\n{name} ({pos}, OVR={ovr}, MP={mp})')
    for iss in p_issues:
        print(f'  ! {iss}')
