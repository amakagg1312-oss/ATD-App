"""
Dense full snap of the 22MB .data section before/after a single playbook switch.
No noise filtering. Detects switch automatically via volatile entry poll.
Shows ALL bytes that changed, ranked by whether they look like playbook IDs.
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

SCAN_RVA_START = 0x7000000
SCAN_RVA_END   = 0x8600000  # 22MB
CHUNK_SIZE      = 0x10000   # 64KB chunks

def read_entry():
    e = mem_read(hproc, module_base + 0x741F9E0, 16)
    if e:
        return e[3], struct.unpack_from('<Q', e, 8)[0]
    return None, None

def snap_data():
    chunks = {}
    for rva in range(SCAN_RVA_START, SCAN_RVA_END, CHUNK_SIZE):
        d = mem_read(hproc, module_base + rva, CHUNK_SIZE)
        if d:
            chunks[rva] = bytes(d)
    return chunks

pb_id, pb_obj = read_entry()
print('Current: playbook={} obj=0x{:X}'.format(pb_id, pb_obj))
print('Taking snap A ({:.0f} KB)...'.format((SCAN_RVA_END - SCAN_RVA_START) / 1024))
t0 = time.time()
snap_a = snap_data()
print('Snap A done in {:.2f}s — waiting for playbook switch...'.format(time.time() - t0))

# Wait for playbook to change
prev_id = pb_id
while True:
    time.sleep(0.01)
    new_id, new_obj = read_entry()
    if new_id != prev_id:
        print('Switch detected: {} -> {}  obj: 0x{:X} -> 0x{:X}'.format(
            prev_id, new_id, pb_obj, new_obj))
        break

print('Taking snap B...')
t0 = time.time()
snap_b = snap_data()
print('Snap B done in {:.2f}s'.format(time.time() - t0))

print('\n=== ALL CHANGED BYTES ===')
# Known volatile entry RVAs to de-emphasize
VOLATILE_RVAS_SET = set([
    0x741F380, 0x741F4B0, 0x741F4D0, 0x741F510,
    0x741F520, 0x741F540, 0x741F550, 0x741F9E0,
    0x741FA08, 0x741FAA8, 0x741FEB8,
])

all_changes = []  # (abs_addr, old_byte, new_byte, rva)
for rva in sorted(snap_a.keys()):
    if rva not in snap_b:
        continue
    a = snap_a[rva]
    b = snap_b[rva]
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            abs_addr = module_base + rva + i
            all_changes.append((abs_addr, a[i], b[i], rva + i))

print('Total bytes changed: {}'.format(len(all_changes)))

# Separate: in volatile entries vs elsewhere
in_volatile = []
elsewhere = []
for abs_addr, old, new, rva_off in all_changes:
    # Find which volatile entry this belongs to (if any)
    is_v = False
    for vrva in VOLATILE_RVAS_SET:
        if abs(rva_off - vrva) < 16:
            is_v = True
            break
    if is_v:
        in_volatile.append((abs_addr, old, new, rva_off))
    else:
        elsewhere.append((abs_addr, old, new, rva_off))

print('  In volatile entries: {}'.format(len(in_volatile)))
print('  Elsewhere: {}'.format(len(elsewhere)))

# Show elsewhere changes
if elsewhere:
    # Group into runs
    elsewhere_sorted = sorted(elsewhere, key=lambda x: x[0])
    print('\n=== NON-VOLATILE CHANGES ===')

    # Group consecutive addresses
    runs = [[elsewhere_sorted[0]]]
    for item in elsewhere_sorted[1:]:
        if item[0] == runs[-1][-1][0] + 1:
            runs[-1].append(item)
        else:
            runs.append([item])

    for run in runs[:50]:
        abs_addr = run[0][0]
        rva_off = run[0][3]
        old_bytes = bytes(x[1] for x in run)
        new_bytes = bytes(x[2] for x in run)
        old_u32 = struct.unpack_from('<I', old_bytes.ljust(4, b'\x00'))[0]
        new_u32 = struct.unpack_from('<I', new_bytes.ljust(4, b'\x00'))[0]
        # Flag candidates: small integer change
        flag = ''
        if len(run) <= 4 and (1 <= old_u32 <= 60 or 1 <= new_u32 <= 60):
            flag = '  *** PLAYBOOK CANDIDATE ***'
        if len(run) <= 8 and (old_u32 in (new_id, prev_id) or new_u32 in (new_id, prev_id)):
            flag = '  *** EXACT ID MATCH ***'
        old_h = ' '.join('{:02X}'.format(b) for b in old_bytes[:8])
        new_h = ' '.join('{:02X}'.format(b) for b in new_bytes[:8])
        print('  RVA+0x{:X} (abs 0x{:X}): [{}] -> [{}]  u32:{}->{} ({} bytes){}'.format(
            rva_off, abs_addr, old_h, new_h, old_u32, new_u32, len(run), flag))
else:
    print('\nNo changes outside volatile entries!')
    print('=> The volatile entries ARE the only storage that changes.')

kernel32.CloseHandle(hproc)
