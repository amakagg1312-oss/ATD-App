import csv, os, re, math, sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, r'D:\project\nba2k26_generator')

def _read_csv(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def _index_by_player_id(rows, pid_col='PLAYER_ID'):
    idx = {}
    for r in rows:
        pid = str(r.get(pid_col, '')).strip()
        if pid:
            idx[pid] = r
    return idx

sdir = r'D:\project\NBA Site data\2024-25'
base = Path(sdir)
files = sorted(base.glob('*.csv'))
print(f'Found {len(files)} CSV files')

import re as _re
season_tag = None
for f in files:
    m = _re.search(r'player_traditional_(\d{4}-\d{2})_regular_season\.csv', f.name)
    if m:
        season_tag = m.group(1)
        break
print(f'Season tag: {season_tag}')

def sf_name(name):
    return name.replace('SEASON', season_tag)

trad_path = base / sf_name('player_traditional_SEASON_regular_season.csv')
print(f'Trad path: {trad_path}')
print(f'Exists: {trad_path.exists()}')

trad_rows = _read_csv(trad_path)
trad_idx = _index_by_player_id(trad_rows)
print(f'Players indexed: {len(trad_idx)}')

for pid, row in trad_idx.items():
    pn = row.get('PLAYER_NAME', '')
    if 'lebron' in str(pn).lower():
        print(f'Found LeBron: {pn} pid={pid}')
        break

# Now test the full load_season_rows
from gen_player_fast import load_season_rows, load_all_rows

rows = load_season_rows(sdir)
print(f'load_season_rows returned {len(rows)} rows')

all_rows = load_all_rows(r'D:\project\NBA Site data')
print(f'load_all_rows returned {len(all_rows)} rows')

for r in all_rows:
    pn = r.get('player_name', '')
    if 'lebron' in str(pn).lower():
        print(f'Found in all_rows: {pn} season={r.get("season_label")}')
        break
