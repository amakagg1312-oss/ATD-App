import struct

snap1_path = 'D:\\project\\Playbook\\snapshot1.bin'
snap2_path = 'D:\\project\\Playbook\\snapshot2.bin'

with open(snap1_path, 'rb') as f:
    snap1 = f.read()
with open(snap2_path, 'rb') as f:
    snap2 = f.read()

# The repeating pattern starts at 0xEAE344
# Let's examine the structure around it
start = 0xEAE300
end = 0xEAE600

print('=== Data structure around repeating pattern ===')
print('File offset range: 0x{:X} - 0x{:X}'.format(start, end))

# Read the data
data1 = snap1[start:end]
data2 = snap2[start:end]

# Interpret as structs of 12 bytes (based on the 12-byte interval)
print('\nAs 12-byte structs:')
for i in range(0, len(data1) - 11, 12):
    struct_data = data1[i:i+12]
    # Try different interpretations
    uint16_vals = struct.unpack_from('<6H', struct_data, 0)
    uint32_vals = struct.unpack_from('<3I', struct_data, 0)
    float_vals = struct.unpack_from('<3f', struct_data, 0)
    
    # Check if this struct changed
    struct_data2 = data2[i:i+12]
    changed = struct_data != struct_data2
    
    if changed:
        print('  Struct {} (offset 0x{:X}): CHANGED'.format(i // 12, start + i))
        print('    Before uint16: {}'.format(uint16_vals))
        uint16_vals2 = struct.unpack_from('<6H', struct_data2, 0)
        print('    After uint16:  {}'.format(uint16_vals2))
        print('    Before uint32: {}'.format(uint32_vals))
        uint32_vals2 = struct.unpack_from('<3I', struct_data2, 0)
        print('    After uint32:  {}'.format(uint32_vals2))
        print('    Before floats: {}'.format(float_vals))
        float_vals2 = struct.unpack_from('<3f', struct_data2, 0)
        print('    After floats:  {}'.format(float_vals2))

# Also look at the data before the repeating pattern
print('\n=== Data before repeating pattern (0xEADF00 - 0xEAE350) ===')
data_before = snap1[0xEADF00:0xEAE350]
for i in range(0, len(data_before) - 3, 4):
    val = struct.unpack_from('<I', data_before, i)[0]
    fval = struct.unpack_from('<f', data_before, i)[0]
    if i % 16 == 0:
        print('  0x{:X}: uint32={}, float={:.4f}'.format(0xEADF00 + i, val, fval))
