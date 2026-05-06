"""
Map playbook ID -> heap object address by cycling through all playbooks.
Polls for 90 seconds; user cycles through all playbooks during that time.
Then searches for a pointer table containing all object addresses.
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

ADDR_MIN = 0x10000
ADDR_MAX = 0x7FFFFFFFFFFF

def read_entry():
    e = mem_read(hproc, module_base + 0x741F9E0, 16)
    if e:
        return e[3], struct.unpack_from('<Q', e, 8)[0]
    return None, None

pb_map = {}  # pb_id -> obj_addr

pb_id, obj_addr = read_entry()
prev_id = pb_id
pb_map[pb_id] = obj_addr
print('Start: playbook={} obj=0x{:X}'.format(pb_id, obj_addr))
print('Cycle through ALL available playbooks in the next 90 seconds...')
print()

deadline = time.time() + 90
while time.time() < deadline:
    time.sleep(0.05)
    new_id, new_obj = read_entry()
    if new_id is None:
        continue
    if new_id != prev_id:
        pb_map[new_id] = new_obj
        elapsed = int(90 - (deadline - time.time()))
        print('  [{}s] Playbook {} -> obj=0x{:X}   ({} unique so far)'.format(
            elapsed, new_id, new_obj, len(pb_map)))
        prev_id = new_id
    remaining = int(deadline - time.time())
    if remaining % 10 == 0 and remaining > 0:
        import datetime
        pass  # don't spam

print('\n=== PLAYBOOK MAP ({} entries) ==='.format(len(pb_map)))
for pb_id_k in sorted(pb_map.keys()):
    print('  pb_id={:3d} (0x{:02X}) -> obj=0x{:X}'.format(pb_id_k, pb_id_k, pb_map[pb_id_k]))

all_objs = list(pb_map.values())
if len(all_objs) < 2:
    print('Not enough playbooks mapped.')
    kernel32.CloseHandle(hproc)
    sys.exit(1)

print('\n=== Searching module .data for pointer table ===')
print('(searching for addresses that reference multiple playbook objects...)')

# Search module .data (8KB chunks) for any known playbook object addresses
ref_locations = {}  # abs_addr_in_module -> list of pb_objs referenced there
for target in all_objs:
    target_bytes = struct.pack('<Q', target)
    for rva in range(0x6000000, 0x9000000, 0x10000):
        chunk = mem_read(hproc, module_base + rva, 0x10000)
        if not chunk:
            continue
        for i in range(0, len(chunk)-7, 8):
            if bytes(chunk[i:i+8]) == target_bytes:
                abs_addr = module_base + rva + i
                if abs_addr not in ref_locations:
                    ref_locations[abs_addr] = []
                ref_locations[abs_addr].append(target)

print('Total reference locations found: {}'.format(len(ref_locations)))
sorted_refs = sorted(ref_locations.keys())

# Show all references and cluster them
if sorted_refs:
    clusters = [[sorted_refs[0]]]
    for addr in sorted_refs[1:]:
        if addr - clusters[-1][-1] < 0x2000:
            clusters[-1].append(addr)
        else:
            clusters.append([addr])
    print('\nReference clusters:')
    for cluster in sorted(clusters, key=lambda c: -len(c)):
        base_rva = cluster[0] - module_base
        print('  Cluster @ RVA+0x{:X}: {} references'.format(base_rva, len(cluster)))
        for addr in cluster[:8]:
            pb_objs = ref_locations[addr]
            pb_ids = [k for k, v in pb_map.items() if v in pb_objs]
            print('    abs=0x{:X} RVA+0x{:X} -> pb_ids={}'.format(
                addr, addr - module_base, pb_ids))

kernel32.CloseHandle(hproc)
