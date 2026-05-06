import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import load_rows, as_float

rows = load_rows('NBA Site data')
for r in rows:
    if 'Kessler' in r.get('player_name','') and 'Walker' in r.get('player_name',''):
        # key fields
        three_pa = as_float(r, 'per_game_x3pa_per_game')
        three_pct = as_float(r, 'per_game_x3p_percent')
        three_pct36 = as_float(r, 'per_36_x3p_percent')
        three_pa36 = as_float(r, 'per_36_x3pa_per_36_min')
        ft_pct = as_float(r, 'per_game_ft_percent')
        ft_pct36 = as_float(r, 'per_36_ft_percent')
        assisted3 = as_float(r, 'shooting_percent_assisted_x3p_fg')
        trk_cs_3pct = as_float(r, 'tracking_catch_shoot_fg3_pct')
        trk_cs_3pa = as_float(r, 'tracking_catch_shoot_fg3a_pg')
        catch_shoot_signal = as_float(r, 'tracking_catch_shoot_fg3_pct')
        
        print(f"Walker Kessler 3PT trace:")
        print(f"  per_game_x3pa_per_game = {three_pa}")
        print(f"  per_game_x3p_percent = {three_pct}")
        print(f"  per_36_x3p_percent = {three_pct36}")
        print(f"  per_36_x3pa_per_36_min = {three_pa36}")
        print(f"  ft_pct (per_game) = {ft_pct}")
        print(f"  assisted3 = {assisted3}")
        print(f"  trk_catch_shoot_fg3_pct = {trk_cs_3pct}")
        print(f"  trk_catch_shoot_fg3a_pg = {trk_cs_3pa}")
        
        # Print other key blended fields
        print("\nAll 3pt-related fields in row:")
        for k, v in sorted(r.items()):
            if '3p' in k.lower() or 'three' in k.lower() or 'catch' in k.lower():
                print(f"  {k} = {v}")
        break
