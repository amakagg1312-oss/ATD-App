import struct
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Read the playdata file directly
playdata_path = r'D:\project\Playbook\game files\playdata_extracted\Plays.playdata'

with open(playdata_path, 'rb') as f:
    data = f.read()

print('File size: {} bytes'.format(len(data)))

# Try to find play names of "FIST"
searches = [b'FIST', b'MIDDLE', b'FLAT', b'IVE', b'CHEST']

print('\n=== Searching in playdata file ===')
for s in searches:
    pos = data.find(s)
    if pos >= 0:
        print('Found {} at offset {} (0x{})'.format(s, pos, hex(pos)))
        # Context
        start = max(0, pos - 10)
        end = min(len(data), pos + 40)
        ctx = data[start:end]
        print('  Context: {}'.format(ctx))

# Try different decoding - maybe strings are stored differently
print('\n=== Looking for any strings ===')

# Scan for ASCII strings visible
import re
ascii_strings = re.findall(b'[\x20-\x7e]{4,}', data)
print('Found {} ASCII strings'.format(len(ascii_strings)))

# Look for FIST strings
fist_strings = [s for s in ascii_strings if b'FIST' in s]
print('\nFIST strings:')
for s in fist_strings[:20]:
    print('  {}'.format(s))

# Also look for UTF-16 patterns
print('\n=== Looking for UTF-16 patterns ===')

# In UTF-16, null bytes appear between chars
# Look for pattern: letter, null, letter, null...
for i in range(0, len(data) - 20, 2):
    # Check if this could be start of UTF-16 string
    if data[i] != 0 and data[i+1] == 0:
        # Possible start of UTF-16 char
        # Try decode
        try:
            # Get 30 bytes
            chunk = data[i:i+40]
            decoded = chunk.decode('utf-16-le', errors='replace')
            # Check if it contains FIST
            if 'FIST' in decoded:
                print('\nPotential UTF-16 at offset {}: {}'.format(i, decoded[:40]))
                print('  Raw: {}'.format(chunk[:30]))
        except:
            pass

CloseHandle