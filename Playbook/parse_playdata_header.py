import struct

path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

# The first 4 bytes are 0x71 = 113, which might be the header size
# Let's parse the header as a table of section descriptors
header_size = struct.unpack_from('<I', data, 0)[0]
print('Header size: {} bytes (0x{:X})'.format(header_size, header_size))

# Each section descriptor might be 24 bytes (3x8 bytes)
# Pattern: [offset_4][zeros_4][size_or_id_4][zeros_4][something_4][zeros_4]
sections = []
for i in range(8, header_size, 24):
    if i + 24 > len(data):
        break
    offset = struct.unpack_from('<I', data, i)[0]
    zeros1 = struct.unpack_from('<I', data, i+4)[0]
    size_or_id = struct.unpack_from('<I', data, i+8)[0]
    zeros2 = struct.unpack_from('<I', data, i+12)[0]
    something = struct.unpack_from('<I', data, i+16)[0]
    zeros3 = struct.unpack_from('<I', data, i+20)[0]
    
    if zeros1 == 0 and zeros2 == 0 and zeros3 == 0 and offset > 0:
        sections.append({
            'offset': offset,
            'size_or_id': size_or_id,
            'something': something,
            'header_pos': i
        })

print('Found {} sections:'.format(len(sections)))
for idx, sec in enumerate(sections):
    print('  Section {}: offset=0x{:X} ({}) size_or_id={} something=0x{:X}'.format(
        idx, sec['offset'], sec['offset'], sec['size_or_id'], sec['something']))

# Let's look at the data at each section offset
for idx, sec in enumerate(sections[:15]):
    off = sec['offset']
    print('\n=== Section {} at 0x{:X} ==='.format(idx, off))
    
    # First 4 bytes might be size
    sec_size = struct.unpack_from('<I', data, off)[0]
    print('  First 4 bytes (size?): {}'.format(sec_size))
    
    # Read the section data
    chunk = data[off:off+min(sec_size+8, 128)]
    
    # Try to interpret as text
    ascii_chunk = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk[:80])
    print('  ASCII: {}'.format(ascii_chunk))
    
    # Check if it starts with a known magic
    magic = chunk[:4]
    print('  Magic: {}'.format(magic))
