import os

base = 'D:\\project\\Playbook\\game files\\english_extracted'

# Check SLUG files for text content
slug_files = ['gameplay.SLUG', 'generic.SLUG', 'mycareer.SLUG', 'myteam.SLUG', 'title.SLUG', 'miscgamemode.SLUG']

for slug in slug_files:
    path = os.path.join(base, slug)
    if not os.path.exists(path):
        continue
    with open(path, 'rb') as f:
        content = f.read()
    
    print('{}: {} bytes'.format(slug, len(content)))
    
    # Search for play-related terms
    terms = [b'play', b'offense', b'defense', b'pick', b'roll', b'iso', b'fist', b'quick', b'chest', b'horn', b'flex', b'motion', b'pistol', b'triangle', b'princeton', b'alley', b'drive', b'post', b'screen', b'cut', b'spot', b'corner']
    
    found = False
    for term in terms:
        idx = content.lower().find(term)
        if idx != -1:
            ctx = content[max(0,idx-20):idx+60]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print('  Found "{}": ...{}...'.format(term.decode(), ascii_ctx))
            found = True
    
    if not found:
        print('  No play-related terms found')
    print()
