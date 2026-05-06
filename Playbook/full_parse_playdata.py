import struct

path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

print('File size: {} bytes'.format(len(data)))

# Extract ALL offsets from the header (8-byte pattern: [4 bytes offset][4 bytes zeros])
offsets = []
for i in range(0, min(1000, len(data)-7), 8):
    val = struct.unpack_from('<I', data, i)[0]
    zeros = struct.unpack_from('<I', data, i+4)[0]
    if zeros == 0 and val > 0x100 and val < len(data):
        offsets.append((i, val))

print('Found {} offsets in first 1000 bytes:'.format(len(offsets)))
for pos, off in offsets:
    print('  Header pos 0x{:04X} -> data offset 0x{:X}'.format(pos, off))

# Now search for ALL ASCII strings in the file
print('\nSearching for ASCII strings (min 5 chars)...')
strings = []
current_start = None
current_str = b''

for i, b in enumerate(data):
    if 32 <= b < 127:
        if current_start is None:
            current_start = i
        current_str += bytes([b])
    else:
        if len(current_str) >= 5:
            strings.append((current_start, current_str.decode('ascii')))
        current_start = None
        current_str = b''

print('Found {} strings'.format(len(strings)))

# Show strings that might be play-related
play_keywords = ['iso', 'fist', 'quick', 'chest', 'pick', 'horn', 'flex', 'motion', 'pistol', 'triangle', 'princeton', 'alley', 'drive', 'post', 'screen', 'cut', 'spot', 'corner', 'offense', 'defense', 'play', 'set', 'go', 'mem']

print('\nPlay-related strings:')
for offset, s in strings:
    s_lower = s.lower()
    if any(kw in s_lower for kw in play_keywords):
        print('  0x{:X}: "{}"'.format(offset, s))

# Also show first 50 strings to understand the structure
print('\nFirst 50 strings:')
for offset, s in strings[:50]:
    print('  0x{:X}: "{}"'.format(offset, s))
