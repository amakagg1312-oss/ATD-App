"""
Follow pointer chains from team structs to find playbook assignment.
The team struct has 5672 bytes with many pointers. Let's follow the first
few pointers and look for playbook-related data (small ints that change with switch).

Also: scan for the VALUE 14 (=28/2) as potential playbook INDEX (vs the ID 28 we saw).
"""
import sys, struct, time
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

HEAP_MIN = 0x100000000
HEAP_MAX = 0xF00000000

# --- 1. Read full first pointer from each team and dump 256 bytes from there ---
print('\n=== Team struct pointer[0] targets (first 256 bytes) ===')
for idx in [0, 6, 10, 11, 12, 13, 14]:
    team_addr = table_base + idx * TEAM_STRIDE
    tdata = mem_read(hproc, team_addr, 32)
    if not tdata:
        continue
    ptr0 = struct.unpack_from('<Q', tdata, 0)[0]
    if not (HEAP_MIN < ptr0 < HEAP_MAX):
        print('  Team[{}]: ptr0=0x{:X} (not heap)'.format(idx, ptr0))
        continue
    # Read 256 bytes from ptr0
    d = mem_read(hproc, ptr0, 256)
    if not d:
        print('  Team[{}]: ptr0=0x{:X} (unreadable)'.format(idx, ptr0))
        continue
    # Find small ints (1-50) that could be playbook IDs
    small32 = [(j, struct.unpack_from('<I', d, j)[0]) for j in range(0, 252, 4)
               if 1 <= struct.unpack_from('<I', d, j)[0] <= 50]
    print('  Team[{}]: ptr0=0x{:X}  small u32 (1-50): {}'.format(idx, ptr0, small32[:8]))

# --- 2. Scan ALL of team struct's 5672 bytes for pointers and follow them ---
# Focus on team[0] (the 76ers / Nick Nurse's team)
print('\n=== Team[0] full pointer scan (5672 bytes, all heap pointers + 64 bytes each) ===')
t0data = mem_read(hproc, table_base, TEAM_STRIDE)
if t0data:
    found_ptrs = []
    for i in range(0, TEAM_STRIDE - 7, 8):
        val = struct.unpack_from('<Q', t0data, i)[0]
        if HEAP_MIN < val < HEAP_MAX:
            found_ptrs.append((i, val))
    print('  {} heap pointers in team[0]'.format(len(found_ptrs)))
    for off, ptr in found_ptrs[:60]:  # first 60 pointers
        # Read 64 bytes from each target
        d = mem_read(hproc, ptr, 64)
        if not d:
            continue
        small = [(j, struct.unpack_from('<I', d, j)[0]) for j in range(0, 60, 4)
                 if 1 <= struct.unpack_from('<I', d, j)[0] <= 50]
        if small:
            print('  +0x{:04X} -> 0x{:X}  small u32: {}'.format(off, ptr, small[:6]))

# --- 3. Check the RVA+0x7998xxx area more carefully ---
print('\n=== Context at RVA+0x7998D40 (256 bytes) ===')
d = mem_read(hproc, module_base + 0x7998D40, 256)
if d:
    for row in range(0, 256, 16):
        chunk = d[row:row+16]
        h = ' '.join('{:02X}'.format(b) for b in chunk)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print('  RVA+0x{:X}: {}  {}'.format(0x7998D40 + row, h, asc))

# --- 4. Look specifically at what's at the pointer referenced in the 0x741F9E0 entry ---
# Second u64 of entry at 0x741F9E0 was: 30 9F 97 30 00 00 00 00
# (was 40 97... before, changed to 30 97...)
# Actually let's re-read it fresh
entry_9E0 = mem_read(hproc, module_base + 0x741F9E0, 16)
if entry_9E0:
    u64_0 = struct.unpack_from('<Q', entry_9E0, 0)[0]
    u64_1 = struct.unpack_from('<Q', entry_9E0, 8)[0]
    print('\n=== Entry at RVA+0x741F9E0 (fresh read) ===')
    print('  u64[0]=0x{:X}  u64[1]=0x{:X}'.format(u64_0, u64_1))
    if HEAP_MIN < u64_0 < HEAP_MAX:
        d = mem_read(hproc, u64_0, 128)
        if d:
            print('  u64[0] target (128 bytes):')
            for row in range(0, 128, 16):
                chunk = d[row:row+16]
                h = ' '.join('{:02X}'.format(b) for b in chunk)
                asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                print('    +0x{:03X}: {}  {}'.format(row, h, asc))
    if HEAP_MIN < u64_1 < HEAP_MAX:
        d = mem_read(hproc, u64_1, 128)
        if d:
            print('  u64[1] target (128 bytes):')
            for row in range(0, 128, 16):
                chunk = d[row:row+16]
                h = ' '.join('{:02X}'.format(b) for b in chunk)
                asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                print('    +0x{:03X}: {}  {}'.format(row, h, asc))

# --- 5. Read the NEW 3 changing entries (0x741FA08, 0x741FAA8, 0x741FEB8) ---
print('\n=== New changing entries ===')
for rva in [0x741FA08, 0x741FAA8, 0x741FEB8]:
    d = mem_read(hproc, module_base + rva, 16)
    if d:
        h = ' '.join('{:02X}'.format(b) for b in d)
        u64_0 = struct.unpack_from('<Q', d, 0)[0]
        u64_1 = struct.unpack_from('<Q', d, 8)[0]
        print('  RVA+0x{:X}: {}  byte[3]={} u64[1]=0x{:X}'.format(
            rva, h, d[3], u64_1))

# --- 6. Let's also check stable_diff "persistent" area in 0x7998xxx more carefully ---
# Read 512 bytes around RVA+0x7998D00
print('\n=== Context at RVA+0x7998D00 (512 bytes) ===')
d = mem_read(hproc, module_base + 0x7998D00, 512)
if d:
    for row in range(0, 512, 16):
        chunk = d[row:row+16]
        h = ' '.join('{:02X}'.format(b) for b in chunk)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print('  RVA+0x{:X}: {}  {}'.format(0x7998D00 + row, h, asc))

kernel32.CloseHandle(hproc)
