import json

with open('D:\\project\\Playbook\\extracted_playbook.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Deduplicate plays
unique_plays = {}
for arr, plays in data['arrays'].items():
    for play in plays:
        name = play['play_name']
        if name not in unique_plays:
            unique_plays[name] = {
                'byte_offset': play['byte_offset'],
                'arrays': []
            }
        unique_plays[name]['arrays'].append(arr)

# Sort by play name
sorted_plays = sorted(unique_plays.items(), key=lambda x: x[0])

print('Total unique plays: {}'.format(len(sorted_plays)))

# Group by category
categories = {}
for name, info in sorted_plays:
    if name.startswith("'"):
        cat = name[:4]
    elif name.startswith(('HS_', 'INF', 'SST', 'PXM', 'CSU', 'ATD', 'LVA', 'MNL', 'NYL')):
        cat = name.split()[0]
    elif name.startswith('W '):
        cat = 'W'
    elif 'QUICK' in name:
        cat = 'QUICK'
    elif 'FIST' in name:
        cat = 'FIST'
    elif 'PUNCH' in name:
        cat = 'PUNCH'
    elif 'ISO' in name:
        cat = 'ISO'
    elif 'GIVE' in name:
        cat = 'GIVE'
    elif 'CUT' in name:
        cat = 'CUT'
    else:
        cat = 'OTHER'
    
    if cat not in categories:
        categories[cat] = []
    categories[cat].append((name, info))

# Print summary
print('\n=== Playbook Summary ===')
for cat in sorted(categories.keys()):
    plays = categories[cat]
    print('\n{}: {} plays'.format(cat, len(plays)))
    for name, info in plays[:10]:
        print('  - {}'.format(name))
    if len(plays) > 10:
        print('  ... and {} more'.format(len(plays) - 10))

# Save deduplicated version
output = {
    'total_unique_plays': len(sorted_plays),
    'categories': {cat: [{'play_name': name, 'byte_offset': info['byte_offset']} for name, info in plays] for cat, plays in categories.items()}
}

with open('D:\\project\\Playbook\\playbook_deduplicated.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print('\n\nSaved deduplicated playbook to D:\\project\\Playbook\\playbook_deduplicated.json')
