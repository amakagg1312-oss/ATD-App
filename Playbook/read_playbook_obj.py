"""
Read the playbook heap object in detail.
Focus on the three PLAYBOOK CANDIDATE offsets found in fast_watch2 diff.
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

ADDR_MIN = 0x10000
ADDR_MAX = 0x7FFFFFFFFFFF

# Get current u64[1] from the volatile entry
entry = mem_read(hproc, module_base + 0x741F9E0, 16)
u64_0 = struct.unpack_from('<Q', entry, 0)[0]
u64_1 = struct.unpack_from('<Q', entry, 8)[0]
byte3 = entry[3]
print('Volatile entry RVA+0x741F9E0: byte[3]={} u64[0]=0x{:X} u64[1]=0x{:X}'.format(
    byte3, u64_0, u64_1))

# Use the snap object addr (from last diff) - also check current u64[1]
OBJ_BASE = u64_1  # current live object
if OBJ_BASE < ADDR_MIN or OBJ_BASE > ADDR_MAX:
    print('u64[1] not valid, using hardcoded 0x127714770')
    OBJ_BASE = 0x127714770

print('Object base: 0x{:X}'.format(OBJ_BASE))

# Read the full object (first 16KB to cover all offsets we saw: max was +0x33B0)
obj_data = mem_read(hproc, OBJ_BASE, 0x4000)
if not obj_data:
    print('Cannot read object!'); kernel32.CloseHandle(hproc); sys.exit(1)
print('Read {:,} bytes from object'.format(len(obj_data)))

# --- 1. Show the three candidate sections (±128 bytes each) ---
CANDIDATE_OFFS = [0x1370, 0x21F0, 0x2760]
for grp, base_off in enumerate(CANDIDATE_OFFS):
    print('\n=== Group {} (base +0x{:X}) ==='.format(grp+1, base_off))
    for row_off in range(0, 0x100, 16):
        abs_off = base_off + row_off
        if abs_off + 16 > len(obj_data):
            break
        chunk = obj_data[abs_off:abs_off+16]
        h = ' '.join('{:02X}'.format(b) for b in chunk)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        markers = []
        for i in range(16):
            rva_off = base_off + row_off + i
            if rva_off in [0x13F0, 0x2270, 0x27E0]:
                markers.append('+0x{:X}=CANDIDATE'.format(i))
        print('  obj+0x{:04X}: {}  {}  {}'.format(abs_off, h.ljust(47), asc, ' '.join(markers)))

# --- 2. Look for small ints (1-40) throughout the entire object ---
print('\n=== All u32 values 1-40 in object ===')
for i in range(0, min(len(obj_data)-3, 0x4000), 4):
    v = struct.unpack_from('<I', obj_data, i)[0]
    if 1 <= v <= 40:
        print('  obj+0x{:04X}: u32={}'.format(i, v))

# --- 3. Look for pointers to the team table area ---
print('\n=== Pointers near team_table in object ===')
for i in range(0, min(len(obj_data)-7, 0x4000), 8):
    v = struct.unpack_from('<Q', obj_data, i)[0]
    if abs(v - table_base) < 0x1000000:  # within 16MB of team table
        print('  obj+0x{:04X}: 0x{:X} (offset from team_table: {:+d})'.format(
            i, v, v - table_base))

# --- 4. Also check ALL 11 volatile entries - show current byte[3] ---
VOLATILE_RVAS = [
    0x741F380, 0x741F4B0, 0x741F4D0, 0x741F510,
    0x741F520, 0x741F540, 0x741F550, 0x741F9E0,
    0x741FA08, 0x741FAA8, 0x741FEB8,
]
print('\n=== Current volatile entry state ===')
for rva in VOLATILE_RVAS:
    e = mem_read(hproc, module_base + rva, 16)
    if e:
        b3 = e[3]
        u1 = struct.unpack_from('<Q', e, 8)[0]
        print('  RVA+0x{:X}: byte[3]={} u64[1]=0x{:X}'.format(rva, b3, u1))

# --- 5. Snap this object and wait for user to switch, then diff inline ---
print('\n=== Taking live baseline of object (re-read) ===')
snap_a = mem_read(hproc, OBJ_BASE, 0x4000)
print('NOW SWITCH PLAYBOOK, then press Enter...')
input()

snap_b = mem_read(hproc, OBJ_BASE, 0x4000)
mn = min(len(snap_a), len(snap_b))
diffs = [(i, snap_a[i], snap_b[i]) for i in range(mn) if snap_a[i] != snap_b[i]]
print('{} bytes changed in the object:'.format(len(diffs)))
for i, old, new in diffs[:30]:
    raw_a = snap_a[i:i+4].ljust(4, b'\x00')
    raw_b = snap_b[i:i+4].ljust(4, b'\x00')
    u32_a = struct.unpack('<I', raw_a[:4])[0]
    u32_b = struct.unpack('<I', raw_b[:4])[0]
    flag = '  *** CANDIDATE ***' if (1 <= old <= 60 or 1 <= new <= 60) else ''
    print('  obj+0x{:04X} (abs 0x{:X}): {} -> {}  u32: {} -> {}{}'.format(
        i, OBJ_BASE + i, old, new, u32_a, u32_b, flag))

kernel32.CloseHandle(hproc)
