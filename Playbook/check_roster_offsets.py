import json

# Get the playbook offsets from memory
d = json.load(open('76ers_playbook.json'))
offsets = [p['byte_offset'] for p in d['plays'][:20]]
print('Playbook offsets (first 20):', offsets)

# Search for these offset values in roster file
data = open('RosterNBA0004', 'rb').read()
print('\nSearching for offsets in roster...')

search_count = 0
for offset_val in offsets:
    # Search for this 4-byte value
    b = offset_val.to_bytes(4, 'little')
    pos = data.find(b)
    if pos > 0:
        print(f'  Offset {offset_val} at 0x{pos:04X}')
        search_count += 1
        if search_count >= 5:
            break

if search_count == 0:
    print('  No matches found - trying different encoding')
    # Maybe stored differently - try different endianness
    for offset_val in offsets[:5]:
        b = offset_val.to_bytes(4, 'big')
        pos = data.find(b)
        if pos > 0:
            print(f'  Offset {offset_val} (big endian) at 0x{pos:04X}')