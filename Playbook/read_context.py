"""
Read context around the changing RVAs and check team names at indices 12/13/14.
"""
import sys, struct
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

# --- 1. Read 512 bytes around 0x741F4B3 (center it) ---
ctx_rva = 0x741F400
ctx_addr = module_base + ctx_rva
ctx_data = mem_read(hproc, ctx_addr, 512)

print('\n=== 512 bytes @ RVA+0x{:X} (abs 0x{:X}) ==='.format(ctx_rva, ctx_addr))
for row in range(0, 512, 16):
    chunk = ctx_data[row:row+16]
    h = ' '.join('{:02X}'.format(b) for b in chunk)
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    marker = '  <-- 0x741F4B3' if row <= 0xB3 < row + 16 else ''
    print('  RVA+0x{:05X}: {}  {}{}'.format(ctx_rva + row, h.ljust(47), asc, marker))

# --- 2. Check current byte values at all the changing RVAs ---
CHANGING_RVAS = [0x741F383, 0x741F4B3, 0x741F4D3, 0x741F513,
                 0x741F523, 0x741F543, 0x741F553, 0x741F9E3,
                 0x741FAA9, 0x741FEB9]
print('\n=== Current values at changing RVAs ===')
for rva in CHANGING_RVAS:
    b = mem_read(hproc, module_base + rva, 4)
    if b:
        u8 = b[0]
        u16 = struct.unpack('<H', b[:2])[0]
        u32 = struct.unpack('<I', b)[0]
        print('  RVA+0x{:X}: byte={} u16={} u32={}'.format(rva, u8, u16, u32))

# --- 3. Check team names at relevant indices ---
# Values seen: 24, 26, 28 -> divide by 2 -> indices 12, 13, 14
# But also check if they are direct team IDs: read team structs for those entries
print('\n=== Team names at table indices 11..15 ===')
for idx in range(11, 16):
    team_off = table_base + idx * TEAM_STRIDE
    # Team name is likely near the start of the struct - try first 128 bytes
    tdata = mem_read(hproc, team_off, 128)
    if not tdata:
        print('  [{}] (no data)'.format(idx))
        continue
    # Look for ASCII name
    name_bytes = []
    for i in range(0, 128):
        if 32 <= tdata[i] < 127:
            name_bytes.append(chr(tdata[i]))
        else:
            if len(name_bytes) >= 3:
                break
            name_bytes = []
    name = ''.join(name_bytes) if len(name_bytes) >= 3 else '(no name)'
    # Also check for wide string
    wide_name = []
    for i in range(0, 126, 2):
        lo = tdata[i]; hi = tdata[i+1]
        if lo == 0 and hi == 0:
            break
        if 32 <= lo < 127 and hi == 0:
            wide_name.append(chr(lo))
        else:
            if len(wide_name) >= 3:
                break
            wide_name = []
    # Hex dump first 32 bytes
    h = ' '.join('{:02X}'.format(b) for b in tdata[:32])
    print('  [{}] 0x{:X}  hex: {}  ascii: "{}"'.format(idx, team_off, h, name[:30]))

# --- 4. Check what pointers the changing region looks like ---
# Read 2KB around RVA 0x741F000 and show all heap pointers in it
print('\n=== Heap pointers in RVA+0x741E000..0x742000 ===')
region_rva = 0x741E000
region_data = mem_read(hproc, module_base + region_rva, 0x2000)
HEAP_MIN = 0x100000000
HEAP_MAX = 0xF00000000
for i in range(0, len(region_data) - 7, 8):
    val = struct.unpack_from('<Q', region_data, i)[0]
    if HEAP_MIN < val < HEAP_MAX:
        rva = region_rva + i
        print('  RVA+0x{:X} -> 0x{:X}'.format(rva, val))

# --- 5. Try to find what the 0x741F4B3 byte is part of ---
# Read a bigger chunk (4KB) centered on this region and look for patterns
print('\n=== Pattern analysis: 4KB at RVA+0x741F000 ===')
block = mem_read(hproc, module_base + 0x741F000, 0x1000)
# Find all non-zero bytes with small values (1-60 range, like playbook IDs)
small_bytes = [(i, block[i]) for i in range(len(block)) if 1 <= block[i] <= 60]
print('  {} bytes with values 1-60:'.format(len(small_bytes)))
for off, val in small_bytes[:40]:
    print('    +0x{:04X} (RVA+0x{:X}): {}'.format(off, 0x741F000 + off, val))

kernel32.CloseHandle(hproc)
