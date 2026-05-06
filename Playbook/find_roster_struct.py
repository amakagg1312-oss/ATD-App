"""
Scan the entire module .data section for pointers that lead to team-indexed structures.
The playbook is likely in a separate 'roster settings' array, not the live team struct.
We look for structures that:
 - Have a stride of ~100-1000 bytes
 - Contain NBA team names as strings OR player-related data patterns
 - Differ between our two playbook states
"""
import sys, struct, json, ctypes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess, TEAM_RVA, TEAM_STRIDE)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]
print('module=0x{:X}  team_table=0x{:X}'.format(module_base, table_base))

HEAP_MIN = 0x100000000
HEAP_MAX = 0xF00000000

# Scan a much wider range of module .data (the game .data section can be large)
# Known RVAs: Player=0x7E0DCC8, Team=0x7E1E318, Staff=0x7E1E358
# Let's scan from RVA 0x7800000 to 0x7F00000 (7MB window around known offsets)
scan_ranges = [
    (module_base + 0x7800000, module_base + 0x7E00000),  # before known RVAs
    (module_base + 0x7E00000, module_base + 0x7F00000),  # around known RVAs
    (module_base + 0x7F00000, module_base + 0x8200000),  # after known RVAs
]

all_ptrs = []
for scan_start, scan_end in scan_ranges:
    data = mem_read(hproc, scan_start, scan_end - scan_start)
    if not data:
        continue
    for i in range(0, len(data) - 7, 8):
        val = struct.unpack_from('<Q', data, i)[0]
        if HEAP_MIN < val < HEAP_MAX:
            rva = scan_start + i - module_base
            all_ptrs.append((rva, val))

print('Total pointers in scan range: {:,}'.format(len(all_ptrs)))

# For each pointer, read 4KB and try to identify what it is
# Look specifically for:
# 1. Structures containing "76ers" or other team names
# 2. Structures containing small playbook-like IDs (1-100)
# 3. Structures with exactly 30 or 40 entries (team count)

NBA_TEAMS = [b'76ers', b'Lakers', b'Celtics', b'Warriors', b'Bulls',
             b'Knicks', b'Nets', b'Heat', b'Spurs', b'Bucks',
             b'Clippers', b'Nuggets', b'Suns', b'Mavericks', b'Thunder']

NBA_WTEAMS = [t + b'\x00' for t in [b'7\x006\x00e\x00r\x00s\x00',
                                      b'L\x00a\x00k\x00e\x00r\x00s\x00',
                                      b'C\x00e\x00l\x00t\x00i\x00c\x00s\x00']]

print()
print('=== SEARCHING FOR TEAM-INDEXED STRUCTURES ===')
team_hits = []
for rva, addr in all_ptrs:
    data4k = mem_read(hproc, addr, 4096)
    if not data4k:
        continue
    # Check for ASCII team names
    for term in NBA_TEAMS:
        if term in data4k:
            team_hits.append((rva, addr, term.decode()))
            break

print('Pointers with NBA team name strings: {:}'.format(len(team_hits)))
for rva, addr, term in team_hits[:20]:
    # Read 256 bytes to show context
    data = mem_read(hproc, addr, 256)
    if not data:
        continue
    print()
    print('  RVA+0x{:X} -> 0x{:X}  [contains "{}"]'.format(rva, addr, term))
    # Show small ints
    small = [(j, struct.unpack_from('<I', data, j)[0])
             for j in range(0, min(256, len(data))-3, 4)
             if 1 <= struct.unpack_from('<I', data, j)[0] <= 200]
    print('  Small ints (1-200): {}'.format(small[:10]))
    # Hex dump
    for row in range(0, min(128, len(data)), 16):
        chunk = data[row:row+16]
        h = ' '.join('{:02X}'.format(b) for b in chunk)
        asc = ''.join(chr(b) if 32<=b<127 else '.' for b in chunk)
        print('    +0x{:03X}: {}  {}'.format(row, h, asc))

# Also: look for pointer targets that themselves contain ~30-40 valid heap pointers
# (suggesting an array of 30-40 objects = one per team)
print()
print('=== SEARCHING FOR 30-40 ELEMENT ARRAYS ===')
for rva, addr in all_ptrs[:2000]:
    data4k = mem_read(hproc, addr, 4096)
    if not data4k:
        continue
    ptr_count = sum(1 for i in range(0, len(data4k)-7, 8)
                    if HEAP_MIN < struct.unpack_from('<Q', data4k, i)[0] < HEAP_MAX)
    if 28 <= ptr_count <= 45:
        print('  RVA+0x{:X} -> 0x{:X}  has {} heap pointers (likely team/player array)'.format(
            rva, addr, ptr_count))
        # Read further to count the array more precisely
        data_big = mem_read(hproc, addr, 4096)
        small32 = [(j, struct.unpack_from('<I', data_big, j)[0])
                   for j in range(0, len(data_big)-3, 4)
                   if 1 <= struct.unpack_from('<I', data_big, j)[0] <= 150]
        if small32:
            print('    Small ints (1-150): {}'.format(small32[:8]))

kernel32.CloseHandle(hproc)
