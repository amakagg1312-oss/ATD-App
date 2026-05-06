path = r'D:\project\Playbook\game files\playcatalog json format.txt'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

terms = ['MEM ISO', 'FIST', 'QUICK', 'CHEST', 'ISO', 'PICK', 'HORNS', 'FLEX', 'PRINCETON', 'TRIANGLE', 'PISTOL', 'MOTION', 'isolation', 'three', '3pt', '90', '14', '1 ', 'go', 'chest']
for t in terms:
    idx = content.lower().find(t.lower())
    if idx != -1:
        ctx = content[max(0,idx-50):idx+200]
        print('Found "{}":'.format(t))
        print(ctx)
        print('---')
