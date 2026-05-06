import struct

snap1_path = 'D:\\project\\Playbook\\snapshot1.bin'
with open(snap1_path, 'rb') as f:
    snap1 = f.read()

# Search for potential play catalog structure
# Look for arrays of small integers that could be play IDs
print('Searching for arrays of small integers (potential play IDs)...')

# Scan for sequences of uint8 values in range 1-200 (common play ID range)
for start in range(0, len(snap1) - 200, 1):
    # Check if next 50 bytes look like small uint8 values
    values = []
    valid = True
    for j in range(50):
        val = snap1[start + j]
        if val > 200 or val == 0:
            valid = False
            break
        values.append(val)
    
    if valid and len(values) >= 20:
        # Check if values are diverse (not all same)
        if len(set(values)) > 5:
            print('  0x{:X}: {}'.format(start, values[:30]))
            # Show context
            ctx = snap1[max(0,start-20):start+60]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print('    Context: ...{}...'.format(ascii_ctx))
            print()
            if len(values) > 30:
                break

# Also search for uint16 arrays with values 1-500
print('\nSearching for uint16 arrays (values 1-500)...')
for start in range(0, len(snap1) - 100, 2):
    values = []
    valid = True
    for j in range(0, 40, 2):
        val = struct.unpack_from('<H', snap1, start + j)[0]
        if val > 500 or val == 0:
            valid = False
            break
        values.append(val)
    
    if valid and len(values) >= 10:
        if len(set(values)) > 3:
            print('  0x{:X}: {}'.format(start, values[:15]))
            ctx = snap1[max(0,start-20):start+40]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print('    Context: ...{}...'.format(ascii_ctx))
            print()
            if len(values) > 15:
                break
