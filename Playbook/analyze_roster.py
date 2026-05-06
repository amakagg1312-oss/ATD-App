import struct
import os

def analyze_roster_structure(path):
    with open(path, 'rb') as f:
        data = f.read()
    
    print('File: {} ({} bytes)'.format(os.path.basename(path), len(data)))
    
    # EBNH header analysis
    # EBNH is typically: Magic(4) + Version(4) + NumTables(4) + TableOffsets...
    magic = data[:4]
    version = struct.unpack_from('<I', data, 4)[0]
    num_tables = struct.unpack_from('<I', data, 8)[0]
    
    print('Version: {}'.format(version))
    print('NumTables: {}'.format(num_tables))
    
    # If num_tables is reasonable, try to read table offsets
    if 0 < num_tables < 1000:
        print('\nTable offsets:')
        for i in range(num_tables):
            offset = struct.unpack_from('<I', data, 12 + i*4)[0]
            print('  Table {}: 0x{:X}'.format(i, offset))
    
    # Search for patterns that could be play IDs
    # Play IDs are typically small integers (0-999) stored in arrays
    print('\nSearching for arrays of small integers (potential play IDs)...')
    
    # Scan for sequences of uint16 values in range 1-500
    for start in range(0, len(data) - 100, 2):
        # Check if next 20 bytes look like small uint16 values
        values = []
        valid = True
        for j in range(0, 20, 2):
            val = struct.unpack_from('<H', data, start + j)[0]
            if val > 500 or val == 0:
                valid = False
                break
            values.append(val)
        
        if valid and len(values) >= 5:
            # Check if this is a unique pattern (not repeated nearby)
            print('  0x{:X}: {}'.format(start, values[:10]))
            break  # Just show first match
    
    # Search for known 2K play ID ranges
    # Common play IDs in 2K: 1-200 for offense, 200+ for defense
    print('\nSearching for potential play ID arrays (uint8, values 1-100)...')
    for start in range(0, len(data) - 50, 1):
        values = []
        valid = True
        for j in range(20):
            val = data[start + j]
            if val > 100 or val == 0:
                valid = False
                break
            values.append(val)
        
        if valid and len(values) >= 10:
            # Check if values are diverse (not all same)
            if len(set(values)) > 3:
                print('  0x{:X}: {}'.format(start, values[:20]))
                break

for f in ['RosterNBA0004', 'RosterNBA0005']:
    path = 'D:\\project\\Playbook\\{}'.format(f)
    if os.path.exists(path):
        analyze_roster_structure(path)
        print()
