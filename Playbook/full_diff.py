import os

# Full diff of both snapshots
snap1_path = 'D:\\project\\Playbook\\snapshot1.bin'
snap2_path = 'D:\\project\\Playbook\\snapshot2.bin'

print('Loading snapshots...')
with open(snap1_path, 'rb') as f:
    snap1 = f.read()
with open(snap2_path, 'rb') as f:
    snap2 = f.read()

print('Snapshot sizes: {} and {} bytes'.format(len(snap1), len(snap2)))

# Find all changed bytes
print('Finding differences...')
changed_regions = []
in_region = False
region_start = 0

for i in range(min(len(snap1), len(snap2))):
    if snap1[i] != snap2[i]:
        if not in_region:
            region_start = i
            in_region = True
    else:
        if in_region:
            changed_regions.append((region_start, i - 1))
            in_region = False

if in_region:
    changed_regions.append((region_start, min(len(snap1), len(snap2)) - 1))

print('Found {} changed regions'.format(len(changed_regions)))

# Show all changed regions
for start, end in changed_regions:
    size = end - start + 1
    print('  0x{:X} - 0x{:X} ({} bytes)'.format(start, end, size))
    
    # Show the changed data
    before = snap1[start:end+1]
    after = snap2[start:end+1]
    
    # As hex
    print('    Before: {}'.format(' '.join('{:02X}'.format(b) for b in before[:32])))
    print('    After:  {}'.format(' '.join('{:02X}'.format(b) for b in after[:32])))
    
    # As uint16
    if size >= 4:
        values_before = []
        values_after = []
        for j in range(0, min(size, 32), 2):
            vb = (before[j+1] << 8) | before[j]
            va = (after[j+1] << 8) | after[j]
            values_before.append(vb)
            values_after.append(va)
        print('    Before (uint16): {}'.format(values_before[:10]))
        print('    After (uint16):  {}'.format(values_after[:10]))
    
    # As uint32
    if size >= 8:
        values_before = []
        values_after = []
        for j in range(0, min(size, 32), 4):
            vb = (before[j+3] << 24) | (before[j+2] << 16) | (before[j+1] << 8) | before[j]
            va = (after[j+3] << 24) | (after[j+2] << 16) | (after[j+1] << 8) | after[j]
            values_before.append(vb)
            values_after.append(va)
        print('    Before (uint32): {}'.format(values_before[:5]))
        print('    After (uint32):  {}'.format(values_after[:5]))
    
    print()
