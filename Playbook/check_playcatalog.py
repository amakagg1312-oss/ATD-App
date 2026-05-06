import os

path = 'D:\\project\\Playbook\\game files\\playcatalog_extracted\\PlayCatalog.VCUIELEMENT'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print('PlayCatalog.VCUIELEMENT: {} bytes'.format(len(content)))

# Search for play names
terms = ['MEM ISO', 'FIST', 'QUICK', 'CHEST', 'ISO', 'PICK', 'HORNS', 'FLEX', 'PRINCETON', 'TRIANGLE', 'PISTOL', 'MOTION', 'isolation', 'three', '3pt', '90', '14', '1 ']
for term in terms:
    idx = content.lower().find(term.lower())
    if idx != -1:
        ctx = content[max(0,idx-50):idx+300]
        print('Found "{}":'.format(term))
        print(ctx)
        print('---')
