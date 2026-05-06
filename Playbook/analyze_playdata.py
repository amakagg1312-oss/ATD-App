import os

path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
size = os.path.getsize(path)
print('Plays.playdata: {} bytes'.format(size))

with open(path, 'rb') as f:
    data = f.read(200)

print('Header: {}'.format(' '.join('{:02X}'.format(b) for b in data[:64])))
ascii_hdr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:100])
print('ASCII: {}'.format(ascii_hdr))

# Search for play names
with open(path, 'rb') as f:
    content = f.read()

terms = [b'MEM ISO', b'FIST', b'QUICK', b'CHEST', b'ISO', b'PICK', b'HORNS', b'FLEX', b'PRINCETON', b'TRIANGLE', b'PISTOL', b'MOTION', b'isolation', b'3PT', b'OFFENSE', b'DEFENSE', b'PLAY_CAT', b'play_cat', b'go', b'GO', b'90', b'14', b'alley', b'drive', b'post', b'screen', b'cut', b'spot', b'corner']

print('\nSearching for play-related strings:')
for term in terms:
    idx = content.lower().find(term.lower())
    if idx != -1:
        ctx = content[max(0,idx-20):idx+60]
        ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
        print('  Found "{}" at 0x{:X}: ...{}...'.format(term.decode(), idx, ascii_ctx))
