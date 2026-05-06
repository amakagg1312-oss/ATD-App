# Find Lakers play indices in catalog
catalog = {}
with open('game files/all_play_names.txt', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if ': ' in line:
            name = line.split(': ', 1)[1].strip(" '")
            catalog[name] = i

# Search for Lakers plays
lal_plays = [
    'FIST 21 CHASE', 'FIST 21 NASH', 'FIST 21 CHASE 2', 'FIST 21 POP',
    'FIST DELAY 2', 'FIST 13 DOWN', 'FIST 15 SPREAD DOWN', 'FIST 25 GIVE',
    'FIST 25 GIVE DOWN', 'FIST 4 CNR', 'LAL FIST 15 CURL', 'FIST 41 HORNS',
    'FIST 41 SPREAD GET', 'LAL FIST 15 CURL DRAG', 'LAL FIST 15 GIVE DBL',
    'LAL FIST 24 RAM'
]

print('Looking for Lakers plays in catalog:')
for play in lal_plays:
    found = None
    # Try exact match first
    for name, idx in catalog.items():
        if name.upper() == play.upper():
            found = idx
            break
    # Try partial match
    if not found:
        for name, idx in catalog.items():
            if play.upper() in name.upper() or name.upper() in play.upper():
                found = idx
                break
    if found:
        print(f'  {play} -> index {found}')
    else:
        print(f'  {play} -> NOT FOUND')
