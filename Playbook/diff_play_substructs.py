"""
Follow every 0x127xxxxxxx pointer inside the playbook object and snap those
sub-structures before and after you add/remove ONE play via game UI.

The play list lives in one of those sub-objects. The diff will show exactly which
one and at what offset inside it.

Usage:
  1. Run this (snap A taken immediately — stay on the same playbook)
  2. In-game: press 2 (Select Play), add OR remove exactly one play, save with RET
  3. Press Enter — script takes snap B and diffs
"""
import sys, struct, ctypes, time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

VOLATILE_RVA = 0x741F9E0
OBJ_SIZE     = 0x5000   # read slightly more than 16KB to catch full structure

CATEGORY_NAMES = [
    '3 POINT', 'PICK & ROLL', 'ISOLATION', 'POST UP HIGH',
    'CUTTER', 'POST UP LOW', 'MID RANGE', 'GUARD POST', 'HANDOFF',
]

def read_entry():
    e = mem_read(hproc, module_base + VOLATILE_RVA, 16)
    if e:
        return e[3], struct.unpack_from('<Q', e, 8)[0]
    return None, None

pb_id, obj_addr = read_entry()
print('Playbook: pb_id={} obj=0x{:X}'.format(pb_id, obj_addr))

# Read playbook object
obj_data = mem_read(hproc, obj_addr, OBJ_SIZE)
if not obj_data:
    print('ERROR: cannot read playbook object')
    kernel32.CloseHandle(hproc)
    sys.exit(1)
obj_data = bytes(obj_data)
print('Read {} bytes from playbook object'.format(len(obj_data)))

# Extract all unique 0x127xxxxxxx pointers (heap sub-structures)
HEAP_MIN = 0x100000000
HEAP_MAX = 0x200000000

sub_ptrs = {}   # offset_in_obj -> target_addr
for i in range(0, len(obj_data) - 7, 8):
    lo = struct.unpack_from('<I', obj_data, i)[0]
    hi = struct.unpack_from('<I', obj_data, i+4)[0]
    v  = lo | (hi << 32)
    if HEAP_MIN <= v < HEAP_MAX:
        if v not in sub_ptrs.values():  # unique only
            sub_ptrs[i] = v

print('Found {} unique sub-structure pointers (0x127xxxxxxx):'.format(len(sub_ptrs)))
for off, addr in sorted(sub_ptrs.items()):
    print('  obj+0x{:04X} -> 0x{:X}'.format(off, addr))

# Snap function: read 512 bytes from each sub-struct pointer
READ_SIZE = 512
def snap_subs():
    snaps = {}
    for off, addr in sub_ptrs.items():
        d = mem_read(hproc, addr, READ_SIZE)
        snaps[addr] = bytes(d) if d else b''
    return snaps

print('\nTaking snap A of all {} sub-structures...'.format(len(sub_ptrs)))
snap_a = snap_subs()
pb_id_a = pb_id

print('\nIn-game: add OR remove ONE play (press 2 → Select Play → change one play → RET)')
print('Press Enter when done...')
input()

# Verify we are still on the same playbook
pb_id_b, obj_addr_b = read_entry()
if pb_id_b != pb_id_a:
    print('WARNING: Playbook changed! ({} -> {}) Re-reading object...'.format(pb_id_a, pb_id_b))
    obj_data = bytes(mem_read(hproc, obj_addr_b, OBJ_SIZE) or b'')

print('Taking snap B...')
snap_b = snap_subs()

# Diff
print('\n=== DIFF ===')
total_changed = 0
for addr in sorted(snap_a.keys()):
    a = snap_a[addr]
    b = snap_b.get(addr, b'')
    if not a or not b:
        continue
    diffs = [(i, a[i], b[i]) for i in range(min(len(a), len(b))) if a[i] != b[i]]
    if not diffs:
        continue
    total_changed += len(diffs)

    # Find which obj offset points here
    obj_off = next((o for o, p in sub_ptrs.items() if p == addr), 0)
    elem_idx = obj_off // 0x910
    print('\n  Sub-object 0x{:X} (obj+0x{:04X} = element {:d}):'.format(addr, obj_off, elem_idx))
    print('  {} bytes changed'.format(len(diffs)))

    # Group into runs
    runs = [[diffs[0]]]
    for item in diffs[1:]:
        if item[0] == runs[-1][-1][0] + 1:
            runs[-1].append(item)
        else:
            runs.append([item])

    for run in runs:
        off = run[0][0]
        n = len(run)
        old_bytes = bytes(x[1] for x in run)
        new_bytes = bytes(x[2] for x in run)
        oh = ' '.join('{:02X}'.format(v) for v in old_bytes[:16])
        nh = ' '.join('{:02X}'.format(v) for v in new_bytes[:16])
        old_u32s = [struct.unpack_from('<I', old_bytes, j)[0] for j in range(0, min(n, 32), 4) if j+4 <= n]
        new_u32s = [struct.unpack_from('<I', new_bytes, j)[0] for j in range(0, min(n, 32), 4) if j+4 <= n]
        flag = ''
        if n >= 120:
            flag = '  *** LARGE CHANGE - LIKELY PLAY ARRAY ***'
        elif any(1 <= v <= 9999 for v in old_u32s + new_u32s):
            flag = '  ** small-int field **'
        print('    +0x{:03X} ({} bytes): [{}] -> [{}]{}'.format(off, n, oh, nh, flag))
        if n >= 4:
            print('    u32: {} -> {}'.format(old_u32s[:8], new_u32s[:8]))

print('\nTotal bytes changed across all sub-objects: {}'.format(total_changed))

if total_changed == 0:
    print('\nNo changes found!')
    print('Possible causes:')
    print('  - Same playbook before/after (carousel switched then switched back)')
    print('  - The play list is in a region not pointed to by 0x127xxxxxxx pointers')
    print('  - Need to widen the heap range filter')

# Also re-snap the 16KB object itself for completeness
print('\nChecking 16KB object for changes...')
obj_b = bytes(mem_read(hproc, obj_addr, OBJ_SIZE) or b'')
obj_diffs = [(i, obj_data[i], obj_b[i]) for i in range(min(len(obj_data), len(obj_b))) if obj_data[i] != obj_b[i]]
print('  16KB object changed bytes: {}'.format(len(obj_diffs)))
for i, oa, nb in obj_diffs[:20]:
    print('  +0x{:04X}: {:02X} -> {:02X}  (element {})'.format(i, oa, nb, i // 0x910))

kernel32.CloseHandle(hproc)
