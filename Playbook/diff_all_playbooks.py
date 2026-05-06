"""
Snap ALL known playbook objects (using fixed addresses from playbook_map.json)
before and after you add/remove one play. Bypasses the carousel problem entirely.

The modified playbook object will be the one with changes.
"""
import sys, struct, time, json, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

# Look for map next to this script first, then cwd
_here = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = next(
    (p for p in [os.path.join(_here, 'playbook_map.json'), 'playbook_map.json']
     if os.path.exists(p)),
    'playbook_map.json'
)
OBJ_SIZE  = 0x5000   # read 20KB (object may extend beyond 16KB)
SUB_SIZE  = 512      # bytes to read from each sub-pointer target
HEAP_MIN  = 0x100000000
HEAP_MAX  = 0x200000000

# Load known playbook addresses
if not os.path.exists(MAP_FILE):
    print('ERROR: {} not found. Run inject_playbook.py discover first.'.format(MAP_FILE))
    kernel32.CloseHandle(hproc)
    sys.exit(1)

with open(MAP_FILE) as f:
    raw = json.load(f)
pb_map = {int(k): v for k, v in raw.items()}
print('Loaded {} playbooks: {}'.format(len(pb_map), sorted(pb_map.keys())))

def get_sub_ptrs(obj_data):
    """Extract unique 0x127xxxxxxx pointer targets from a playbook object."""
    ptrs = {}
    for i in range(0, len(obj_data) - 7, 8):
        lo = struct.unpack_from('<I', obj_data, i)[0]
        hi = struct.unpack_from('<I', obj_data, i+4)[0]
        v  = lo | (hi << 32)
        if HEAP_MIN <= v < HEAP_MAX:
            ptrs[v] = i  # target -> offset_in_object (last occurrence wins)
    return ptrs

def snap_all():
    """Snap every known playbook object + all its sub-pointers."""
    result = {}
    for pb_id, obj_addr in pb_map.items():
        obj_data = mem_read(hproc, obj_addr, OBJ_SIZE)
        obj_bytes = bytes(obj_data) if obj_data else b''
        sub_snaps = {}
        if obj_bytes:
            sub_ptrs = get_sub_ptrs(obj_bytes)
            for sub_addr in sub_ptrs:
                d = mem_read(hproc, sub_addr, SUB_SIZE)
                sub_snaps[sub_addr] = bytes(d) if d else b''
        result[pb_id] = {'obj': obj_bytes, 'subs': sub_snaps, 'addr': obj_addr}
    return result

print('\nTaking snap A of all {} playbook objects + sub-structures...'.format(len(pb_map)))
snap_a = snap_all()
for pb_id, d in sorted(snap_a.items()):
    print('  pb{}: obj={}B, {} sub-structs'.format(pb_id, len(d['obj']), len(d['subs'])))

print('\nIn-game: add OR remove EXACTLY ONE play from the 76ers playbook')
print('(press 2 → Select Play → toggle one play → RET to save)')
print('\nPress Enter when done...')
input()

print('Taking snap B...')
snap_b = snap_all()

# ── DIFF ─────────────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('DIFF RESULTS')
print('='*60)

