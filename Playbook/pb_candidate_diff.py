"""
Snap/diff only the clean playbook candidate locations.
Focuses on addresses where u32 = current playbook ID cleanly (not embedded in pointers).
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

def is_ptr(v):
    return ADDR_MIN < v < ADDR_MAX

# Get current playbook ID and object
entry = mem_read(hproc, module_base + 0x741F9E0, 16)
pb_id = entry[3]
pb_obj = struct.unpack_from('<Q', entry, 8)[0]
print('Current playbook ID={} obj=0x{:X}'.format(pb_id, pb_obj))

# Dynamically build candidate list from current team[0] state
t0data = mem_read(hproc, table_base, TEAM_STRIDE)

# Find pointer targets that have the EXACT playbook ID as a clean u32
# (i.e., context: [?? ?? pb 00 00 00 00 00] or similar isolated small int)
candidates = []

for off in range(0, TEAM_STRIDE - 7, 8):
    ptr = struct.unpack_from('<Q', t0data, off)[0]
    if not is_ptr(ptr):
        continue
    d = mem_read(hproc, ptr, 0x300)
    if not d:
        continue
    for i in range(0, len(d) - 3, 4):
        v = struct.unpack_from('<I', d, i)[0]
        if v == pb_id:
            # Check it's a clean isolated field (next 4 bytes should be 0 or small)
            if i + 8 <= len(d):
                next4 = struct.unpack_from('<I', d, i+4)[0]
                if next4 == 0 or next4 < 0x100:
                    candidates.append(('team[0]+{:04X}->{:X}+{:04X}'.format(off, ptr, i),
                                       ptr + i, 4))

# Also check the pointer-of-pointer targets around offset 0x1058-0x10B8
for team_off in range(0x1058, 0x10C0, 8):
    if team_off + 8 > TEAM_STRIDE:
        break
    ptr = struct.unpack_from('<Q', t0data, team_off)[0]
    if not is_ptr(ptr):
        continue
    d = mem_read(hproc, ptr, 0x200)
    if not d:
        continue
    # Check +0x168 specifically (found in scan)
    if 0x168 + 4 <= len(d):
        v = struct.unpack_from('<I', d, 0x168)[0]
        if v == pb_id or (v & 0xFF) == pb_id:
            candidates.append(('team[0]+{:04X}->{:X}+0168'.format(team_off, ptr),
                               ptr + 0x168, 4))

# Deduplicate by address
seen = set()
unique_cands = []
for label, addr, size in candidates:
    if addr not in seen:
        seen.add(addr)
        unique_cands.append((label, addr, size))

print('Found {} unique candidate addresses'.format(len(unique_cands)))
for label, addr, size in unique_cands[:30]:
    d = mem_read(hproc, addr, size)
    v = struct.unpack('<I', d[:4])[0] if d else 0
    print('  {} abs=0x{:X} val={}'.format(label, addr, v))

print()
print('=== SWITCH PLAYBOOK — 6 seconds ===')
for i in range(6, 0, -1):
    print('  {}...'.format(i))
    time.sleep(1.0)

# Re-read entry to confirm switch
entry2 = mem_read(hproc, module_base + 0x741F9E0, 16)
pb_id2 = entry2[3]
print('Post-switch playbook ID={}'.format(pb_id2))

if pb_id2 == pb_id:
    print('WARNING: playbook ID did not change! Did you switch?')

print('\n=== CANDIDATES THAT CHANGED ===')
changed = []
for label, addr, size in unique_cands:
    d = mem_read(hproc, addr, size)
    if not d:
        continue
    v = struct.unpack('<I', d[:4])[0]
    if v != pb_id:
        flag = '  *** NEW ID {} ***'.format(v) if v == pb_id2 else '  (changed to {})'.format(v)
        changed.append((label, addr, pb_id, v, flag))
        print('  CHANGED: {} abs=0x{:X}: {} -> {}{}'.format(label, addr, pb_id, v, flag))

if not changed:
    print('  None of the {} candidates changed!'.format(len(unique_cands)))
    print('  Trying deeper: re-reading all candidates vs original value...')
    # Show first 10 regardless
    for label, addr, size in unique_cands[:10]:
        d = mem_read(hproc, addr, 8)
        h = ' '.join('{:02X}'.format(b) for b in d) if d else '??'
        print('    {} : [{}]'.format(label, h))

kernel32.CloseHandle(hproc)
