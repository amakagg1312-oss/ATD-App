import sys; sys.path.insert(0,'.'); sys.stdout.reconfigure(encoding='utf-8')
from nba2k26_generator.nba_site_normalization import load_nba_site_rows
rows = load_nba_site_rows('NBA Site data')
for r in rows:
    if 'giannis' in r.get('player_name','').lower():
        ds = r.get('shooting_percent_dunks_of_fga')
        dc = r.get('shooting_num_of_dunks')
        print(f'dunks_share raw={ds} type={type(ds)}')
        print(f'dunk_count raw={dc} type={type(dc)}')
        break
cnt = sum(1 for r in rows if float(r.get('shooting_percent_dunks_of_fga',0) or 0) > 0.001)
print(f'Players with dunks_share > 0.001: {cnt}/{len(rows)}')
top = sorted(rows, key=lambda r: float(r.get('shooting_percent_dunks_of_fga',0) or 0), reverse=True)[:10]
for r in top:
    n = r['player_name']
    ds = r.get('shooting_percent_dunks_of_fga')
    dc = r.get('shooting_num_of_dunks')
    print(f'  {n}: share={ds} dunks={dc}')

# check Doncic
for r in rows:
    if 'luka' in r.get('player_name','').lower():
        ds = r.get('shooting_percent_dunks_of_fga')
        dc = r.get('shooting_num_of_dunks')
        spp = r.get('scoring_pct_pts_paint')
        drv = r.get('tracking_drives_per_game')
        print(f'Doncic: dunks_share={ds} dunk_count={dc} pts_paint={spp} drives_pg={drv}')
        break
