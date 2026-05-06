import json

d = json.load(open('76ers_playbook.json'))
print('Total plays:', len(d['plays']))
indices = [p['index'] for p in d['plays'][:15]]
print('First 15 indices:', indices)
print('Indices range:', min(indices), '-', max(indices))