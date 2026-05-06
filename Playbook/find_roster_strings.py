import struct
import os

def find_strings_in_roster(path, min_len=5):
    with open(path, 'rb') as f:
        data = f.read()
    
    print('File: {} ({} bytes)'.format(os.path.basename(path), len(data)))
    
    # Find all ASCII strings
    strings = []
    current_start = None
    current_str = b''
    
    for i, b in enumerate(data):
        if 32 <= b < 127:
            if current_start is None:
                current_start = i
            current_str += bytes([b])
        else:
            if len(current_str) >= min_len:
                strings.append((current_start, current_str.decode('ascii')))
            current_start = None
            current_str = b''
    
    print('Found {} strings (min {} chars)'.format(len(strings), min_len))
    
    # Show strings that might be related to plays/teams/players
    keywords = ['bucks', 'celtics', 'lakers', 'warriors', 'sixers', 'knicks', 'nuggets', 'heat', 'play', 'offense', 'defense', 'set', 'motion', 'iso', 'pick', 'roll', 'horn', 'fist', 'quick', 'chest', 'pistol', 'flex', 'triangle', 'princeton', 'alley', 'drive', 'post', 'screen', 'cut', 'spot', 'corner']
    
    print('\nRelevant strings:')
    for offset, s in strings:
        s_lower = s.lower()
        if any(kw in s_lower for kw in keywords):
            print('  0x{:X}: "{}"'.format(offset, s))
    
    # Also show team names to understand structure
    print('\nTeam/player names:')
    for offset, s in strings:
        s_lower = s.lower()
        if any(kw in s_lower for kw in ['bucks', 'celtics', 'lakers', 'warriors', 'sixers', 'knicks', 'nuggets', 'heat', 'curry', 'james', 'durant', 'embiid', 'antetokounmpo', 'doncic', 'jokic']):
            print('  0x{:X}: "{}"'.format(offset, s))

for f in ['RosterNBA0004', 'RosterNBA0005']:
    path = 'D:\\project\\Playbook\\{}'.format(f)
    if os.path.exists(path):
        find_strings_in_roster(path)
        print()
