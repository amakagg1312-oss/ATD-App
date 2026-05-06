with open('D:\\project\\Playbook\\game files\\all_play_names.txt', 'r') as f:
    lines = f.readlines()

# Search for the specific plays the user mentioned
search_terms = ['MEM ISO', '90 FIST', 'QUICK 1 CHEST', 'QUICK 1', 'QUICK 2', 'FIST 14', 'MEM', 'ISO 3', 'CHEST']

for term in search_terms:
    matches = [l.strip() for l in lines if term.lower() in l.lower()]
    if matches:
        print('=== Plays containing "{}" ({} found) ==='.format(term, len(matches)))
        for m in matches[:30]:
            print('  {}'.format(m))
        if len(matches) > 30:
            print('  ... and {} more'.format(len(matches) - 30))
        print()
