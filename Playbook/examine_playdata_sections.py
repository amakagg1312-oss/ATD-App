import struct

path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

# The section at 0x3B5891 looked like an array of small integers (play IDs?)
# Let's examine it more carefully
offset = 0x3B5891
print('=== Section at 0x{:X} ==='.format(offset))

# Read as uint16 array
values16 = []
for i in range(0, 2000, 2):
    val = struct.unpack_from('<H', data, offset + i)[0]
    values16.append(val)

print('First 100 uint16 values:')
print(values16[:100])

# Check for patterns
# Look for sequences that might be play IDs
print('\nNon-zero unique values in first 500:')
unique_vals = sorted(set(v for v in values16[:500] if v > 0))
print(unique_vals[:50])
print('... total unique: {}'.format(len(unique_vals)))

# Also look at offset 0x3B5849, 0x3B57F3, etc. (nearby sections)
for off in [0x3B5849, 0x3B57F3, 0x3B57A3, 0x3B575D, 0x3B571B, 0x3B56CD, 0x3B5685]:
    print('\n=== Section at 0x{:X} ==='.format(off))
    vals = []
    for i in range(0, 64, 2):
        val = struct.unpack_from('<H', data, off + i)[0]
        vals.append(val)
    print('First 32 uint16: {}'.format(vals))
