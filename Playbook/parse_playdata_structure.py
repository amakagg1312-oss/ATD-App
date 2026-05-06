import struct

path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

# The play catalog contains play names, but we need to find where playbook assignments are stored.
# Let's look at the structure of the file to understand how plays are organized.

# First, let's find all the section offsets from the header
print('=== Parsing header structure ===')

# The header is 113 bytes (0x71)
# Let's read it as a series of section descriptors
header_size = struct.unpack_from('<I', data, 0)[0]
print('Header size: {} bytes'.format(header_size))

# Read the header as 24-byte sections (common pattern in game files)
sections = []
for i in range(8, header_size, 24):
    if i + 24 > len(data):
        break
    offset = struct.unpack_from('<I', data, i)[0]
    size = struct.unpack_from('<I', data, i+8)[0]
    flags = struct.unpack_from('<I', data, i+16)[0]
    
    if offset > 0 and offset < len(data):
        sections.append({'offset': offset, 'size': size, 'flags': flags, 'pos': i})
        print('  Section at 0x{:04X}: offset=0x{:X} size={} flags=0x{:X}'.format(i, offset, size, flags))

# Now let's examine each section
print('\n=== Examining sections ===')
for idx, sec in enumerate(sections):
    off = sec['offset']
    size = sec['size']
    
    # Read first 64 bytes
    chunk = data[off:off+64]
    
    # Try to interpret as text
    ascii_chunk = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk[:40])
    
    # Check if it starts with a known pattern
    print('\nSection {} at 0x{:X} (size={}):'.format(idx, off, size))
    print('  First bytes: {}'.format(' '.join('{:02X}'.format(b) for b in chunk[:20])))
    print('  ASCII: {}'.format(ascii_chunk))
    
    # If size is reasonable, read more
    if 0 < size < 1000000:
        # Check if this section contains play names
        section_data = data[off:off+min(size, 1000)]
        play_count = 0
        for i in range(0, len(section_data) - 1, 2):
            if section_data[i] != 0 and section_data[i+1] == 0:
                # Start of UTF-16LE string
                j = i
                while j + 1 < len(section_data) and section_data[j] != 0 and section_data[j+1] == 0:
                    j += 2
                if j - i >= 16:
                    try:
                        s = section_data[i:j].decode('utf-16-le', errors='ignore')
                        if len(s) >= 8 and any(c.isalpha() for c in s):
                            play_count += 1
                    except:
                        pass
        if play_count > 0:
            print('  Contains {} play names'.format(play_count))
