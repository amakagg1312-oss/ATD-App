"""
Playbook injector - discovers available playbooks and injects a selected one.

Usage:
  python inject_playbook.py discover   -- cycle through playbooks; saves mapping
  python inject_playbook.py inject <id> -- write playbook ID immediately
  python inject_playbook.py list        -- show saved mapping

The volatile entry u64[1] controls which playbook object the game uses.
Writing it alone is sufficient; byte[3] auto-updates from the object.
"""
import sys, struct, time, ctypes, json, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)

MAPPING_FILE = 'playbook_map.json'

# Both volatile entry addresses track the same playbook
VOLATILE_ADDRS_RVAS = [0x741F9E0, 0x741FA08]

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def read_entry(rva):
    e = mem_read(hproc, module_base + rva, 16)
    return bytes(e) if e else None

def write_u64(addr, value):
    data = struct.pack('<Q', value)
    buf = (ctypes.c_char * 8)(*data)
    written = ctypes.c_size_t(0)
    return kernel32.WriteProcessMemory(hproc, ctypes.c_ulonglong(addr),
                                       buf, 8, ctypes.byref(written))

def get_current():
    e = read_entry(VOLATILE_ADDRS_RVAS[0])
    if e:
        return e[3], struct.unpack_from('<Q', e, 8)[0]
    return None, None

def load_map():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE) as f:
            raw = json.load(f)
        return {int(k): v for k, v in raw.items()}
    return {}

def save_map(pb_map):
    with open(MAPPING_FILE, 'w') as f:
        json.dump({str(k): v for k, v in pb_map.items()}, f, indent=2)

cmd = sys.argv[1] if len(sys.argv) > 1 else 'discover'

# ─── DISCOVER ─────────────────────────────────────────────────────────────────
if cmd == 'discover':
    pb_map = load_map()
    pb_id, obj_addr = get_current()
    if pb_id:
        pb_map[pb_id] = obj_addr
        print('Current: pb_id={} obj=0x{:X}'.format(pb_id, obj_addr))

    print('\nCycle through ALL available playbooks in Edit Plays.')
    print('Discovery will stop after 60s with no new playbooks found.')
    print()

    prev_id = pb_id
    no_new_for = 0
    last_change = time.time()
    while time.time() - last_change < 60:
        time.sleep(0.05)
        new_id, new_obj = get_current()
        if new_id is None:
            continue
        if new_id != prev_id:
            if new_id not in pb_map:
                pb_map[new_id] = new_obj
                print('  NEW: pb_id={} obj=0x{:X}'.format(new_id, new_obj))
                last_change = time.time()
            else:
                print('  Seen: pb_id={}'.format(new_id))
            prev_id = new_id

    save_map(pb_map)
    print('\n=== DISCOVERED PLAYBOOKS ===')
    for pid_k in sorted(pb_map.keys()):
        print('  pb_id={:3d} (0x{:02X}) -> obj=0x{:X}'.format(pid_k, pid_k, pb_map[pid_k]))
    print('\nSaved to {}'.format(MAPPING_FILE))

# ─── LIST ─────────────────────────────────────────────────────────────────────
elif cmd == 'list':
    pb_map = load_map()
    pb_id, obj_addr = get_current()
    print('Current: pb_id={}'.format(pb_id))
    if not pb_map:
        print('No mapping saved. Run: python inject_playbook.py discover')
    else:
        for pid_k in sorted(pb_map.keys()):
            marker = ' <-- CURRENT' if pid_k == pb_id else ''
            print('  pb_id={:3d} (0x{:02X}) -> obj=0x{:X}{}'.format(
                pid_k, pid_k, pb_map[pid_k], marker))

# ─── INJECT ───────────────────────────────────────────────────────────────────
elif cmd == 'inject':
    if len(sys.argv) < 3:
        print('Usage: python inject_playbook.py inject <playbook_id>')
        kernel32.CloseHandle(hproc)
        sys.exit(1)

    target_id = int(sys.argv[2])
    pb_map = load_map()

    if target_id not in pb_map:
        print('Playbook {} not in saved map. Available: {}'.format(
            target_id, sorted(pb_map.keys())))
        print('Run discover first to build the map.')
        kernel32.CloseHandle(hproc)
        sys.exit(1)

    target_obj = pb_map[target_id]
    pb_id, cur_obj = get_current()
    print('Current pb_id={} obj=0x{:X}'.format(pb_id, cur_obj))
    print('Injecting pb_id={} obj=0x{:X}...'.format(target_id, target_obj))

    # Write u64[1] to both volatile entries
    ok = 0
    for rva in VOLATILE_ADDRS_RVAS:
        addr = module_base + rva
        if write_u64(addr + 8, target_obj):
            ok += 1

    time.sleep(0.01)
    new_id, new_obj = get_current()
    print('Result: pb_id={} obj=0x{:X} ({}/{} writes OK)'.format(
        new_id, new_obj, ok, len(VOLATILE_ADDRS_RVAS)))

    if new_id == target_id:
        print('SUCCESS! Playbook changed to {}'.format(target_id))
    else:
        print('FAILED: expected pb_id={} got {}'.format(target_id, new_id))

else:
    print('Commands: discover | list | inject <id>')

kernel32.CloseHandle(hproc)
