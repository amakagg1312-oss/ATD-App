import struct

# Load both snapshots
with open('D:\\project\\Playbook\\snapshot1.bin', 'rb') as f:
    snap1 = f.read()
with open('D:\\project\\Playbook\\snapshot2.bin', 'rb') as f:
    snap2 = f.read()

# The playbook changed between snapshots, so the difference should be in the playbook data
# We already found 3 changed regions, let's examine them more carefully

# Changed regions from earlier diff:
# 1. 0xEADC38 - 0xEADC3F (8 bytes) - pointer/hash
# 2. 0xEADF50 - 0xEADF6F (32 bytes) - floats/stats
# 3. 0xEAE344 - 0xEAE579 (566 bytes) - repeating uint16 pattern

# Let's look at region 3 more carefully - it had a repeating pattern
# that changed from 0x7100 to 0x74A2

region_start = 0xEAE344
region_end = 0xEAE579

print('=== Changed region 3 (0x{:X} - 0x{:X}) ==='.format(region_start, region_end))

# Read the data
data1 = snap1[region_start:region_end+1]
data2 = snap2[region_start:region_end+1]

# Interpret as uint16 array
print('\nAs uint16 array (before -> after):')
for i in range(0, min(len(data1), 128), 2):
    v1 = struct.unpack_from('<H', data1, i)[0]
    v2 = struct.unpack_from('<H', data2, i)[0]
    if v1 != v2:
        print('  Offset +0x{:04X}: 0x{:04X} ({}) -> 0x{:04X} ({})'.format(i, v1, v1, v2, v2))

# This looks like it could be animation/rendering data, not playbook data
# Let's search for playbook data in a different way

# Search for the specific play name strings in memory
# The play names are stored as UTF-16LE in the game files
# Let's search for "MEM ISO 3 GO" in UTF-16LE

search_strings = [
    b'M\x00E\x00M\x00 \x00I\x00S\x00O\x00 \x003\x00 \x00G\x00O\x00',
    b'Q\x00U\x00I\x00C\x00K\x00 \x001\x00 \x00C\x00H\x00E\x00S\x00T\x00',
    b'9\x000\x00 \x00F\x00I\x00S\x00T\x00 \x001\x004\x00 \x00Q\x00U\x00I\x00C\x00K\x00 \x002\x00',
]

print('\n=== Searching for play name strings in memory ===')
for search in search_strings:
    idx = snap1.find(search)
    if idx != -1:
        print('Found at offset 0x{:X}'.format(idx))
    else:
        print('Not found: {}'.format(search[:20]))

# Let's also search for the play names as ASCII (without null bytes)
search_ascii = [
    b'MEM ISO 3 GO',
    b'QUICK 1 CHEST',
    b'90 FIST 14 QUICK 2',
]

print('\n=== Searching for ASCII play names ===')
for search in search_ascii:
    idx = snap1.find(search)
    if idx != -1:
        print('Found at offset 0x{:X}'.format(idx))
    else:
        print('Not found: {}'.format(search))
