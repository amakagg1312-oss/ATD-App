"""
Snap the full team table (all 42 teams * 5672 bytes) + the volatile entries,
then diff after a playbook switch. The authoritative playbook ID must be
in the team struct or in a struct directly pointed to by the team struct.

Also snaps objects pointed-to by ALL team struct pointers (shallow: first 256 bytes).
"""
import sys, struct, time, json, os
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

ADDR_MIN = 0x10000
ADDR_MAX = 0x7FFFFFFFFFFF
NUM_TEAMS = 42
SNAP_FILE = 'team_pb_snap.json'

def is_ptr(v):
    return ADDR_MIN < v < ADDR_MAX

def snap_teams():
    data = {}
    # All team structs
    full = mem_read(hproc, table_base, TEAM_STRIDE * NUM_TEAMS)
    if full:
        data['teams'] = full.hex()
    # Current volatile entry u64[1] objects
    for rva in [0x741F9E0, 0x741FA08]:
        entry = mem_read(hproc, module_base + rva, 16)
        if entry:
            u64_1 = struct.unpack_from('<Q', entry, 8)[0]
            data['entry_{:X}_raw'.format(rva)] = entry.hex()
            if is_ptr(u64_1):
                obj = mem_read(hproc, u64_1, 0x400)
                if obj:
                    data['entry_{:X}_obj'.format(rva)] = (hex(u64_1), obj.hex())
    return data

cmd = sys.argv[1] if len(sys.argv) > 1 else 'run'

if cmd == 'snap':
    s = snap_teams()
    with open(SNAP_FILE, 'w') as f:
        json.dump(s, f)
    print('Snapped. Now switch playbook, then run: python team_playbook_diff.py diff')
    kernel32.CloseHandle(hproc)
    sys.exit(0)

if cmd == 'diff':
    if not os.path.exists(SNAP_FILE):
        print('Run snap first.'); kernel32.CloseHandle(hproc); sys.exit(1)
    with open(SNAP_FILE) as f:
        saved = json.load(f)
    snap_b = snap_teams()

    # Diff teams block
    if 'teams' in saved and 'teams' in snap_b:
        a = bytes.fromhex(saved['teams'])
        b = bytes.fromhex(snap_b['teams'])
        mn = min(len(a), len(b))
        diffs = [(i, a[i], b[i]) for i in range(mn) if a[i] != b[i]]
        print('{} bytes changed in team table ({} teams * {} bytes)'.format(
            len(diffs), NUM_TEAMS, TEAM_STRIDE))
        for i, old, new in diffs[:60]:
            team_idx = i // TEAM_STRIDE
            off_in_team = i % TEAM_STRIDE
            raw_a = a[i:i+4].ljust(4, b'\x00')
            raw_b = b[i:i+4].ljust(4, b'\x00')
            u32_a = struct.unpack('<I', raw_a[:4])[0]
            u32_b = struct.unpack('<I', raw_b[:4])[0]
            flag = ''
            if (1 <= old <= 60 or 1 <= new <= 60):
                flag = '  *** PLAYBOOK CANDIDATE ***'
            print('  team[{}]+0x{:04X} (abs 0x{:X}): {} -> {}  u32:{}->{}{}'.format(
                team_idx, off_in_team, table_base + i, old, new, u32_a, u32_b, flag))

    kernel32.CloseHandle(hproc)
    sys.exit(0)

# Default 'run': timed snap+diff inline
print('Snapping baseline (team structs + volatile obj entries)...')
snap_a = snap_teams()

# Show current state
if 'teams' in snap_a:
    t0 = bytes.fromhex(snap_a['teams'])
    pb_vals = []
    for idx in range(min(8, NUM_TEAMS)):
        chunk = t0[idx*TEAM_STRIDE:(idx+1)*TEAM_STRIDE]
        # Look for values 1-60 in first 0x80 bytes (likely identity/config fields)
        for off in range(0, min(0x80, len(chunk)-3), 4):
            v = struct.unpack_from('<I', chunk, off)[0]
            if 1 <= v <= 60:
                pb_vals.append('team[{}]+0x{:02X}={}'.format(idx, off, v))
    if pb_vals:
        print('Small values (1-60) in first 0x80 of first 8 teams: {}'.format(pb_vals[:12]))

print()
print('=== SWITCH THE PLAYBOOK NOW — you have 6 seconds ===')
for i in range(6, 0, -1):
    print('  {}...'.format(i))
    time.sleep(1.0)

print('Reading post-switch state...')
snap_b = snap_teams()

print('\n=== TEAM TABLE DIFF ===')
if 'teams' in snap_a and 'teams' in snap_b:
    a = bytes.fromhex(snap_a['teams'])
    b = bytes.fromhex(snap_b['teams'])
    mn = min(len(a), len(b))
    diffs = [(i, a[i], b[i]) for i in range(mn) if a[i] != b[i]]
    print('{} bytes changed'.format(len(diffs)))
    for i, old, new in diffs[:80]:
        team_idx = i // TEAM_STRIDE
        off_in_team = i % TEAM_STRIDE
        raw_a = a[i:i+4].ljust(4, b'\x00')
        raw_b = b[i:i+4].ljust(4, b'\x00')
        u32_a = struct.unpack('<I', raw_a[:4])[0]
        u32_b = struct.unpack('<I', raw_b[:4])[0]
        flag = ''
        if (1 <= old <= 60 or 1 <= new <= 60):
            flag = '  *** PLAYBOOK CANDIDATE ***'
        print('  team[{}]+0x{:04X} (abs 0x{:X}): {} -> {}  u32:{}->{}{}'.format(
            team_idx, off_in_team, table_base + i, old, new, u32_a, u32_b, flag))

kernel32.CloseHandle(hproc)
