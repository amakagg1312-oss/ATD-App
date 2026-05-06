import struct

data = open('playdata.iff', 'rb').read()
print('Size:', len(data))
print('Header:', data[:20])
print('First uint32:', struct.unpack_from('<I', data, 0)[0])
print('Second uint32:', struct.unpack_from('<I', data, 4)[0])

# Check if it's a ZIP
if data[:2] == b'PK':
    print('This is a ZIP file')

# Look for strings
print('\nLooking for string table...')
# Look for UTF-16BE markers
null16 = b'\x00\x00'
pos = data.find(null16.encode() if isinstance(null16, str) else null16)
print('First null16 at:', pos)