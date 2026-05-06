import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nba2k26_generator'))
from generator_cli import load_rows, as_float

rows = load_rows(r'D:\project\NBA Site data')
targets = ['Brunson', 'Giddey', 'Haliburton', 'Gobert', 'Fox', 'Finney-Smith',
           'Antetokounmpo', 'Harris', 'Durant', 'Booker', 'Gilgeous-Alexander',
           'Williamson', 'Anunoby', 'Caruso', 'Maxey', 'Lopez']

print(f"{'Name':30} {'pos':3} {'spd':6} {'spd_off':7} {'drives':7} {'stl':5} {'blk':5} {'3PA':5} {'3pct':6}")
for row in rows:
    name = str(row.get('player_name', ''))
    if any(t in name for t in targets):
        speed = as_float(row, 'tracking_avg_speed')
        speed_off = as_float(row, 'tracking_avg_speed_off')
        drives = as_float(row, 'tracking_drives_pg', 0)
        stl = as_float(row, 'stl_pg', 0)
        blk = as_float(row, 'blk_pg', 0)
        pos = str(row.get('POSITION', ''))
        threepa = as_float(row, 'three_pa_pg', 0)
        threepct = as_float(row, 'three_pt_pct', 0)
        rim_freq = as_float(row, 'shooting_percent_fga_lt6ft', 0)
        dist_miles = as_float(row, 'tracking_dist_miles_pg', 0)
        print(f'{name:30} {pos:3} {speed:6.2f} {speed_off:7.2f} {drives:7.1f} {stl:5.2f} {blk:5.2f} {threepa:5.1f} {threepct:6.3f} rim={rim_freq:.2f} dist={dist_miles:.2f}')
