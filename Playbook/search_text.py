import os

path = 'D:\\project\\Playbook\\game files\\english_extracted\\TEXT.VCLOCALIZEDATA'
size = os.path.getsize(path)
print('TEXT.VCLOCALIZEDATA: {} bytes'.format(size))

with open(path, 'rb') as f:
    data = f.read(200)
print('Header: {}'.format(' '.join('{:02X}'.format(b) for b in data[:40])))

# Search for play names
with open(path, 'rb') as f:
    content = f.read()

terms = [b'MEM ISO', b'FIST', b'QUICK', b'CHEST', b'ISO', b'PICK', b'HORNS', b'FLEX', b'PRINCETON', b'TRIANGLE', b'PISTOL', b'MOTION', b'isolation', b'three', b'3PT', b'GO', b'ALLEY', b'DRIVE', b'POST', b'SCREEN', b'CUT', b'SPOT', b'CORNER', b'PLAYBOOK', b'OFFENSE', b'DEFENSE']
for term in terms:
    idx = content.lower().find(term.lower())
    if idx != -1:
        ctx = content[max(0,idx-30):idx+100]
        ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
        print('Found "{}" at 0x{:X}: ...{}...'.format(term, idx, ascii_ctx))
        print()
