import struct

# Analyze roster more deeply
data = open('RosterNBA0004', 'rb').read()
size = len(data)

# Try to find where playbooks are stored by looking for patterns
# Common structures: count (2 bytes) + indices (2 bytes each)

print('Searching for playbook blocks (uint16 arrays)...')
# Teams have ~5-25 plays typically
# Look for sequences: count + indices where count * 2 + 2 matches nearby

for start in range(0, min(size, 0x200000), 4):
    count = struct.unpack_from('<H', data, start)[0]
    if 1 <= count <= 30:  # Reasonable playbook size
        # Check next 'count' values also in range
        if start + 2 + count*2 <= size:
            indices = struct.unpack_from(f'<{count}H', data, start + 2)
            # Check if all valid play IDs (1-13000)
            if all(1 <= idx <= 13000 for idx in indices):
                # Check distinct (not duplicate-heavy)
                if len(set(indices)) >= count // 2:
                    print(f'Found at 0x{start:04X}: count={count}, first 10: {list(indices[:10])}')
                    break

# Try uint32 arrays
print('\nSearching for uint32 playbook blocks...')
for start in range(0, min(size, 0x200000), 4):
    count = struct.unpack_from('<I', data, start)[0]
    if 1 <= count <= 30:
        if start + 4 + count*4 <= size:
            indices = struct.unpack_from(f'<{count}I', data, start + 4)
            if all(1 <= idx <= 13000 for idx in indices):
                if len(set(indices)) >= count // 2:
                    print(f'Found at 0x{start:04X}: count={count}, first 10: {list(indices[:10])}')
                    break