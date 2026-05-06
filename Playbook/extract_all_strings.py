import struct

path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

# Let's try to find the play catalog by looking for patterns
# that might indicate play names or IDs

# First, let's look at the entire file for any readable text
# by extracting all sequences of printable ASCII characters
print('Extracting all readable ASCII sequences (min 8 chars)...')
strings = []
current_start = None
current_str = b''

for i, b in enumerate(data):
    if 32 <= b < 127:
        if current_start is None:
            current_start = i
        current_str += bytes([b])
    else:
        if len(current_str) >= 8:
            strings.append((current_start, current_str.decode('ascii')))
        current_start = None
        current_str = b''

print('Found {} strings >= 8 chars'.format(len(strings)))

# Show all strings
for offset, s in strings:
    print('  0x{:X}: "{}"'.format(offset, s))

# Also try UTF-16LE
print('\nSearching for UTF-16LE strings (min 6 chars)...')
for i in range(0, len(data) - 12, 2):
    # Check if it looks like UTF-16LE (alternating null bytes)
    if data[i+1] == 0 and data[i+3] == 0 and data[i+5] == 0:
        # Try to decode
        j = i
        while j + 1 < len(data) and data[j] != 0 and data[j+1] == 0:
            j += 2
        if j - i >= 12:  # At least 6 chars
            try:
                s = data[i:j].decode('utf-16-le', errors='ignore')
                if len(s) >= 6 and all(32 <= ord(c) < 127 for c in s):
                    print('  0x{:X}: "{}"'.format(i, s))
            except:
                pass
