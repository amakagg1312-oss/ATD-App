import struct
import os

def parse_roster(path):
    with open(path, 'rb') as f:
        data = f.read()
    
    print('File: {} ({} bytes)'.format(os.path.basename(path), len(data)))
    
    # Header: EBNH
    magic = data[:4]
    print('Magic: {}'.format(magic))
    
    # Parse header fields
    if magic == b'EBNH':
        # Try common header structure
        header_fields = struct.unpack_from('<II', data, 4)
        print('Header fields: {}'.format(header_fields))
        
        # Search for known play ID patterns
        # Play IDs in 2K are typically stored as small integers or in specific tables
        # Look for sections with repeated small values
        
        # Search for text strings that might be play names
        print('\nSearching for ASCII strings (min 4 chars)...')
        strings = []
        current = b''
        for i, b in enumerate(data):
            if 32 <= b < 127:
                current += bytes([b])
            else:
                if len(current) >= 4:
                    strings.append((i - len(current), current.decode('ascii')))
                current = b''
        
        # Filter for play-related strings
        play_keywords = ['iso', 'fist', 'quick', 'chest', 'pick', 'horn', 'flex', 'motion', 'pistol', 'triangle', 'princeton', 'play', 'offense', 'defense', 'set']
        for offset, s in strings:
            s_lower = s.lower()
            if any(kw in s_lower for kw in play_keywords):
                print('  0x{:X}: "{}"'.format(offset, s))
        
        # Also search for UTF-16 strings
        print('\nSearching for UTF-16 strings (min 4 chars)...')
        for i in range(0, len(data) - 8, 2):
            chunk = data[i:i+20]
            try:
                # Check if it looks like UTF-16
                if chunk[1] == 0 and chunk[3] == 0 and chunk[5] == 0:
                    # Try to decode
                    end = i
                    while end + 1 < len(data) and data[end] != 0 and data[end+1] == 0:
                        end += 2
                    if end - i >= 8:
                        s = data[i:end].decode('utf-16-le', errors='ignore')
                        if len(s) >= 4:
                            s_lower = s.lower()
                            if any(kw in s_lower for kw in play_keywords):
                                print('  0x{:X}: "{}"'.format(i, s))
            except:
                pass

for f in ['RosterNBA0004', 'RosterNBA0005']:
    path = 'D:\\project\\Playbook\\{}'.format(f)
    if os.path.exists(path):
        parse_roster(path)
        print()
