import struct

dump_start = 0x2A5CA17D0
team_base = 0x2A75A17D0

regions = [
    (0xEADC38, 0xEADC3F),
    (0xEADF50, 0xEADF6F),
    (0xEAE344, 0xEAE579),
]

print('=== Changed Regions Analysis ===\n')

for start, end in regions:
    mem_addr = dump_start + start
    offset_from_team = mem_addr - team_base
    size = end - start + 1
    
    print('File offset: 0x{:X} - 0x{:X}'.format(start, end))
    print('Memory address: 0x{:X} - 0x{:X}'.format(mem_addr, dump_start + end))
    print('Offset from team table: 0x{:X} ({} bytes before team)'.format(offset_from_team, -offset_from_team))
    print('Size: {} bytes'.format(size))
    
    # Read the changed data
    with open('D:\\project\\Playbook\\snapshot1.bin', 'rb') as f:
        f.seek(start)
        before = f.read(size + 16)
    with open('D:\\project\\Playbook\\snapshot2.bin', 'rb') as f:
        f.seek(start)
        after = f.read(size + 16)
    
    # Interpret as different data types
    print('\n  Interpretation:')
    
    # As uint32
    print('  As uint32 array:')
    for i in range(0, min(size, 64), 4):
        if i + 4 <= len(before):
            b = struct.unpack_from('<I', before, i)[0]
            a = struct.unpack_from('<I', after, i)[0]
            if b != a:
                print('    Offset +0x{:04X}: 0x{:08X} -> 0x{:08X}'.format(i, b, a))
    
    # As float
    print('  As float array:')
    for i in range(0, min(size, 64), 4):
        if i + 4 <= len(before):
            b = struct.unpack_from('<f', before, i)[0]
            a = struct.unpack_from('<f', after, i)[0]
            if b != a:
                print('    Offset +0x{:04X}: {:.4f} -> {:.4f}'.format(i, b, a))
    
    # As uint16
    print('  As uint16 array:')
    for i in range(0, min(size, 64), 2):
        if i + 2 <= len(before):
            b = struct.unpack_from('<H', before, i)[0]
            a = struct.unpack_from('<H', after, i)[0]
            if b != a:
                print('    Offset +0x{:04X}: 0x{:04X} ({}) -> 0x{:04X} ({})'.format(i, b, b, a, a))
    
    print()

# Check if any of these could be playbook data
# Play IDs are typically small integers (0-999)
print('\n=== Checking for play ID patterns ===')
for start, end in regions:
    with open('D:\\project\\Playbook\\snapshot1.bin', 'rb') as f:
        f.seek(start)
        before = f.read(end - start + 1)
    with open('D:\\project\\Playbook\\snapshot2.bin', 'rb') as f:
        f.seek(start)
        after = f.read(end - start + 1)
    
    # Look for arrays of small values
    values_before = []
    values_after = []
    for i in range(0, len(before) - 1, 2):
        values_before.append(struct.unpack_from('<H', before, i)[0])
        values_after.append(struct.unpack_from('<H', after, i)[0])
    
    small_before = [v for v in values_before if 0 < v < 1000]
    small_after = [v for v in values_after if 0 < v < 1000]
    
    if small_before or small_after:
        print('Region 0x{:X}:'.format(start))
        print('  Small values (< 1000) before: {}'.format(small_before[:20]))
        print('  Small values (< 1000) after: {}'.format(small_after[:20]))
        print()
