with open('D:\\project\\Playbook\\game files\\all_play_names.txt', 'r') as f:
    lines = f.readlines()

print('Total plays in catalog: {}'.format(len(lines)))

# Group by category
categories = {}
for line in lines:
    parts = line.strip().split(': ', 1)
    if len(parts) == 2:
        offset, name = parts
        name = name.strip("'")
        first_word = name.split()[0] if name.split() else name
        if first_word not in categories:
            categories[first_word] = []
        categories[first_word].append(name)

print('\nPlay categories (top 30):')
for cat in sorted(categories.keys(), key=lambda x: -len(categories[x]))[:30]:
    print('  {}: {} plays'.format(cat, len(categories[cat])))
