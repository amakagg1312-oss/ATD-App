import struct

path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

# The play catalog has play names, but we need to find where play IDs are stored
# and how they're assigned to team playbooks.

# Let's look at the structure of the file more carefully
# The header had offsets to different sections
# Let's examine the sections that might contain play IDs or assignments

# First, let's find the section that contains play names and understand its structure
# Play names start around 0x3B5000 based on our earlier findings

# Let's look for patterns that could be play IDs or assignments
# Play IDs are likely stored as small integers referencing the catalog

# Search for arrays of small integers that could be play IDs
print('Searching for play ID arrays...\n')

# Look for sections with repeated small integer patterns
for offset in range(0x10000, 0x400000, 0x1000):
    # Check if this looks like an array of uint16 play IDs
    values = []
    for i in range(0, 64, 2):
        if offset + i + 2 <= len(data):
            val = struct.unpack_from('<H', data, offset + i)[0]
            values.append(val)
    
    # Check if values are in a reasonable play ID range
    if values and all(0 < v < 0x10000 for v in values[:20]):
        # Check if there's a pattern (repeated values, sequential, etc.)
        unique = len(set(values[:20]))
        if unique < 15:  # Some repetition suggests structured data
            print('Offset 0x{:X}: {}'.format(offset, values[:20]))

# Let's also look at the header structure more carefully
print('\n=== Header structure ===')
# First 4 bytes: 0x71 = 113 (header size?)
header_size = struct.unpack_from('<I', data, 0)[0]
print('Header size: {} (0x{:X})'.format(header_size, header_size))

# Read the header as a table
for i in range(0, min(header_size + 100, 500), 8):
    val = struct.unpack_from('<I', data, i)[0]
    next_val = struct.unpack_from('<I', data, i+4)[0] if i+4 < len(data) else 0
    if i % 24 == 0:
        print('  0x{:04X}: 0x{:08X} 0x{:08X}'.format(i, val, next_val))
