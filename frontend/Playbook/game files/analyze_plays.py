import struct

data = open('playdata_extracted/Plays.playdata', 'rb').read()
print('Size:', len(data))
print('Header (first 40 bytes):', data[:40])
print('First uint32:', struct.unpack_from('<I', data, 0)[0])

# How many plays?
num_plays = struct.unpack_from('<I', data, 0)[0]
print('Number of plays:', num_plays)

# Look for play string table
print('\nSearching for play names...')
# Strings start after play entries, usually at offset 4 or 8
# Check the entry size
entry_size = 8  # Try 8 bytes
for est in [4, 8, 12, 16, 20]:
    if (num_plays * est) < len(data):
        # Try to find string table
        string_start = num_plays * est
        # Look for UTF-16BE play name
        if data[string_start:string_start+2] == b'\x00\x00' or data[string_start:string_start+2] != b'\x00\x00':
            # Read first string
            print('Possible string table at offset', string_start, 'first bytes:', data[string_start:string_start+20])
            break