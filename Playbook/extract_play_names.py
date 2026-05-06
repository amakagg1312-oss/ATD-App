import struct

path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

# Extract all unique play names by finding the longest string at each 2-byte boundary
# The pattern shows strings starting at even offsets, each overlapping the next
print('Extracting unique play names from playdata...\n')

# Find the region with play names (around 0x42F000-0x431000 based on output)
# Let's search the entire file for play name patterns
play_names = set()

# Find all ASCII strings of length >= 8
current_start = None
current_str = b''

for i, b in enumerate(data):
    if 32 <= b < 127:
        if current_start is None:
            current_start = i
        current_str += bytes([b])
    else:
        if len(current_str) >= 8:
            s = current_str.decode('ascii')
            # Only keep strings that look like play names (contain spaces, numbers, or known play keywords)
            if any(c.isdigit() for c in s) or ' ' in s:
                play_names.add(s)
        current_start = None
        current_str = b''

# Filter to only keep the "root" play names (longest versions)
# Remove substrings of other names
filtered_names = set()
for name in sorted(play_names):
    is_substring = False
    for other in play_names:
        if name != other and name in other:
            is_substring = True
            break
    if not is_substring:
        filtered_names.add(name)

print('Found {} unique play names\n'.format(len(filtered_names)))

# Search for the specific plays the user mentioned
search_terms = ['MEM ISO', 'FIST', 'QUICK', 'CHEST', 'ISO', '90', '14', '1 CHEST', 'GO']

print('=== Searching for user-mentioned plays ===')
for term in search_terms:
    matches = [n for n in filtered_names if term.lower() in n.lower()]
    if matches:
        print('\nPlays containing "{}":'.format(term))
        for m in sorted(matches)[:20]:
            print('  {}'.format(m))
    else:
        print('\nNo plays containing "{}"'.format(term))

# Show all plays grouped by category
print('\n\n=== All plays by category ===')
categories = {}
for name in sorted(filtered_names):
    # Use first word as category
    first_word = name.split()[0] if name.split() else name
    if first_word not in categories:
        categories[first_word] = []
    categories[first_word].append(name)

for cat in sorted(categories.keys()):
    plays = categories[cat]
    print('\n{} ({} plays):'.format(cat, len(plays)))
    for p in plays[:15]:
        print('  {}'.format(p))
    if len(plays) > 15:
        print('  ... and {} more'.format(len(plays) - 15))
