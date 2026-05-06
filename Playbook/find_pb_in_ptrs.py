"""
Scan all pointer targets from team[0] struct, searching for current playbook ID.
Also search the module .data region more broadly for potential authoritative store.

Strategy:
1. Get current byte[3] from volatile entry (= current playbook ID)
2. Read all team[0] pointer targets (up to 256 bytes each)
3. Show any that contain the playbook ID as a u32/byte
4. Also do a 2-level deep follow (ptr -> ptr -> content)
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
print('module=0x{:X}  team_table=0x{:X}'.format(module_base, table_base))

ADDR_MIN = 0x10000
ADDR_MAX = 0x7FFFFFFFFFFF

# Get current playbook ID
entry = mem_read(hproc, module_base + 0x741F9E0, 16)
pb_id = entry[3]
pb_obj = struct.unpack_from('<Q', entry, 8)[0]
print('Current playbook ID = {} (0x{:02X})  obj=0x{:X}'.format(pb_id, pb_id, pb_obj))

def is_ptr(v):
    return ADDR_MIN < v < ADDR_MAX

def find_pb_id_in_data(data, base_addr, pb_id, label=''):
    hits = []
    # Byte matches
    for i, b in enumerate(data):
        if b == pb_id:
            # Check surrounding context to reduce noise — want isolated small values
            nearby = data[max(0,i-2):i+6]
            hits.append((i, 'byte', b, nearby))
    # u32 matches
    for i in range(0, len(data)-3, 1):
        v = struct.unpack_from('<I', data, i)[0]
        if v == pb_id:
            hits.append((i, 'u32', v, data[i:i+4]))
    return hits

# --- 1. Team[0] pointer scan ---
print('\n=== Team[0] pointer targets containing playbook ID={} ==='.format(pb_id))
t0data = mem_read(hproc, table_base, TEAM_STRIDE)
checked = 0
for off in range(0, TEAM_STRIDE - 7, 8):
    ptr = struct.unpack_from('<Q', t0data, off)[0]
    if not is_ptr(ptr):
        continue
    d = mem_read(hproc, ptr, 512)
    if not d:
        continue
    checked += 1
    hits = find_pb_id_in_data(d, ptr, pb_id)
    if hits:
        for h_off, h_type, h_val, h_ctx in hits[:4]:
            ctx_hex = ' '.join('{:02X}'.format(b) for b in h_ctx)
            print('  team[0]+0x{:04X} -> 0x{:X} +0x{:03X}: {} {}  ctx=[{}]'.format(
                off, ptr, h_off, h_type, h_val, ctx_hex))

print('  (checked {} pointer targets)'.format(checked))

# --- 2. Also check team[0] struct itself ---
print('\n=== Team[0] struct direct bytes with playbook ID={} ==='.format(pb_id))
for i, b in enumerate(t0data):
    if b == pb_id:
        ctx = t0data[max(0,i-4):i+8]
        ctx_hex = ' '.join('{:02X}'.format(x) for x in ctx)
        print('  team[0]+0x{:04X}: byte={} ctx=[{}]'.format(i, b, ctx_hex))

# --- 3. Two-level deep: team[0] ptr -> ptr -> search ---
print('\n=== Two-level deep search for playbook ID={} ==='.format(pb_id))
for off in range(0, TEAM_STRIDE - 7, 8):
    ptr1 = struct.unpack_from('<Q', t0data, off)[0]
    if not is_ptr(ptr1):
        continue
    d1 = mem_read(hproc, ptr1, 256)
    if not d1:
        continue
    for off2 in range(0, len(d1) - 7, 8):
        ptr2 = struct.unpack_from('<Q', d1, off2)[0]
        if not is_ptr(ptr2) or ptr2 == ptr1:
            continue
        d2 = mem_read(hproc, ptr2, 256)
        if not d2:
            continue
        hits = find_pb_id_in_data(d2, ptr2, pb_id)
        if hits:
            for h_off, h_type, h_val, h_ctx in hits[:2]:
                ctx_hex = ' '.join('{:02X}'.format(b) for b in h_ctx)
                print('  team[0]+0x{:04X}->0x{:X}+0x{:04X}->0x{:X}+0x{:03X}: {} {}  ctx=[{}]'.format(
                    off, ptr1, off2, ptr2, h_off, h_type, h_val, ctx_hex))

kernel32.CloseHandle(hproc)
