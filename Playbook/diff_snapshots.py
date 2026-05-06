import os

snap1_path = 'D:\\project\\Playbook\\snapshot1.bin'
snap2_path = 'D:\\project\\Playbook\\snapshot2.bin'

print('Loading snapshots...')
with open(snap1_path, 'rb') as f:
    snap1 = f.read()
with open(snap2_path, 'rb') as f:
    snap2 = f.read()

print('Snapshot 1 size: {} bytes'.format(len(snap1)))
print('Snapshot 2 size: {} bytes'.format(len(snap2)))

# Find differences
print('\nFinding differences...')
diffs = []
block_size = 0x1000  # 4KB blocks
for i in range(0, min(len(snap1), len(snap2)), block_size):
    block1 = snap1[i:i+block_size]
    block2 = snap2[i:i+block_size]
    if block1 != block2:
        # Find exact byte positions within the block
        for j in range(min(len(block1), len(block2))):
            if block1[j] != block2[j]:
                diffs.append((i + j, block1[j], block2[j]))

print('Found {} changed bytes'.format(len(diffs)))

# Group diffs into regions
if diffs:
    regions = []
    current_start = diffs[0][0]
    current_end = diffs[0][0]
    for addr, old_val, new_val in diffs:
        if addr - current_end > 16:
            regions.append((current_start, current_end))
            current_start = addr
        current_end = addr
    regions.append((current_start, current_end))
    
    print('\nChanged regions ({} total):'.format(len(regions)))
    for start, end in regions:
        size = end - start + 1
        offset_from_team = start - (0x2A75A17D0 - (0x2A75A17D0 - 0x2A5CA17D0))
        print('  0x{:X} - 0x{:X} ({} bytes, offset from dump start: +0x{:X})'.format(
            start, end, size, start - 0x2A5CA17D0))
        
        # Show the changed bytes
        with open(snap1_path, 'rb') as f:
            f.seek(start - 16)
            old_context = f.read(size + 32)
        with open(snap2_path, 'rb') as f:
            f.seek(start - 16)
            new_context = f.read(size + 32)
        
        print('    Before: {}'.format(' '.join('{:02X}'.format(b) for b in old_context[:min(64, len(old_context))])))
        print('    After:  {}'.format(' '.join('{:02X}'.format(b) for b in new_context[:min(64, len(new_context))])))
        
        # Show as ASCII
        old_ascii = ''.join(chr(b) if 32 <= b < 127 else '.' for b in old_context[:min(64, len(old_context))])
        new_ascii = ''.join(chr(b) if 32 <= b < 127 else '.' for b in new_context[:min(64, len(new_context))])
        print('    Before ASCII: {}'.format(old_ascii))
        print('    After ASCII:  {}'.format(new_ascii))
        print()
