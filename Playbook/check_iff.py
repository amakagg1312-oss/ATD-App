import os

base = 'D:\\project\\Playbook\\game files'
files_to_check = [
    'playbookmenu_assignplays_extracted/PlaybookMenu_AssignPlays.VCUIELEMENT',
    'playbookmenu_editplays_extracted/PlaybookMenu_EditPlays.VCUIELEMENT',
    'playbook_extracted/playbook.SCNE',
]

for rel_path in files_to_check:
    path = os.path.join(base, rel_path)
    if not os.path.exists(path):
        print('NOT FOUND: {}'.format(path))
        continue
    size = os.path.getsize(path)
    with open(path, 'rb') as fh:
        content = fh.read()
    print('{}: {} bytes'.format(rel_path, size))
    
    # Check format
    if b'<?xml' in content[:200] or b'<VCUI' in content[:200] or b'<SCNE' in content[:200]:
        print('  Format: XML')
    elif b'{' in content[:200]:
        print('  Format: JSON-like')
    else:
        print('  Header: {}'.format(' '.join('{:02X}'.format(b) for b in content[:40])))
    
    # Search for play names
    for term in [b'MEM ISO', b'FIST', b'QUICK', b'CHEST', b'ISO', b'PICK', b'play', b'OFFENSE', b'DEFENSE', b'ASSIGN', b'EDIT']:
        idx = content.lower().find(term.lower())
        if idx != -1:
            ctx = content[max(0,idx-20):idx+60]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print('  Found "{}": ...{}...'.format(term.decode(), ascii_ctx))
    print()
