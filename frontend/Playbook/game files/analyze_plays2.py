import struct

data = open('playdata_extracted/Plays.playdata', 'rb').read()
num_plays = struct.unpack_from('<I', data, 0)[0]
print('Number of plays:', num_plays)

# Entry format: Unknown but likely contains ID + offset to string
# Entries start at offset 4, strings start later

# Find string table - look for play names like "ISO", "PUNCH", etc.
# Try different entry sizes
for entry_size in [4, 8, 12, 16, 20, 24]:
    string_table_start = 4 + (num_plays * entry_size)
    if string_table_start < len(data) - 100:
        # Check if this looks like string data (UTF-16BE with nulls)
        test = data[string_table_start:string_table_start+20]
        # Look for ASCII play names
        try:
            s = test.decode('utf-8', errors='ignore').strip('\x00')
            if len(s) > 3:
                print(f'Entry size {entry_size}: String table at {string_table_start}, first: {s[:20]}')
                break
        except:
            pass