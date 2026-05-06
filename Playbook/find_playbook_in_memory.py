import struct

# Load snapshot1
with open('D:\\project\\Playbook\\snapshot1.bin', 'rb') as f:
    snap1 = f.read()

# The team table base is at offset 0xE9E7D0 in the snapshot
# (0x2A75A17D0 - 0x2A5CA17D0 = 0xE9E7D0)
team_base = 0xE9E7D0

print('Team base in snapshot: 0x{:X}'.format(team_base))

# Search for arrays of small integers near the team struct that could be play IDs
# Play IDs would likely be in the range 0-12506 (number of plays)

# Let's look at the team struct and nearby data
# First, let's dump the team struct area
start = team_base - 0x10000
end = team_base + 0x2000

print('\nSearching for play ID arrays near team struct (0x{:X} - 0x{:X})...'.format(start, end))

# Look for arrays of uint16 values in the play ID range
for offset in range(start, end, 2):
    # Check if next 20 bytes look like play IDs
    values = []
    valid = True
    for i in range(0, 40, 2):
        if offset + i + 2 > len(snap1):
            valid = False
            break
        val = struct.unpack_from('<H', snap1, offset + i)[0]
        if val > 12506:  # Max play ID
            valid = False
            break
        values.append(val)
    
    if valid and len(values) >= 10:
        # Check if values are diverse (not all same or sequential)
        unique = len(set(values))
        if unique > 3 and unique < 15:
            print('  Offset 0x{:X}: {}'.format(offset, values[:15]))

# Also search for the specific play name offsets we found
# If playbook assignments store offsets directly, they would be around 0x3B0000-0x430000
print('\nSearching for play name offsets (0x3B0000-0x430000)...')
for offset in range(start, end, 8):
    if offset + 8 > len(snap1):
        break
    val = struct.unpack_from('<Q', snap1, offset)[0]
    if 0x3B0000 <= val <= 0x430000:
        print('  Offset 0x{:X}: 0x{:X}'.format(offset, val))
