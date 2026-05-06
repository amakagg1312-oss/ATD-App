import struct

path = 'D:\\project\\Playbook\\game files\\english_extracted\\TEXT.VCLOCALIZEDATA'
with open(path, 'rb') as f:
    content = f.read()

# Header analysis
# Offset 0x10: 0x31 = 49 (could be number of string categories/sections)
# Offset 0x18: 0x2E5269 = 3035753 (could be string data offset)
# Offsets 0x20-0x2C: look like string counts or sizes

num_sections = struct.unpack_from('<I', content, 0x10)[0]
string_data_offset = struct.unpack_from('<I', content, 0x18)[0]

print('Num sections: {}'.format(num_sections))
print('String data offset: 0x{:X}'.format(string_data_offset))

# Let's look at the data at offset 0x18
print('\nData at 0x18:')
for i in range(0x18, 0x100, 4):
    val = struct.unpack_from('<I', content, i)[0]
    print('  0x{:02X}: 0x{:08X} ({})'.format(i, val, val))

# Try to find strings by looking for null-terminated sequences
print('\nSearching for null-terminated strings...')
strings = []
current_start = None
for i in range(0x1000, min(len(content), 0x100000)):
    b = content[i]
    if b == 0:
        if current_start is not None:
            s = content[current_start:i]
            if len(s) >= 4:
                try:
                    decoded = s.decode('ascii')
                    if all(32 <= ord(c) < 127 for c in decoded):
                        strings.append((current_start, decoded))
                except:
                    pass
            current_start = None
    else:
        if current_start is None:
            current_start = i

print('Found {} strings'.format(len(strings)))
for offset, s in strings[:50]:
    print('  0x{:X}: "{}"'.format(offset, s))
