"""
Print stat vs attribute comparison for every notable player (1000+ min)
grouped by attribute category so we can manually spot mismatches.
"""
import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from nba2k26_generator.generator_cli import load_rows, compute_attributes, compute_tendencies

rows = load_rows('NBA Site data')
season_rows = [r for r in rows if str(r.get('season_label','  ')).startswith('2025')]

by_player = {}
for r in season_rows:
    name = r.get('player_name','')
    mp = float(r.get('totals_mp', 0) or 0)
    if name not in by_player or mp > float(by_player[name].get('totals_mp', 0) or 0):
        by_player[name] = r

def fv(r, k):
    return float(r.get(k, 0) or 0)

records = []
for r in by_player.values():
    mp = fv(r, 'totals_mp')
    if mp < 1000:
        continue
    try:
        t = compute_tendencies(r)
        result = compute_attributes(r, t, 'Player Roles', all_rows=rows,
                                    badges_txt_path='Badges/NBA 2K26 Badges.txt')
        a = result['attributes']
        ovr = result['ovr']
    except:
        continue

    records.append(dict(
        name=r.get('player_name',''),
        pos=r.get('position',''),
        mp=int(mp),
        ovr=ovr,
        # shooting
        fg3pa=fv(r,'per_game_x3pa_per_game'), fg3pct=fv(r,'per_game_x3p_percent'),
        fg2pct=fv(r,'per_game_x2p_percent'), ftpct=fv(r,'per_game_ft_percent'),
        ftpa=fv(r,'per_game_fta_per_game'),
        mid_fg=fv(r,'shooting_fga_2pt_mid_range'), mid_pct=fv(r,'shooting_pct_2pt_mid_range'),
        # playmaking
        apg=fv(r,'per_game_ast_per_game'), ast_pct=fv(r,'advanced_ast_percent'),
        tov_pct=fv(r,'advanced_tov_percent'), usg=fv(r,'advanced_usg_percent'),
        # rebounding
        orb_pct=fv(r,'advanced_orb_percent'), drb_pct=fv(r,'advanced_drb_percent'),
        rpg=fv(r,'per_game_trb_per_game'),
        # defense
        spg=fv(r,'per_game_stl_per_game'), stl_pct=fv(r,'advanced_stl_percent'),
        bpg=fv(r,'per_game_blk_per_game'), blk_pct=fv(r,'advanced_blk_percent'),
        # physical
        ppg=fv(r,'per_game_pts_per_game'), mpg=fv(r,'per_game_mp_per_game'),
        dunk_pct=fv(r,'shooting_percent_dunks_of_fga'),
        # attrs
        a3pt=a.get('Three-Point Shot',0), amid=a.get('Mid-Range Shot',0),
        aft=a.get('Free Throw',0), acs=a.get('Close Shot',0),
        adl=a.get('Driving Layup',0), add=a.get('Driving Dunk',0), asd=a.get('Standing Dunk',0),
        abh=a.get('Ball Handle',0), aswb=a.get('Speed with Ball',0),
        apa=a.get('Pass Accuracy',0), apiq=a.get('Pass IQ',0), apv=a.get('Pass Vision',0),
        aid=a.get('Interior Defense',0), apd=a.get('Perimeter Defense',0),
        astl=a.get('Steal',0), ablk=a.get('Block',0),
        aorb=a.get('Offensive Rebound',0), adrb=a.get('Defensive Rebound',0),
        aspd=a.get('Speed',0), aagl=a.get('Agility',0),
        astr=a.get('Strength',0), avert=a.get('Vertical',0),
        adf=a.get('Draw Foul',0), aph=a.get('Post Hook',0), apf=a.get('Post Fade',0),
        siq=a.get('Shot IQ',0),
        is_guard='PG' in r.get('position','').upper() or 'SG' in r.get('position','').upper(),
        is_big='PF' in r.get('position','').upper() or 'C' in r.get('position','').upper(),
    ))

records.sort(key=lambda x: -x['mp'])

# Print tables by attribute

def print_table(title, rows_sorted, cols, n=25):
    header = f"{'Player':<28} {'Pos':<4} {'OVR':>3} {'MP':>5}  " + "  ".join(f'{c:>8}' for c in cols)
    print(f"\n{'='*len(header)}")
    print(title)
    print(header)
    print('-'*len(header))
    for rec in rows_sorted[:n]:
        vals = "  ".join(f'{rec[c]:>8.1f}' if isinstance(rec.get(c,0), float) else f'{rec.get(c,0):>8}' for c in cols)
        print(f"{rec['name']:<28} {rec['pos']:<4} {rec['ovr']:>3} {rec['mp']:>5}  {vals}")

# ── SHOOTING ─────────────────────────────────────────────────────────────
# Top 3pt shooters by volume—check attribute
top_3pt_shooters = sorted([r for r in records if r['fg3pa'] >= 4.0], key=lambda x: -x['fg3pct'])
print_table('3PT SHOOTERS (4+ attempts) — sorted by percentage',
            top_3pt_shooters, ['fg3pa','fg3pct','a3pt'], n=20)

# Low-3pt attr but decent shooter
low_3pt_mismatch = sorted([r for r in records if r['a3pt'] < 70 and r['fg3pa'] >= 3.5 and r['fg3pct'] >= 0.37],
                          key=lambda x: -x['fg3pa'])
print_table('3PT MISMATCH: low attr (<70) but real shooter (4+@37%+)',
            low_3pt_mismatch, ['fg3pa','fg3pct','a3pt'], n=20)

