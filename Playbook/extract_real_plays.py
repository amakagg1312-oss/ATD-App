import re

path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

# Extract strings that look like actual play names
# Play names contain: letters, digits, spaces, and some punctuation like _ - .
# They should be at least 8 chars and mostly printable ASCII

play_names = set()
current_start = None
current_str = b''

for i, b in enumerate(data):
    if 32 <= b < 127:
        if current_start is None:
            current_start = i
        current_str += bytes([b])
    else:
        if len(current_str) >= 8:
            s = current_str.decode('ascii', errors='ignore')
            # Check if it looks like a play name:
            # - Contains at least 50% letters/spaces
            # - Has at least one space (play names have spaces)
            # - No weird control characters
            letter_count = sum(1 for c in s if c.isalpha() or c == ' ')
            if letter_count > len(s) * 0.5 and ' ' in s:
                play_names.add(s)
        current_start = None
        current_str = b''

# Filter out substrings
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
search_terms = ['MEM', 'ISO', 'FIST', 'QUICK', 'CHEST', '90', '14', 'GO', 'HORNS', 'DRIVE', 'WING', 'TOP', 'BIG', 'CORNER', 'GUARD', 'DELAY', 'SLICE', 'SWING', 'FLOW', 'EIGHTY', 'TRI', 'BOX', 'PHILLY', 'COMP', 'PACE', 'HAWK', 'JAZZ', 'POINT', '5OUT', '4OUT', '3OUT']

print('=== Plays by keyword ===')
for term in search_terms:
    matches = [n for n in filtered_names if term.lower() in n.lower()]
    if matches:
        print('\n{} ({} plays):'.format(term, len(matches)))
        for m in sorted(matches)[:30]:
            print('  {}'.format(m))
        if len(matches) > 30:
            print('  ... and {} more'.format(len(matches) - 30))
