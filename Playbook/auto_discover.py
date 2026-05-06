"""
Auto-discover all available playbook objects by scanning heap near the current one.
Playbook objects have a characteristic structure:
  - 16KB size (~0x4000 bytes)
  - Playbook ID at object+0x0173 (u8, range 1-60)
  - Same ID at object+0x019B

No manual cycling required.
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

def read_entry_rva(rva):
    e = mem_read(hproc, module_base + rva, 16)
    return bytes(e) if e else None

def is_playbook_object(obj_data):
    """Check if 16KB of data looks like a playbook object."""
    if len(obj_data) < 0x200:
        return False, 0
    # Check playbook ID at +0x0173 (must be 1-60)
    id1 = obj_data[0x173]
    if not (1 <= id1 <= 60):
        return False, 0
    # Cross-check at +0x019B
    id2 = obj_data[0x19B]
    if id1 != id2:
        return False, 0
    # The IDs should be even (2K playbook IDs are typically even: 2,4,...,60)
    # Extra confidence: check u32 at +0x0173 = id (next bytes should be 0)
    u32_at_173 = struct.unpack_from('<I', obj_data, 0x173)[0]
    if u32_at_173 & 0xFFFFFF00 != 0:  # high bytes should be 0
        return False, 0
    return True, id1

# Get current playbook state
e = read_entry_rva(0x741F9E0)
cur_id = e[3] if e else None
cur_obj = struct.unpack_from('<Q', e, 8)[0] if e else 0
print('Current: pb_id={} obj=0x{:X}'.format(cur_id, cur_obj))

if not (ADDR_MIN < cur_obj < ADDR_MAX):
    print('Invalid current object address. Are you in Edit Plays?')
    kernel32.CloseHandle(hproc)
    sys.exit(1)

# Scan the heap region near the current object for other playbook objects
# Try two strategies: 1) fixed stride scan, 2) object-size-aligned scan
found = {}
found[cur_id] = cur_obj

# Read current object to confirm structure
cur_data = mem_read(hproc, cur_obj, 0x4000)
if cur_data:
    ok, detected_id = is_playbook_object(cur_data)
    print('Current object self-check: ok={} detected_id={}'.format(ok, detected_id))

# Strategy 1: Scan ±512KB around current object in 0x200-byte steps
# (playbook objects are ~16KB each)
print('\nScanning ±1MB around current object...')
scan_base = max(ADDR_MIN, cur_obj - 0x100000)
scan_end = cur_obj + 0x100000
addr = scan_base
# align to 256-byte boundary
addr = (addr + 0xFF) & ~0xFF

checked = 0
while addr < scan_end:
    # Quick pre-check: read 2 bytes at object+0x173 (playbook ID location)
    probe = mem_read(hproc, addr + 0x173, 2)
    if probe and 1 <= probe[0] <= 60 and probe[0] == probe[1]:
        # Looks promising - read more
        d = mem_read(hproc, addr, 0x200)
        if d:
            ok, pb_id = is_playbook_object(bytes(d))
            if ok and pb_id not in found:
                found[pb_id] = addr
                print('  Found: pb_id={} at 0x{:X}'.format(pb_id, addr))
    checked += 1
    addr += 0x200  # 512-byte steps

print('Scan complete. Checked {} addresses.'.format(checked))

# Strategy 2: If we know one address, try stride multiples
# Plabook 26 @ 0x362C6590, Playbook 28 @ 0x362CA500 — stride = 0x3F10
# So try: scan at addr ± N * stride for N=1..20
if len(found) >= 2:
    addrs = sorted(found.values())
    if len(addrs) >= 2:
        stride = addrs[1] - addrs[0]
        print('\nInferred stride: 0x{:X}'.format(stride))
        if 0x1000 < stride < 0x100000:
            for n in range(-10, 20):
                test_addr = addrs[0] + n * stride
                if test_addr <= ADDR_MIN or test_addr >= ADDR_MAX:
                    continue
                if test_addr in found.values():
                    continue
                probe = mem_read(hproc, test_addr + 0x173, 2)
                if probe and 1 <= probe[0] <= 60 and probe[0] == probe[1]:
                    d = mem_read(hproc, test_addr, 0x200)
                    if d:
                        ok, pb_id = is_playbook_object(bytes(d))
                        if ok and pb_id not in found:
                            found[pb_id] = test_addr
                            print('  Stride found: pb_id={} at 0x{:X}'.format(pb_id, test_addr))

print('\n=== AUTO-DISCOVERED PLAYBOOKS ===')
for pb_id_k in sorted(found.keys()):
    marker = ' <-- CURRENT' if pb_id_k == cur_id else ''
    print('  pb_id={:3d} (0x{:02X}) -> 0x{:X}{}'.format(
        pb_id_k, pb_id_k, found[pb_id_k], marker))

# Save to mapping file
import json
with open('playbook_map.json', 'w') as f:
    json.dump({str(k): v for k, v in found.items()}, f, indent=2)
print('\nSaved {} entries to playbook_map.json'.format(len(found)))

kernel32.CloseHandle(hproc)
