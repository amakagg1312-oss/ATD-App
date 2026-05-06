import os

for f in ['RosterNBA0004', 'RosterNBA0005']:
    path = 'D:\\project\\Playbook\\{}'.format(f)
    if not os.path.exists(path):
        continue
    with open(path, 'rb') as fh:
        content = fh.read()
    
    print('{}: {} bytes'.format(f, len(content)))
    
    # Search for specific play name patterns
    terms = [
        b'mem', b'MEM', b'fist', b'FIST', b'quick', b'QUICK',
        b'chest', b'CHEST', b'iso', b'ISO', b'go', b'GO',
        b'90', b'14', b'1 ', b'2 ', b'3 ',
        b'isolation', b'ISOLATION', b'pick', b'PICK',
        b'playbook', b'PLAYBOOK', b'play_cat', b'PLAY_CAT',
        b'offense', b'OFFENSE', b'defense', b'DEFENSE',
        b'horns', b'HORNS', b'flex', b'FLEX',
    ]
    
    found_count = 0
    for term in terms:
        idx = 0
        while found_count < 10:
            idx = content.find(term, idx)
            if idx == -1:
                break
            ctx = content[max(0,idx-10):idx+40]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print('  Found "{}" at 0x{:X}: ...{}...'.format(term.decode(), idx, ascii_ctx))
            found_count += 1
            idx += 1
    print()
