import struct

path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

# Play names are stored as UTF-16LE, separated by 00 00
# Find all UTF-16LE strings
print('Extracting play names from playdata...\n')

play_names = []
i = 0
while i < len(data) - 1:
    # Look for start of UTF-16LE string (char followed by 00)
    if data[i] != 0 and data[i+1] == 0:
        # Try to decode as UTF-16LE
        j = i
        while j + 1 < len(data) and data[j] != 0 and data[j+1] == 0:
            j += 2
        
        if j - i >= 16:  # At least 8 chars
            try:
                s = data[i:j].decode('utf-16-le', errors='ignore')
                # Check if it looks like a play name
                if len(s) >= 8 and any(c.isalpha() for c in s):
                    # Filter: must contain letters and spaces/numbers
                    letter_count = sum(1 for c in s if c.isalpha() or c == ' ')
                    if letter_count > len(s) * 0.5:
                        play_names.append((i, s))
                        i = j + 2  # Skip past this string
                        continue
            except:
                pass
    i += 1

print('Found {} play names\n'.format(len(play_names)))

# Search for the specific plays the user mentioned
search_terms = ['MEM', 'ISO', 'FIST', 'QUICK', 'CHEST', '90', '14', 'GO', 'HORNS', 'DRIVE', 'WING', 'TOP', 'BIG', 'CORNER', 'GUARD', 'DELAY', 'SLICE', 'SWING', 'FLOW', 'EIGHTY', 'TRI', 'BOX', 'PHILLY', 'COMP', 'PACE', 'HAWK', 'JAZZ', 'POINT', '5OUT', '4OUT', '3OUT', 'ISOLATION']

print('=== Plays by keyword ===')
for term in search_terms:
    matches = [(offset, name) for offset, name in play_names if term.lower() in name.lower()]
    if matches:
        print('\n{} ({} plays):'.format(term, len(matches)))
        for offset, name in sorted(matches, key=lambda x: x[1])[:30]:
            print('  0x{:X}: {}'.format(offset, name))
        if len(matches) > 30:
            print('  ... and {} more'.format(len(matches) - 30))

# Save all play names to a file
print('\n\n=== All play names ===')
with open('D:\\project\\Playbook\\game files\\all_play_names.txt', 'w') as f:
    for offset, name in sorted(play_names, key=lambda x: x[1]):
        f.write('0x{:X}: {}\n'.format(offset, name))
        print('  0x{:X}: {}'.format(offset, name))

print('\nSaved {} play names to all_play_names.txt'.format(len(play_names)))
