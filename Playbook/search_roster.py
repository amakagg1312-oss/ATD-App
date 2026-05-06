import struct
import os

# Try to find 76ers team data in roster
data = open('RosterNBA0004', 'rb').read()

# Look for PHI in file
print("Looking for PHI team...")
pos = data.find(b'PHI')
if pos >= 0:
    print(f"Found PHI at 0x{pos:04X}")
else:
    print("PHI not found - searching for partial match...")
    pos = data.find(b'\x50\x48\x49')  # PHI encoded
    if pos >= 0:
        print(f"Found PHI at 0x{pos:04X}")

# Look for patterns near team areas
# Try 76ers team = team ID around 0-30
print("\nSearching for small integers near team names...")

# Find all team abbreviations
teams = [b'PHI', b'LAL', b'BOS', b'GSW', b'MIA', b'DEN', b'CHI', b'DAL']
for team in teams:
    pos = data.find(team)
    if pos >= 0:
        print(f"{team.decode()} at 0x{pos:04X}")
        # Show 32 bytes around it
        start = max(0, pos - 32)
        end = min(len(data), pos + 32)
        ctx = data[start:end]
        print(f"  Context: {ctx[:24].hex()}")

# Try to find play catalog reference
# Look for known play index 14 (85 PHI 14 CUT)
print("\nSearching for play index values...")
# These are line numbers from all_play_names.txt
for play_idx in [14, 25, 26, 27, 2840, 2841]:
    # Search as byte
    b = play_idx.to_bytes(2, 'little')
    pos = data.find(b)
    if pos >= 0:
        print(f"  Index {play_idx} at 0x{pos:04X}")

# Try searching for known play from PHI playbook
# The play "85 PHI 14 CUT" is line 14 in catalog
print("\nSearching for catalog string locations...")
# Look for string table markers
for sig in [b'\x00\x00\x00', b'\xff\xff\xff']:
    pos = data.find(sig, 0x10000)
    if pos >= 0 and pos < 0x200000:
        print(f"  Found {sig.hex()} at 0x{pos:04X}")

# Print overall file info
print(f"\nFile: {len(data)} bytes")
print(f"Header: {data[:10].hex()}")