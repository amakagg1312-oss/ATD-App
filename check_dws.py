import csv
f = open('NBA Site data/player_defense_2025-26_regular_season.csv', encoding='utf-8')
r = csv.DictReader(f)
for row in r:
    n = row.get('PLAYER_NAME', '')
    if any(x in n.lower() for x in ['reaves', 'gilgeous', 'caruso', 'thybulle']):
        ws = row.get('DEF_WS', '?')
        wr = row.get('DEF_WS_RAW', '?')
        print(f'{n}: DEF_WS={ws} DEF_WS_RAW={wr}')
