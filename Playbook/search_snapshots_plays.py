import os

# Search the memory snapshots for play-related strings
for snap in ['snapshot1.bin', 'snapshot2.bin']:
    path = 'D:\\project\\Playbook\\{}'.format(snap)
    with open(path, 'rb') as f:
        data = f.read()
    
    print('=== {} ==='.format(snap))
    
    # Search for specific play names
    terms = [
        b'MEM ISO', b'ISO 3', b'FIST 14', b'QUICK 2', b'QUICK 1',
        b'CHEST', b'90 FIST', b'14 QUICK', b'1 CHEST',
        b'HORNS', b'FLEX', b'PRINCETON', b'TRIANGLE', b'PISTOL',
        b'MOTION', b'ISOLATION', b'PICK AND', b'PICK N',
        b'OFFENSE', b'DEFENSE', b'PLAY_CAT', b'play_cat',
        b'PLAYBOOK', b'playbook',
    ]
    
    for term in terms:
        idx = 0
        found = 0
        while found < 5:
            idx = data.find(term, idx)
            if idx == -1:
                break
            ctx = data[max(0,idx-20):idx+40]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print('  0x{:X}: ...{}...'.format(idx, ascii_ctx))
            found += 1
            idx += 1
    print()
