import json
from collections import Counter

with open('D:\\project\\Playbook\\extracted_playbook.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count how many arrays each play appears in
play_counts = Counter()
play_offsets = {}

for arr, plays in data['arrays'].items():
    for play in plays:
        name = play['play_name']
        play_counts[name] += 1
        if name not in play_offsets:
            play_offsets[name] = play['byte_offset']

# Sort by frequency
sorted_plays = play_counts.most_common()

print('=== Plays sorted by frequency (most common = likely in actual playbook) ===\n')
print('Play appears in N arrays -> likely in the 60-play roster\n')

# Show all plays with their frequency
for name, count in sorted_plays:
    marker = '***' if count > 50 else ('**' if count > 20 else ('*' if count > 5 else ''))
    print('[{:3d}] {} {}'.format(count, name, marker))

print('\n\nTotal unique plays found: {}'.format(len(sorted_plays)))

# Plays that appear in >50 arrays are likely the core 60
high_freq = [(name, count) for name, count in sorted_plays if count > 50]
print('\nPlays appearing in >50 arrays (likely the core playbook):')
for name, count in high_freq:
    print('  - {}'.format(name))

print('\nTotal: {}'.format(len(high_freq)))