found_change = False
for pb_id in sorted(pb_map.keys()):
    a = snap_a[pb_id]
    b = snap_b[pb_id]
    obj_addr = a['addr']

    # Diff the 16KB object
    obj_a = a['obj']
    obj_b = b['obj']
    obj_diffs = [(i, obj_a[i], obj_b[i])
                 for i in range(min(len(obj_a), len(obj_b)))
                 if obj_a[i] != obj_b[i]]

    # Diff sub-structures
    sub_changes = {}
    all_sub_addrs = set(a['subs'].keys()) | set(b['subs'].keys())
    for sub_addr in sorted(all_sub_addrs):
        sa = a['subs'].get(sub_addr, b'')
        sb = b['subs'].get(sub_addr, b'')
        diffs = [(i, sa[i], sb[i])
                 for i in range(min(len(sa), len(sb)))
                 if sa[i] != sb[i]]
        if diffs:
            sub_changes[sub_addr] = diffs

    if not obj_diffs and not sub_changes:
        print('\npb{} (0x{:X}): NO CHANGES'.format(pb_id, obj_addr))
        continue

    found_change = True
    print('\n>>> pb{} (0x{:X}): CHANGED <<<'.format(pb_id, obj_addr))
    print('  Object bytes changed: {}'.format(len(obj_diffs)))
    print('  Sub-structs with changes: {}'.format(len(sub_changes)))

    # Show interesting object changes
    if obj_diffs:
        # Group into runs
        runs = [[obj_diffs[0]]]
        for item in obj_diffs[1:]:
            if item[0] == runs[-1][-1][0] + 1: runs[-1].append(item)
            else: runs.append([item])

        print('\n  --- Object changes ---')
        for run in runs[:20]:
            off = run[0][0]
            n   = len(run)
            ob  = bytes(x[1] for x in run)
            nb  = bytes(x[2] for x in run)
            oh  = ' '.join('{:02X}'.format(v) for v in ob[:12])
            nh  = ' '.join('{:02X}'.format(v) for v in nb[:12])
            ou8 = ob[0]; nu8 = nb[0]
            ou16 = struct.unpack_from('<H', ob, 0)[0] if n >= 2 else 0
            nu16 = struct.unpack_from('<H', nb, 0)[0] if n >= 2 else 0
            ou32 = struct.unpack_from('<I', ob, 0)[0] if n >= 4 else 0
            nu32 = struct.unpack_from('<I', nb, 0)[0] if n >= 4 else 0
            flag = ''
            if abs(ou8 - nu8) <= 3 and ou8 in range(50, 70): flag = '  *** PLAY COUNT? ***'
            elif abs(ou32 - nu32) == 1 and ou32 in range(50, 70): flag = '  *** PLAY COUNT (u32)? ***'
            elif n >= 120: flag = '  *** LARGE CHANGE - PLAY ARRAY? ***'
            elem = off // 0x910
            print('    obj+0x{:04X} (elem {}): {}B  [{}] -> [{}]  u8:{}->{} u16:{}->{} u32:{}->{}{}'.format(
                off, elem, n, oh, nh, ou8, nu8, ou16, nu16, ou32, nu32, flag))

    # Show sub-struct changes
    if sub_changes:
        print('\n  --- Sub-structure changes ---')
        for sub_addr, diffs in sorted(sub_changes.items()):
            # Find which offset in the object points to this sub
            obj_off = a['subs'].get(sub_addr, None)
            runs = [[diffs[0]]]
            for item in diffs[1:]:
                if item[0] == runs[-1][-1][0] + 1: runs[-1].append(item)
                else: runs.append([item])

            print('\n  Sub 0x{:X} ({} bytes changed, {} runs):'.format(
                sub_addr, len(diffs), len(runs)))
            for run in runs[:10]:
                off = run[0][0]
                n   = len(run)
                ob  = bytes(x[1] for x in run)
                nb  = bytes(x[2] for x in run)
                oh  = ' '.join('{:02X}'.format(v) for v in ob[:16])
                nh  = ' '.join('{:02X}'.format(v) for v in nb[:16])
                ou32s = [struct.unpack_from('<I', ob, j)[0] for j in range(0, min(n,64), 4) if j+4 <= n]
                nu32s = [struct.unpack_from('<I', nb, j)[0] for j in range(0, min(n,64), 4) if j+4 <= n]
                flag = ''
                if n >= 120: flag = '  *** LARGE = PLAY ARRAY ***'
                elif any(1 <= v <= 9999 for v in ou32s + nu32s): flag = '  (small ints)'
                print('    sub+0x{:03X}: {}B [{}] -> [{}]{}'.format(off, n, oh, nh, flag))
                if n >= 4:
                    print('    u32: {} -> {}'.format(ou32s[:8], nu32s[:8]))

if not found_change:
    print('\nNO CHANGES in any playbook object or sub-structure!')
    print('The play list may be in a different heap range.')
    print('Try widening HEAP_MIN/HEAP_MAX or check 0x362Cxxxx range.')

kernel32.CloseHandle(hproc)
