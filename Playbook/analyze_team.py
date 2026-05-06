import struct

# Let's analyze the roster by looking at TEAM structures
# Teams are typically in a known order - find the first table offset

data = open('RosterNBA0004', 'rb').read()

# Try different interpretations of the header
print("Analyzing header (first 32 bytes):")
for i in range(0, 32, 4):
    val = struct.unpack_from('<I', data, i)[0]
    if 0 < val < 0x100000:
        print(f"  +{i:2d} (0x{i:02X}): {val} (0x{val:04X})")

# Look for team index table - common at 0x100 or similar
print("\nSearching for team table at common offsets...")
for base in [0x100, 0x200, 0x300, 0x400, 0x500, 0x1000]:
    # Expect 30 teams * some offset
    values = struct.unpack_from('<30I', data, base)
    valid_offsets = [v for v in values if 0 < v < len(data)]
    if len(valid_offsets) > 20:
        print(f"  Possible team table at 0x{base:04X}: {len(valid_offsets)} valid offsets")
        print(f"    First few: {valid_offsets[:5]}")

# Look for team ID sequence (1, 2, 3, 4...)
print("\nSearching for team ID sequence...")
for base in [0x100, 0x200, 0x300, 0x400, 0x500, 0x1000]:
    values = struct.unpack_from('<30I', data, base)
    # Check for sequential team IDs
    if values[0] == 1 and values[1] == 2:
        print(f"  Found team IDs at 0x{base:04X}: {list(values[:10])}")

# Try to read team records directly
# If team table exists, find team data blocks
print("\n--- Looking for team records ---")
# Teams start at some offset - try 0x10000
search_base = 0x10000
for offset in range(search_base, min(len(data), 0x20000), 0x100):
    # Look for team name near an offset
    ctx = data[offset:offset+4]
    if ctx == b'BOS' or ctx == b'MIA':
        print(f"  Team at 0x{offset:04X}: {ctx}")