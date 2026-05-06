import sys
sys.path.insert(0, r'd:\project\nba2k26_generator')
from generator_cli import load_rows, as_float

rows = load_rows(r'D:\project\NBA Site data')
for row in rows:
    name = str(row.get('player_name', ''))
    if 'Kawhi' in name:
        mins_keys = [k for k in row.keys() if 'min' in k.lower() or 'gp' in k.lower()]
        stl_keys = [k for k in row.keys() if 'stl' in k.lower()]
        pos_keys = [k for k in row.keys() if 'pos' in k.lower() or 'POSITION' in k]
        print("=== KAWHI - field samples ===")
        for k in sorted(mins_keys)[:8]:
            print(f'  {k} = {row.get(k)}')
        for k in sorted(stl_keys)[:6]:
            print(f'  {k} = {row.get(k)}')
        for k in sorted(pos_keys)[:6]:
            print(f'  {k} = {row.get(k)}')
        # Check all season data
        all_mins = as_float(row, 'minutes')
        all_mins2 = as_float(row, 'min')
        all_mins3 = as_float(row, 'gp')
        print(f'  as_float(minutes)={all_mins}  as_float(min)={all_mins2}  as_float(gp)={all_mins3}')
        break

# Also check Luka
for row in rows:
    name = str(row.get('player_name', ''))
    if 'Don' in name and 'i' in name and 'c' in name and 'Luka' in name:
        stop_d = as_float(row, 'defense_dash_overall_stop_delta', 0)
        stl_pct = as_float(row, 'stl_pct', 0)
        dws = as_float(row, 'dws', 0)
        mins = as_float(row, 'minutes', 0)
        peak = as_float(row, 'defense_peak_signal', 0)
        print(f'Luka: mins={mins} stl%={stl_pct:.2f} dws={dws:.1f} stop_d={stop_d:.4f} peak={peak:.1f}')
        break
