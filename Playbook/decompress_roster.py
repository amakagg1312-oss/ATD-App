import struct
import zlib

data = open('RosterNBA0004', 'rb').read()
print(f"File size: {len(data)} bytes")

# Check header
magic = data[:4]
print(f"Header: {magic}")

# Look for decompressed data after EBNH
# Try different compression methods

# 1. Try zlib decompression from offset 8
print("\n1. Trying zlib from offset 8...")
try:
    dec = zlib.decompress(data[8:], -15)
    print(f"   Success! Size: {len(dec)}")
except Exception as e:
    print(f"   Failed: {e}")

# 2. Try raw deflate
print("\n2. Trying raw deflate from offset 8...")
try:
    dec = zlib.decompress(data[8:], -15)
    print(f"   Success! Size: {len(dec)}")
except Exception as e:
    print(f"   Failed: {e}")

# 3. Look for common compression signatures
print("\n3. Searching for compression signatures...")
# Common: 0x78 (zlib), 0x78 0x9c, 0x78 0x01, etc.
for sig in [b'\x78\x9c', b'\x78\x01', b'\x78\xda', b'\x08\x1d']:
    pos = data.find(sig)
    if pos > 0:
        print(f"   Found {sig.hex()} at 0x{pos:04X}")

# 4. Look for team name strings (uncompressed)
print("\n4. Looking for team names in file...")
for team in [b'PHI', b'LAL', b'BOS', b'GSW', b'MIA', b'DEN']:
    pos = data.find(team)
    if pos >= 0:
        print(f"   Found {team.decode()} at 0x{pos:04X}")

# 5. Try simple XOR scan (common in 2K games)
print("\n5. Looking for XOR patterns...")
# If data is XORed with constant, look for repeating patterns
# Try to find blocks by entropy

# 6. Check bytes around first team name position
print("\n6. Analysis around BOS at 0x1FD7F3...")
bpos = data.find(b'BOS')
if bpos > 0:
    # Read context
    for off in range(-32, 32, 8):
        ctx = data[bpos+off:bpos+off+16]
        print(f"   +{off:3d}: {ctx[:16].hex()} {ctx}")