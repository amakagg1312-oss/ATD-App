import struct

def find_play_arrays(data):
    """Search for arrays of consecutive small integers that could be play IDs."""
    # Search for uint16 arrays in range 1-500
    print("Looking for uint16 arrays (1-500)...")
    data_len = len(data)
    for start in range(0, data_len, 4):
        if start + 40 > data_len:
            break
        # Try reading as uint16
        values = struct.unpack_from('<20H', data, start)
        # Check if all values are in valid range
        if all(1 <= v <= 500 for v in values):
            if len(set(values)) > 5:  # At least 5 unique values
                print(f"  0x{start:04X}: {list(values)[:10]}")
                break
    
# Search for uint32 arrays in range 1-13000
    print("\nLooking for uint32 arrays (1-13000)...")
    data_len = len(data)
    for start in range(0, data_len, 4):
        if start + 40 > data_len:
            break
        values = struct.unpack_from('<10I', data, start)
        if all(1 <= v <= 13000 for v in values):
            if len(set(values)) > 5:
                print(f"  0x{start:04X}: {list(values)[:10]}")
                break

def find_uncompressed_regions(data):
    """Look for uncompressed data sections (not all zeros or uniform)."""
    print("\nLooking for uncompressed regions...")
    
    # Look for repeated signatures like team names
    for team in [b'PHI', b'LAL', b'BOS', b'GSW']:
        pos = data.find(team)
        if pos >= 0:
            print(f"  Found {team.decode()} at 0x{pos:04X}")
    
    # Look for play name patterns (ISO, PUNCH, etc.)
    for term in [b'ISO', b'PUNCH', b'CUT']:
        pos = data.find(term)
        if pos >= 0:
            # Get context
            start = max(0, pos - 10)
            end = min(len(data), pos + 20)
            ctx = data[start:end]
            print(f"  Found {term.decode()} at 0x{pos:04X}: {ctx[:20]}")

# Load file
data = open('RosterNBA0004', 'rb').read()
print(f"File size: {len(data)} bytes")
print(f"First 100 bytes: {data[:100][:50]}")

# Check header
magic = data[:4]
print(f"\nHeader: {magic}")
if magic == b'EBNH':
    # Try to find compressed data boundary
    # Look for where actual data starts after header
    print("\nSearching for data after EBNH header...")
    
    # Common compression: first few bytes after header are compressed
    # Try to find uncompressed blocks
    find_uncompressed_regions(data)

# Try different offsets
print("\n--- Trying offset 0x100 ---")
data2 = open('RosterNBA0004', 'rb').read(0x10000)
find_play_arrays(data2)

print("\n--- Trying offset 0x50000 ---")
data3 = open('RosterNBA0004', 'rb').read()[0x50000:0x50100]
find_play_arrays(data3)