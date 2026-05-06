import struct

# The roster file uses a custom encoding. Let's try to find where playbooks are stored
data = open('RosterNBA0004', 'rb').read()
file_size = len(data)

print("Looking for play index sequences (uint16 array)...")

# Simplified search - check at specific offsets first
search_offsets = [0x10000, 0x20000, 0x30000, 0x40000, 0x50000, 0x80000, 0x100000, 0x200000]
for start in search_offsets:
    if start + 100 > file_size:
        continue
    values = struct.unpack_from('<50H', data, start)
    valid = [v for v in values if 1 <= v <= 500]
    if len(valid) >= 20 and len(set(valid[:15])) >= 8:
        print(f"  Found at 0x{start:04X}: {valid[:15]}")

print("\nLooking for uint32...")
for start in search_offsets:
    if start + 100 > file_size:
        continue
    values = struct.unpack_from('<25I', data, start)
    valid = [v for v in values if 1 <= v <= 5000]
    if len(valid) >= 15 and len(set(valid[:10])) >= 5:
        print(f"  Found at 0x{start:04X}: {valid[:10]}")

print("\nDone")