import struct

# Search for play names in both snapshots
play_terms = [
    b'MEM ISO', b'ISO 3', b'FIST', b'QUICK', b'CHEST',
    b'90 FIST', b'14 QUICK', b'1 CHEST', b'PLAYBOOK',
    b'OFFENSE', b'DEFENSE', b'PLAY_CAT', b'play_cat',
    b'PICK_AND', b'ISOLATION', b'THREE_PT', b'3PT',
]

for snap_name in ['snapshot1.bin', 'snapshot2.bin']:
    print('\n=== Searching {} ==='.format(snap_name))
    with open('D:\\project\\Playbook\\{}'.format(snap_name), 'rb') as f:
        data = f.read()
    
    for term in play_terms:
        idx = data.find(term)
        if idx != -1:
            print('  Found "{}" at file offset 0x{:X}'.format(term.decode(), idx))
            # Show context
            context_start = max(0, idx - 20)
            context_end = min(len(data), idx + len(term) + 40)
            context = data[context_start:context_end]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
            print('    Context: ...{}...'.format(ascii_ctx))

# Also search for UTF-16 encoded versions
print('\n=== Searching for UTF-16 encoded play names ===')
with open('D:\\project\\Playbook\\snapshot1.bin', 'rb') as f:
    data = f.read()

play_terms_utf16 = [
    b'M\x00E\x00M\x00', b'I\x00S\x00O\x00', b'F\x00I\x00S\x00T\x00',
    b'Q\x00U\x00I\x00C\x00K\x00', b'C\x00H\x00E\x00S\x00T\x00',
    b'P\x00L\x00A\x00Y\x00', b'O\x00F\x00F\x00E\x00N\x00S\x00E\x00',
]

for term in play_terms_utf16:
    idx = data.find(term)
    if idx != -1:
        print('  Found UTF-16 "{}" at file offset 0x{:X}'.format(term.decode('utf-16-le', errors='ignore'), idx))
        context_start = max(0, idx - 20)
        context_end = min(len(data), idx + len(term) + 60)
        context = data[context_start:context_end]
        ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
        print('    Context: ...{}...'.format(ascii_ctx))
