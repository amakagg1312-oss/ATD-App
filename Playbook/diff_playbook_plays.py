"""
Diff the playbook heap object before and after you add/remove a play via game UI.

This finds EXACTLY where in the 16KB object the play list is stored.

Usage:
  1. Run this script (snap A taken immediately)
  2. In-game: press 2 (Select Play) and ADD or REMOVE one play
  3. Press Enter — snap B is taken and diffed
"""
import sys, struct, time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

VOLATILE_RVA = 0x741F9E0
OBJ_SIZE = 0x4000  # 16KB

def read_entry():
    e = mem_read(hproc, module_base + VOLATILE_RVA, 16)
    if e:
        return e[3], struct.unpack_from('<Q', e, 8)[0]
    return None, None

pb_id, obj_addr = read_entry()
print('Playbook: pb_id={} obj=0x{:X}'.format(pb_id, obj_addr))

# ── SNAP A ────────────────────────────────────────────────────────────────────
snap_a = mem_read(hproc, obj_addr, OBJ_SIZE)
if not snap_a:
    print('ERROR: cannot read object')
    kernel32.CloseHandle(hproc)
    sys.exit(1)
snap_a = bytes(snap_a)
print('Snap A taken ({} bytes). Play count field hunt...'.format(len(snap_a)))

# Show candidate play count locations BEFORE change
for i in range(0, len(snap_a) - 3, 1):
    v8 = snap_a[i]
    if v8 == 60:
        print('  u8==60 at +0x{:X}'.format(i))

print()
print('In-game: add or remove ONE play using "2 Select Play"')
print('Press Enter when done...')
input()

# ── SNAP B ────────────────────────────────────────────────────────────────────
# Re-read the object address (might have moved if carousel switched)
pb_id2, obj_addr2 = read_entry()
if obj_addr2 != obj_addr:
    print('WARNING: object address changed (0x{:X} -> 0x{:X})'.format(obj_addr, obj_addr2))
    print('Reading from new address.')
    obj_addr = obj_addr2

snap_b = mem_read(hproc, obj_addr, OBJ_SIZE)
if not snap_b:
    print('ERROR: cannot read object for snap B')
    kernel32.CloseHandle(hproc)
    sys.exit(1)
snap_b = bytes(snap_b)
print('Snap B taken. Diffing...\n')

# ── DIFF ─────────────────────────────────────────────────────────────────────
diffs = [(i, snap_a[i], snap_b[i]) for i in range(min(len(snap_a), len(snap_b)))
         if snap_a[i] != snap_b[i]]

print('Total bytes changed: {}'.format(len(diffs)))

if not diffs:
    print('No changes detected!')
    print('  - Make sure you are looking at the SAME playbook object')
    print('  - The carousel may have switched to a different playbook between snaps')
    kernel32.CloseHandle(hproc)
    sys.exit(0)

# Group into runs
runs = [[diffs[0]]]
for item in diffs[1:]:
    if item[0] == runs[-1][-1][0] + 1:
        runs[-1].append(item)
    else:
        runs.append([item])

print('Changed runs: {}\n'.format(len(runs)))

print('=== ALL CHANGED RUNS ===')
for run in runs:
    off = run[0][0]
    old_bytes = bytes(x[1] for x in run)
    new_bytes = bytes(x[2] for x in run)
    n = len(run)

    old_h = ' '.join('{:02X}'.format(b) for b in old_bytes[:16])
    new_h = ' '.join('{:02X}'.format(b) for b in new_bytes[:16])

    # Interpret as u16/u32 arrays
    old_u16 = [struct.unpack_from('<H', old_bytes, j)[0] for j in range(0, n-1, 2)]
    new_u16 = [struct.unpack_from('<H', new_bytes, j)[0] for j in range(0, n-1, 2)]
    old_u32 = [struct.unpack_from('<I', old_bytes, j)[0] for j in range(0, n-3, 4)]
    new_u32 = [struct.unpack_from('<I', new_bytes, j)[0] for j in range(0, n-3, 4)]

    notes = []
    # Is one value 60 and the other 59/61? → play count
    for v in old_u8 if (old_u8 := [snap_a[off+k] for k in range(n)]) else []:
        pass
    old_u8_vals = [snap_a[off+k] for k in range(n)]
    new_u8_vals = [snap_b[off+k] for k in range(n)]
    if 60 in old_u8_vals or 59 in old_u8_vals or 61 in old_u8_vals:
        notes.append('PLAY COUNT CANDIDATE (u8 near 60)')
    for v32 in old_u32 + new_u32:
        if v32 in (59, 60, 61):
            notes.append('PLAY COUNT CANDIDATE (u32)')
    for v16 in old_u16 + new_u16:
        if v16 in (59, 60, 61):
            notes.append('PLAY COUNT CANDIDATE (u16)')

    note_str = '  *** {} ***'.format('; '.join(notes)) if notes else ''
    print('+0x{:04X} ({} bytes):  [{}] -> [{}]{}'.format(off, n, old_h, new_h, note_str))
    if n > 1:
        if old_u32 != new_u32:
            print('  u32: {} -> {}'.format(old_u32[:8], new_u32[:8]))
        if old_u16 != new_u16:
            print('  u16: {} -> {}'.format(old_u16[:10], new_u16[:10]))

# ── FOCUSED: find the play array offset ───────────────────────────────────────
print('\n=== OFFSET SUMMARY (likely fields) ===')
for run in runs:
    off = run[0][0]
    n = len(run)
    old_u32 = struct.unpack_from('<I', snap_a, off)[0] if off+4 <= len(snap_a) else 0
    new_u32 = struct.unpack_from('<I', snap_b, off)[0] if off+4 <= len(snap_b) else 0
    old_u16 = struct.unpack_from('<H', snap_a, off)[0] if off+2 <= len(snap_a) else 0
    new_u16 = struct.unpack_from('<H', snap_b, off)[0] if off+2 <= len(snap_b) else 0
    desc = ''
    if abs(old_u32 - new_u32) == 1 and old_u32 in range(50, 70):
        desc = 'PLAY COUNT (u32: {} -> {})'.format(old_u32, new_u32)
    elif abs(old_u16 - new_u16) == 1 and old_u16 in range(50, 70):
        desc = 'PLAY COUNT (u16: {} -> {})'.format(old_u16, new_u16)
    elif n >= 2 and n <= 4:
        desc = 'small field ({} bytes)'.format(n)
    elif n >= 60:
        desc = 'LARGE CHANGE ({} bytes) - could be play array'.format(n)
    print('  +0x{:04X}: {} bytes  u32: {} -> {}  u16: {} -> {}  {}'.format(
        off, n, old_u32, new_u32, old_u16, new_u16, desc))

# Save both snaps
with open('pb_snap_a.bin', 'wb') as f: f.write(snap_a)
with open('pb_snap_b.bin', 'wb') as f: f.write(snap_b)
print('\nSaved pb_snap_a.bin and pb_snap_b.bin for offline analysis')

kernel32.CloseHandle(hproc)
