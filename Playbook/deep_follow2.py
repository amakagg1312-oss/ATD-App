"""
Fixed deep follow - HEAP_MIN was 4GB but this session allocates at ~2.7GB.
Use VirtualQueryEx to confirm valid readable pages instead.
"""
import sys, struct, ctypes, time
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

# Adjusted range: anything above 64KB and below 128TB is potentially valid
ADDR_MIN = 0x10000
ADDR_MAX = 0x7FFFFFFFFFFF

def is_valid_ptr(v):
    return ADDR_MIN < v < ADDR_MAX and v != module_base

def find_ptrs(data, base_addr=0):
    """Find all valid-looking pointers in data."""
    results = []
    for i in range(0, len(data) - 7, 8):
        v = struct.unpack_from('<Q', data, i)[0]
        if is_valid_ptr(v) and v != 0:
            results.append((i, v))
    return results

# --- 1. Team[0] full pointer scan with fixed range ---
print('\n=== Team[0] pointer scan (fixed address range) ===')
t0data = mem_read(hproc, table_base, TEAM_STRIDE)
if t0data:
    ptrs = find_ptrs(t0data)
    print('  {} valid pointers in team[0] struct'.format(len(ptrs)))
    for off, ptr in ptrs[:40]:
        d = mem_read(hproc, ptr, 64)
        if not d:
            continue
        small = [(j, struct.unpack_from('<I', d, j)[0]) for j in range(0, 60, 4)
                 if 1 <= struct.unpack_from('<I', d, j)[0] <= 60]
        if small or off < 256:  # show early offsets + any with small ints
            print('  +0x{:04X} -> 0x{:X}  small_u32(1-60): {}'.format(off, ptr, small[:6]))

# --- 2. Follow ptr0 from team[0] deep ---
print('\n=== Following team[0] ptr0 chain ===')
ptr0 = struct.unpack_from('<Q', t0data, 0)[0]
print('  ptr0 = 0x{:X}'.format(ptr0))
if is_valid_ptr(ptr0):
    d = mem_read(hproc, ptr0, 512)
    if d:
        sub_ptrs = find_ptrs(d)
        print('  {:} sub-pointers in ptr0 target'.format(len(sub_ptrs)))
        for off2, sub_ptr in sub_ptrs[:20]:
            d2 = mem_read(hproc, sub_ptr, 64)
            if not d2: continue
            small = [(j, struct.unpack_from('<I', d2, j)[0]) for j in range(0, 60, 4)
                     if 1 <= struct.unpack_from('<I', d2, j)[0] <= 60]
            print('    ptr0+0x{:04X} -> 0x{:X}  small: {}'.format(off2, sub_ptr, small[:5]))

# --- 3. Follow the 0x7998D50 pointer (0xAE05FF40 from last run) ---
d_7998 = mem_read(hproc, module_base + 0x7998D50, 16)
if d_7998:
    ptr_7998 = struct.unpack_from('<Q', d_7998, 4)[0]
    print('\n=== 0x7998D54 pointer target: 0x{:X} ==='.format(ptr_7998))
    if is_valid_ptr(ptr_7998):
        d = mem_read(hproc, ptr_7998, 512)
        if d:
            for row in range(0, 256, 16):
                chunk = d[row:row+16]
                h = ' '.join('{:02X}'.format(b) for b in chunk)
                asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                print('  +0x{:03X}: {}  {}'.format(row, h, asc))
            sub = find_ptrs(d[:256])
            for off, sp in sub[:10]:
                d2 = mem_read(hproc, sp, 64)
                if d2:
                    small = [(j, struct.unpack_from('<I', d2, j)[0]) for j in range(0, 60, 4)
                             if 1 <= struct.unpack_from('<I', d2, j)[0] <= 60]
                    print('  -> +0x{:04X}->0x{:X}: {}'.format(off, sp, small[:5]))

# --- 4. Follow u64[1] from the changing entries (currently = 0x362C6590 or similar) ---
entry_FA08 = mem_read(hproc, module_base + 0x741FA08, 16)
if entry_FA08:
    u64_0 = struct.unpack_from('<Q', entry_FA08, 0)[0]
    u64_1 = struct.unpack_from('<Q', entry_FA08, 8)[0]
    byte3 = entry_FA08[3]
    print('\n=== Entry RVA+0x741FA08: byte[3]={} u64[0]=0x{:X} u64[1]=0x{:X} ==='.format(
        byte3, u64_0, u64_1))
    for label, ptr in [('u64[0]', u64_0), ('u64[1]', u64_1)]:
        if is_valid_ptr(ptr):
            d = mem_read(hproc, ptr, 256)
            if d:
                print('  {} -> 0x{:X}:'.format(label, ptr))
                for row in range(0, min(256, len(d)), 16):
                    chunk = d[row:row+16]
                    h = ' '.join('{:02X}'.format(b) for b in chunk)
                    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                    print('    +0x{:03X}: {}  {}'.format(row, h, asc))

# --- 5. Scan the full team struct for ALL ptr targets with small ints ---
print('\n=== ALL team[0] pointer targets with small u32 (1-40) ===')
for off, ptr in find_ptrs(t0data):
    d = mem_read(hproc, ptr, 256)
    if not d: continue
    small = [(j, struct.unpack_from('<I', d, j)[0]) for j in range(0, 252, 4)
             if 1 <= struct.unpack_from('<I', d, j)[0] <= 40]
    if small:
        print('  team[0]+0x{:04X} -> 0x{:X}  small(1-40): {}'.format(off, ptr, small[:8]))

kernel32.CloseHandle(hproc)
