import sys; sys.path.insert(0,'.'); sys.stdout.reconfigure(encoding='utf-8')
from nba2k26_generator.nba_site_normalization import load_nba_site_rows
from nba2k26_generator.generator_cli import as_float
rows = load_nba_site_rows('NBA Site data')
checks = ['Edwards','Morant','Reaves','Gilgeous','LaVine','Fox','Brunson','Luka','Giannis','Wemban','Davis']
for name in checks:
    for r in rows:
        if name.lower() in r.get('player_name','').lower():
            ds = as_float(r,'shooting_percent_dunks_of_fga')
            dc = as_float(r,'shooting_num_of_dunks')
            pos = r.get('position','')
            print(f'  {r["player_name"]} ({pos}): share={ds:.3f} count={dc:.1f}')
            break
