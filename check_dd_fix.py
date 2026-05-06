import csv

with open('test_all_2025_26.csv', newline='', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

targets = ['Anthony Edwards', 'Cade Cunningham', 'Stephon Castle', 'Kon Knueppel',
           'Tyrese Maxey', 'Desmond Bane', 'Jaylen Brown', 'Tim Hardaway Jr.',
           'Amen Thompson', 'Jordan Goodwin', 'Dyson Daniels', 'Gary Payton II']

print(f"{'Player':<28} {'Pos':<8} {'OVR':<5} {'DD':<4} {'SD':<4} {'Spd':<4} {'ORB':<4}")
print('-'*60)
for r in rows:
    name = r.get('Player', '')
    if any(t.lower() in name.lower() for t in targets):
        pos = r.get('Pos', '')[:8]
        ovr = r.get('OVR', '')
        dd = r.get('Driving Dunk', '')
        sd = r.get('Standing Dunk', '')
        spd = r.get('Speed', '')
        orb = r.get('Offensive Rebound', '')
        print(f"{name:<28} {pos:<8} {ovr:<5} {dd:<4} {sd:<4} {spd:<4} {orb:<4}")
