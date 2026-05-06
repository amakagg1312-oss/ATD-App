"""
Deep investigation of the 0x741Fxxx changing addresses and team name lookups.
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
print('module=0x{:X}  team_table=0x{:X}'.format(module_base, table_base))

# --- 1. Read 256 bytes around RVA+0x741F340 (covers 0x741F383 and context before the 0x741F4xx block) ---
print('\n=== 256 bytes @ RVA+0x741F300 ===')
d = mem_read(hproc, module_base + 0x741F300, 256)
for row in range(0, 256, 16):
    chunk = d[row:row+16]
    h = ' '.join('{:02X}'.format(b) for b in chunk)
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    rva = 0x741F300 + row
    # mark changing addresses
    markers = []
    for off in range(16):
        if rva + off == 0x741F383: markers.append('+0x{:X}=CHANGE'.format(off))
    print('  RVA+0x{:05X}: {}  {}  {}'.format(rva, h.ljust(47), asc, ' '.join(markers)))

# --- 2. Read 128 bytes around RVA+0x741F9E0 (covers 0x741F9E3) ---
print('\n=== 128 bytes @ RVA+0x741F9C0 ===')
d = mem_read(hproc, module_base + 0x741F9C0, 128)
for row in range(0, 128, 16):
    chunk = d[row:row+16]
    h = ' '.join('{:02X}'.format(b) for b in chunk)
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    rva = 0x741F9C0 + row
    markers = []
    for off in range(16):
        if rva + off == 0x741F9E3: markers.append('+0x{:X}=CHANGE'.format(off))
    print('  RVA+0x{:05X}: {}  {}  {}'.format(rva, h.ljust(47), asc, ' '.join(markers)))

# --- 3. Follow pointers to find team names for all 40 teams ---
print('\n=== Team names (following pointer chains) ===')
NBA_TEAMS = [b'76ers', b'Lakers', b'Celtics', b'Warriors', b'Bulls',
             b'Knicks', b'Nets', b'Heat', b'Spurs', b'Bucks',
             b'Clippers', b'Nuggets', b'Suns', b'Mavericks', b'Thunder',
             b'Rockets', b'Blazers', b'Jazz', b'Kings', b'Hornets',
             b'Wolves', b'Grizzlies', b'Cavaliers', b'Pacers', b'Hawks',
             b'Magic', b'Raptors', b'Pistons', b'Wizards', b'Pelicans',
             b'Nuggets', b'Nuggets', b'Nuggets']

CITY_NAMES = [b'Philadelphia', b'Los Angeles', b'Boston', b'Golden State',
              b'Chicago', b'New York', b'Brooklyn', b'Miami', b'San Antonio',
              b'Milwaukee', b'Denver', b'Phoenix', b'Dallas', b'Oklahoma City',
              b'Houston', b'Portland', b'Utah', b'Sacramento', b'Charlotte',
              b'Minnesota', b'Memphis', b'Cleveland', b'Indiana', b'Atlanta',
              b'Orlando', b'Toronto', b'Detroit', b'Washington', b'New Orleans',
              b'OKC', b'Celtics', b'Sixers', b'Knick', b'Laker', b'Buck',
              b'Hawk', b'Jazz', b'King', b'Heat', b'Bull']

def try_find_name(hproc, addr, depth=0):
    """Try to find a team name string starting at addr, following pointers up to depth."""
    if depth > 3:
        return None
    data = mem_read(hproc, addr, 256)
    if not data:
        return None
    # Check for ASCII name in this block
    for term in NBA_TEAMS + CITY_NAMES:
        if term in data:
            # Get context
            idx = data.index(term)
            return data[max(0,idx-2):idx+len(term)+20].decode('ascii','replace').strip()
    # Follow any heap pointers
    for i in range(0, min(len(data)-7, 128), 8):
        val = struct.unpack_from('<Q', data, i)[0]
        if 0x100000000 < val < 0xF00000000:
            result = try_find_name(hproc, val, depth+1)
            if result:
                return result
    return None

for idx in range(42):
    team_addr = table_base + idx * TEAM_STRIDE
    tdata = mem_read(hproc, team_addr, 256)
    if not tdata:
        continue
    # Try direct search first
    name = try_find_name(hproc, team_addr, 0)
    if not name:
        # Try following first few pointers from the struct
        for ptr_off in range(0, 64, 8):
            ptr_val = struct.unpack_from('<Q', tdata, ptr_off)[0]
            if 0x100000000 < ptr_val < 0xF00000000:
                name = try_find_name(hproc, ptr_val, 1)
                if name:
                    break
    print('  Team[{:2d}] @ 0x{:X}: {}'.format(idx, team_addr, name or '???'))

# --- 4. Try to read what the pointers at 0x741F320-0x741F360 point to ---
print('\n=== What do the module-internal pointers at 0x741F320..360 point to? ===')
pdata = mem_read(hproc, module_base + 0x741F318, 8 * 10)
for i in range(10):
    ptr = struct.unpack_from('<Q', pdata, i*8)[0]
    rva_src = 0x741F318 + i * 8
    if ptr > module_base and ptr < module_base + 0x10000000:
        # Module-internal pointer: read bytes there
        d = mem_read(hproc, ptr, 32)
        if d:
            h = ' '.join('{:02X}'.format(b) for b in d[:16])
            asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in d[:16])
            print('  RVA+0x{:X} -> module+0x{:X}: {} {}'.format(
                rva_src, ptr - module_base, h, asc))

kernel32.CloseHandle(hproc)
