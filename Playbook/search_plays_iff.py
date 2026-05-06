import os

path = 'D:\\project\\Playbook\\game files\\playbookmenu_assignplays_extracted\\PlaybookMenu_AssignPlays.VCUIELEMENT'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Search for play names
terms = ['MEM ISO', 'FIST', 'QUICK', 'CHEST', 'ISO', 'PICK', '90 FIST', '14 QUICK', '1 CHEST', 'mem iso 3', 'isolation', 'three', '3pt']
for term in terms:
    idx = content.lower().find(term.lower())
    if idx != -1:
        ctx = content[max(0,idx-50):idx+200]
        print('Found "{}":'.format(term))
        print(ctx)
        print('---')
