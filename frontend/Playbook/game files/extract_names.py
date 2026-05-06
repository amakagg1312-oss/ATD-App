import struct

data = open('playdata_extracted/Plays.playdata', 'rb').read()
size = len(data)
num_plays = struct.unpack_from('<I', data, 0)[0]
print('Number of plays:', num_plays)

# Find string table - try at the end where we saw UTF-16BE
# The strings seem to start from near the end
# Let's find where strings start by looking for null terminators

# Read last 500KB as UTF-16BE
string_data = data[-500000:]
text = string_data.decode('utf-16-be', errors='ignore')

# Split by null terminator
plays = text.split('\x00')
# Filter empty and short strings
play_names = [p.strip() for p in plays if len(p.strip()) > 3]

print('\nExtracted play names:')
for i, name in enumerate(play_names[:50]):
    print(i, name.encode('ascii', errors='ignore').decode())

print(f'\nTotal names found: {len(play_names)}')