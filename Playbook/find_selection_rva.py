"""
Find the "current playbook selection" field near the known static array.

RVA+0x6CCEFD0 holds [0, 24, 26, 28, 25, 27, 29] — the available playbook IDs
as u32 values. The game must store a selection index or the selected ID nearby.

This script diffs a 4KB window around that RVA before/after a playbook change,
then scans a wider area to find any u32 that transitions between known pb IDs.

Usage:
  1. Note current playbook (shown at start)
  2. Change to a different playbook in-game (use inject_playbook.py or game UI)
  3. Press Enter when ready for snap B
"""
import sys, struct, time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

STATIC_ARRAY_RVA = 0x6CCEFD0   # array of available playbook IDs
SCAN_RVA_START   = 0x6CC0000   # 64KB before the array
SCAN_RVA_END     = 0x6D40000   # 448KB total window

VOLATILE_RVAS = [0x741F9E0, 0x741FA08]

def read_entry():
    e = mem_read(hproc, module_base + 0x741F9E0, 16)
    if e:
        return e[3], struct.unpack_from('<Q', e, 8)[0]
    return None, None

# Show the static array first
print('=== STATIC ARRAY at RVA+0x{:X} ==='.format(STATIC_ARRAY_RVA))
arr_data = mem_read(hproc, module_base + STATIC_ARRAY_RVA, 64)
if arr_data:
    vals = [struct.unpack_from('<I', arr_data, i)[0] for i in range(0, 64, 4)]
    print('u32 values: {}'.format(vals[:16]))

cur_id, cur_obj = read_entry()
print('\nCurrent playbook: pb_id={} obj=0x{:X}'.format(cur_id, cur_obj))

# ── SNAP A ────────────────────────────────────────────────────────────────────
print('\nTaking snap A of 0x{:X}..0x{:X} ({} KB)...'.format(
    SCAN_RVA_START, SCAN_RVA_END, (SCAN_RVA_END - SCAN_RVA_START) // 1024))
snap_a = {}
for rva in range(SCAN_RVA_START, SCAN_RVA_END, 0x1000):
    d = mem_read(hproc, module_base + rva, 0x1000)
    if d:
        snap_a[rva] = bytes(d)
print('Snap A done. {} pages read.'.format(len(snap_a)))

# Also snap the volatile entries for reference
vol_a = {}
for vrva in VOLATILE_RVAS:
    e = mem_read(hproc, module_base + vrva, 16)
    vol_a[vrva] = bytes(e) if e else None

print('\nNow change the playbook in-game (use inject_playbook.py or game UI).')
print('Press Enter when the playbook has changed...')
input()

new_id, new_obj = read_entry()
print('New playbook: pb_id={} obj=0x{:X}'.format(new_id, new_obj))

if new_id == cur_id:
    print('WARNING: Playbook ID unchanged! Diffs will be noise only.')

# ── SNAP B ────────────────────────────────────────────────────────────────────
print('\nTaking snap B...')
snap_b = {}
for rva in range(SCAN_RVA_START, SCAN_RVA_END, 0x1000):
    d = mem_read(hproc, module_base + rva, 0x1000)
    if d:
        snap_b[rva] = bytes(d)

vol_b = {}
for vrva in VOLATILE_RVAS:
    e = mem_read(hproc, module_base + vrva, 16)
    vol_b[vrva] = bytes(e) if e else None

# ── DIFF ─────────────────────────────────────────────────────────────────────
print('\n=== DIFF RESULTS ({} -> {}) ==='.format(cur_id, new_id))

all_changes = []
for rva in sorted(snap_a.keys()):
    if rva not in snap_b:
        continue
    a = snap_a[rva]
    b = snap_b[rva]
    for i in range(0, min(len(a), len(b)) - 3, 1):
        if a[i] != b[i]:
            abs_rva = rva + i
            old_u32 = struct.unpack_from('<I', a, i)[0] if i + 4 <= len(a) else 0
            new_u32 = struct.unpack_from('<I', b, i)[0] if i + 4 <= len(b) else 0
            all_changes.append((abs_rva, a[i], b[i], old_u32, new_u32))

print('Total byte changes in scan region: {}'.format(len(all_changes)))

# Group into runs
if all_changes:
    by_rva = sorted(all_changes, key=lambda x: x[0])
    runs = [[by_rva[0]]]
    for item in by_rva[1:]:
        if item[0] == runs[-1][-1][0] + 1:
            runs[-1].append(item)
        else:
            runs.append([item])

    print('\n=== ALL CHANGES IN REGION ===')
    for run in runs[:100]:
        rva_off = run[0][0]
        old_bytes = bytes(x[1] for x in run)
        new_bytes = bytes(x[2] for x in run)
        old_u32 = run[0][3]
        new_u32 = run[0][4]
        flag = ''
        if old_u32 == cur_id or new_u32 == new_id:
            flag = '  *** EXACT PB ID MATCH ***'
        elif 1 <= old_u32 <= 60 and 1 <= new_u32 <= 60:
            flag = '  *** PLAYBOOK RANGE ***'
        old_h = ' '.join('{:02X}'.format(b) for b in old_bytes[:8])
        new_h = ' '.join('{:02X}'.format(b) for b in new_bytes[:8])
        dist = abs(rva_off - STATIC_ARRAY_RVA)
        print('  RVA+0x{:X} (dist={:+d} from array): [{}] -> [{}]  u32:{}->{} ({} bytes){}'.format(
            rva_off, rva_off - STATIC_ARRAY_RVA, old_h, new_h, old_u32, new_u32, len(run), flag))

# ── EXACT MATCHES ─────────────────────────────────────────────────────────────
exact = [(rva, o32, n32) for rva, ob, nb, o32, n32 in all_changes
         if (o32 == cur_id and n32 == new_id)]
if exact:
    print('\n=== EXACT ID TRANSITIONS ({} -> {}) ==='.format(cur_id, new_id))
    for rva, o32, n32 in exact:
        dist = rva - STATIC_ARRAY_RVA
        print('  RVA+0x{:X} (dist={:+d}): {} -> {}'.format(rva, dist, o32, n32))
else:
    print('\nNo exact {} -> {} transitions found.'.format(cur_id, new_id))

# ── CHECK NEAR STATIC ARRAY ───────────────────────────────────────────────────
print('\n=== STATIC ARRAY NEIGHBORS (±256 bytes) ===')
for delta in range(-256, 257, 4):
    rva_check = STATIC_ARRAY_RVA + delta
    page = (rva_check // 0x1000) * 0x1000
    off  = rva_check % 0x1000
    if page in snap_a and page in snap_b and off + 4 <= 0x1000:
        va = struct.unpack_from('<I', snap_a[page], off)[0]
        vb = struct.unpack_from('<I', snap_b[page], off)[0]
        if va != vb:
            print('  RVA+0x{:X} (array{:+d}): {} -> {}  u32: {} -> {}'.format(
                rva_check, delta,
                snap_a[page][off:off+4].hex(), snap_b[page][off:off+4].hex(),
                va, vb))

# ── VOLATILE ENTRY CHANGES ─────────────────────────────────────────────────────
print('\n=== VOLATILE ENTRY CHANGES ===')
for vrva in VOLATILE_RVAS:
    a = vol_a.get(vrva)
    b = vol_b.get(vrva)
    if a and b:
        print('  RVA+0x{:X}: {} -> {}'.format(vrva, a.hex(), b.hex()))

kernel32.CloseHandle(hproc)