# ── FREE THROW ───────────────────────────────────────────────────────────
ft_mismatch_low = sorted([r for r in records if r['aft'] < 65 and r['ftpct'] >= 0.78 and r['ftpa'] >= 2.0],
                         key=lambda x: -(x['ftpa']*x['ftpct']))
print_table('FT MISMATCH: low attr (<65) but good FT shooter (78%+ on 2+)',
            ft_mismatch_low, ['ftpa','ftpct','aft'], n=20)

ft_mismatch_high = sorted([r for r in records if r['aft'] >= 75 and r['ftpct'] <= 0.65 and r['ftpa'] >= 2.0],
                          key=lambda x: -x['ftpa'])
print_table('FT MISMATCH: high attr (75+) but poor FT shooter (65%- on 2+)',
            ft_mismatch_high, ['ftpa','ftpct','aft'], n=15)

# ── DRIVING DUNK ─────────────────────────────────────────────────────────
dd_high_nonbig = sorted([r for r in records if r['add'] >= 80 and not r['is_big'] and r['dunk_pct'] < 0.06],
                        key=lambda x: -x['add'])
print_table('DRIVING DUNK: 80+ attr for non-big with <6% dunks',
            dd_high_nonbig, ['dunk_pct','add','asd'], n=20)

dd_low_rim = sorted([r for r in records if r['asd'] <= 60 and r['is_big'] and r['dunk_pct'] >= 0.15],
                    key=lambda x: -(x['dunk_pct']))
print_table('STANDING/DRIVE DUNK: 60- for rim-running big (15%+ FGA dunks)',
            dd_low_rim, ['dunk_pct','add','asd'], n=15)

# ── BALL HANDLE ──────────────────────────────────────────────────────────
bh_high_big = sorted([r for r in records if r['abh'] >= 72 and r['is_big']], key=lambda x: -x['abh'])
print_table('BALL HANDLE: 72+ for big',
            bh_high_big, ['apg','ast_pct','usg','abh','aswb'], n=20)

bh_low_guard = sorted([r for r in records if r['abh'] < 60 and r['is_guard'] and r['mpg'] >= 20],
                      key=lambda x: x['abh'])
print_table('BALL HANDLE: <60 for guard 20+ mpg',
            bh_low_guard, ['apg','ast_pct','usg','abh','aswb'], n=20)

# ── PASSING ──────────────────────────────────────────────────────────────
pass_high_nonpg = sorted([r for r in records if r['apiq'] >= 80 and not r['is_guard'] and r['ast_pct'] < 12],
                         key=lambda x: -x['apiq'])
print_table('PASS IQ: 80+ for non-guard with ast%<12',
            pass_high_nonpg, ['apg','ast_pct','apiq','apa','apv'], n=20)

# ── BLOCK ──────────────────────────────────────────────────────────────
blk_high_guard = sorted([r for r in records if r['ablk'] >= 65 and r['is_guard'] and r['bpg'] < 0.5],
                        key=lambda x: -x['ablk'])
print_table('BLOCK: 65+ for guard with <0.5 bpg',
            blk_high_guard, ['bpg','blk_pct','ablk'], n=20)

# ── STEAL ────────────────────────────────────────────────────────────────
stl_high_low_rate = sorted([r for r in records if r['astl'] >= 85 and r['stl_pct'] < 1.5 and r['mp'] >= 1000],
                           key=lambda x: -x['astl'])
print_table('STEAL: 85+ but stl%<1.5',
            stl_high_low_rate, ['spg','stl_pct','astl','apd'], n=20)

# ── REBOUND ──────────────────────────────────────────────────────────────
orb_high_guard = sorted([r for r in records if r['aorb'] >= 70 and r['is_guard']], key=lambda x: -x['aorb'])
print_table('OFF REBOUND: 70+ for guard',
            orb_high_guard, ['rpg','orb_pct','aorb'], n=15)

drb_low_big = sorted([r for r in records if r['adrb'] <= 55 and r['is_big'] and r['drb_pct'] >= 16],
                     key=lambda x: x['adrb'])
print_table('DEF REBOUND: 55- for big with drb%>=16',
            drb_low_big, ['rpg','drb_pct','adrb'], n=15)

# ── SPEED ─────────────────────────────────────────────────────────────────
spd_high_big = sorted([r for r in records if r['aspd'] >= 82 and r['is_big']], key=lambda x: -x['aspd'])
print_table('SPEED: 82+ for big',
            spd_high_big, ['mpg','aspd','aagl'], n=15)

spd_low_guard = sorted([r for r in records if r['aspd'] <= 58 and r['is_guard'] and r['mpg'] >= 20],
                       key=lambda x: x['aspd'])
print_table('SPEED: 58- for guard 20+ mpg',
            spd_low_guard, ['mpg','aspd','aagl'], n=15)

# ── STRENGTH ─────────────────────────────────────────────────────────────
str_high_guard = sorted([r for r in records if r['astr'] >= 72 and r['is_guard']], key=lambda x: -x['astr'])
print_table('STRENGTH: 72+ for guard',
            str_high_guard, ['mpg','astr','avert'], n=15)

str_low_big = sorted([r for r in records if r['astr'] <= 45 and r['is_big'] and r['mpg'] >= 20],
                     key=lambda x: x['astr'])
print_table('STRENGTH: 45- for big 20+ mpg',
            str_low_big, ['mpg','rpg','astr'], n=15)
