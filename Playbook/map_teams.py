"""
Map franchise entries to team names and find what playbook IDs 24/26/28 correspond to.
Also scan the franchise table for playbook field candidates.
"""
import sys, struct
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]
franchise_base = struct.unpack('<Q', mem_read(hproc, module_base + 0x7E1E3D8, 8))[0]
FRANCHISE_STRIDE = 840

print('team_table=0x{:X}  franchise_base=0x{:X}'.format(table_base, franchise_base))

# --- 1. Read franchise table entries and find team names ---
print('\n=== Franchise table entries (all 40, looking for names) ===')
NBA_TERMS = [b'76ers', b'Lakers', b'Celtics', b'Warriors', b'Bulls',
             b'Knicks', b'Nets', b'Heat', b'Spurs', b'Bucks',
             b'Clippers', b'Nuggets', b'Suns', b'Mavericks', b'Thunder',
             b'Rockets', b'Blazers', b'Jazz', b'Kings', b'Hornets',
             b'Wolves', b'Grizzlies', b'Cavaliers', b'Pacers', b'Hawks',
             b'Magic', b'Raptors', b'Pistons', b'Wizards', b'Pelicans',
             b'Timberwolves', b'Trail', b'Cavalier']
CITY_TERMS = [b'Philadelphia', b'Los Angeles', b'Boston', b'Golden State',
              b'Chicago', b'New York', b'Brooklyn', b'Miami', b'San Antonio',
              b'Milwaukee', b'Denver', b'Phoenix', b'Dallas', b'Oklahoma',
              b'Houston', b'Portland', b'Utah', b'Sacramento', b'Charlotte',
              b'Minnesota', b'Memphis', b'Cleveland', b'Indiana', b'Atlanta',
              b'Orlando', b'Toronto', b'Detroit', b'Washington', b'New Orleans']

franchise_map = {}  # index -> name
for i in range(42):
    addr = franchise_base + i * FRANCHISE_STRIDE
    data = mem_read(hproc, addr, FRANCHISE_STRIDE)
    if not data:
        continue
    name = None
    for term in NBA_TERMS + CITY_TERMS:
        if term in data:
            idx2 = data.index(term)
            name = data[max(0,idx2):idx2+30].decode('ascii','replace').rstrip('\x00').strip()
            break
    franchise_map[i] = name

    # Also look for small ints at regular spots (potential playbook field)
    small = [(j, struct.unpack_from('<I', data, j)[0])
             for j in range(0, FRANCHISE_STRIDE-3, 4)
             if 1 <= struct.unpack_from('<I', data, j)[0] <= 50]

    print('  Franchise[{:2d}] @ 0x{:X}: {:30s}  small_ints: {}'.format(
        i, addr, name or '???', [(hex(j), v) for j, v in small[:5]]))

# --- 2. Dump first 64 bytes of franchise entries 11..14 ---
print('\n=== Full first 64 bytes of franchise entries 11-14 ===')
for i in range(10, 16):
    addr = franchise_base + i * FRANCHISE_STRIDE
    data = mem_read(hproc, addr, 64)
    if not data:
        continue
    print('\n  Franchise[{}] @ 0x{:X}:'.format(i, addr))
    for row in range(0, 64, 16):
        chunk = data[row:row+16]
        h = ' '.join('{:02X}'.format(b) for b in chunk)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print('    +0x{:03X}: {}  {}'.format(row, h, asc))

# --- 3. Search team structs for any string containing team names (wider scan) ---
print('\n=== Team struct wide scan for names (indices 10-16, 512 bytes each) ===')
for idx in range(10, 16):
    team_addr = table_base + idx * TEAM_STRIDE
    tdata = mem_read(hproc, team_addr, 512)
    if not tdata:
        continue
    found_terms = []
    for term in NBA_TERMS + CITY_TERMS:
        if term in tdata:
            pos = tdata.index(term)
            found_terms.append((pos, term.decode('ascii')))
    # Also check for wide chars (UTF-16 pattern)
    for term in [b'7\x006\x00', b'L\x00a\x00k\x00', b'C\x00e\x00l\x00',
                 b'B\x00u\x00l\x00', b'H\x00e\x00a\x00', b'S\x00p\x00u\x00']:
        if term in tdata:
            pos = tdata.index(term)
            found_terms.append((pos, 'UTF16:' + tdata[pos:pos+20:2].decode('ascii','replace')[:10]))
    if found_terms:
        print('  Team[{:2d}]: found: {}'.format(idx, found_terms))
    else:
        # Show small ints 1-50 in first 64 bytes
        small = [(j, tdata[j]) for j in range(min(512,len(tdata))) if 1 <= tdata[j] <= 50]
        print('  Team[{:2d}]: no names. Small bytes (1-50): {}'.format(idx, small[:8]))

# --- 4. Check the 16-byte entries around the changing addresses for all offsets 0x1380..0x1600 ---
print('\n=== ALL 16-byte entries in RVA+0x741F380..0x741F600 with byte[3] in 0x18..0x1E ===')
block = mem_read(hproc, module_base + 0x741F000, 0x1000)
for off in range(0, 0x1000 - 15, 16):
    b3 = block[off + 3]
    if 0x18 <= b3 <= 0x1E and b3 % 2 == 0:  # even values 24-30
        rva = 0x741F000 + off
        h = ' '.join('{:02X}'.format(x) for x in block[off:off+16])
        print('  RVA+0x{:X}: {}  byte[3]={}'.format(rva, h, b3))

# --- 5. Look for all UNIQUE byte[3] values in this 4KB block ---
print('\n=== Distribution of byte[3] values in RVA+0x741F000..0x741FFFF ===')
from collections import Counter
counter = Counter(block[off+3] for off in range(0, len(block)-15, 16))
for val, count in sorted(counter.items()):
    if count > 0 and val != 0:
        print('  byte[3]={:3d} (0x{:02X}): {:3d} occurrences'.format(val, val, count))

kernel32.CloseHandle(hproc)
