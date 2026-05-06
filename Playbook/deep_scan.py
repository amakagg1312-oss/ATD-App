"""
Deep scan: find the playbook ID by:
1. Using staff_finder.py to locate coach structs (coaches own playbooks in 2K)
2. Reading 64KB from the most promising pointer targets in the team struct
3. Doing an in-memory diff between ptr_snapshot_A and current state (B)
"""
import sys, struct, json, pathlib
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playbook_scanner import (find_pid, get_module_base, mem_read, read_uint64,
                               GAME_EXE, PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]
team_data  = mem_read(hproc, table_base, TEAM_STRIDE)

# ── Load snapshot A for comparison ──────────────────────────────────────────
with open('ptr_snapshot_A.json') as f:
    snap_A = json.load(f)

print('=== DEEP POINTER DIFF (64KB each) ===')
print('Comparing snapshot A vs current memory for all team struct pointer targets')
print()

any_diff = False
for i in range(0, TEAM_STRIDE - 7, 8):
    val = struct.unpack_from('<Q', team_data, i)[0]
    if not (0x100000000 < val < 0x7FF000000000):
        continue

    off_str = str(i)
    if off_str not in snap_A:
        continue

    # Read 64KB from the target now (state B)
    cur = mem_read(hproc, val, 65536)
    if not cur:
        continue

    prev_hex = snap_A[off_str]['data']
    prev = bytes.fromhex(prev_hex)  # only 4096 bytes from snapshot A
    compare_len = min(len(prev), len(cur))

    diffs = [(j, prev[j], cur[j]) for j in range(compare_len) if prev[j] != cur[j]]
    if not diffs:
        continue

    any_diff = True
    print('  +0x{:04X} ({}) -> 0x{:X}  [{} bytes differ in first {}B]'.format(
        i, i, val, len(diffs), compare_len))
    blocks = []
    blk = [diffs[0]]
    for d in diffs[1:]:
        if d[0] == blk[-1][0] + 1: blk.append(d)
        else: blocks.append(blk); blk = [d]
    blocks.append(blk)
    for blk in blocks[:10]:
        sub = blk[0][0]
        raw_a = bytes(x[1] for x in blk[:4]).ljust(4, b'\x00')
        raw_b = bytes(x[2] for x in blk[:4]).ljust(4, b'\x00')
        u32_a = struct.unpack('<I', raw_a)[0]
        u32_b = struct.unpack('<I', raw_b)[0]
        hex_a = ' '.join('{:02X}'.format(x[1]) for x in blk[:8])
        hex_b = ' '.join('{:02X}'.format(x[2]) for x in blk[:8])
        print('    sub +0x{:04X} ({:4d}): [{}] -> [{}]  u32: {} -> {}'.format(
            sub, sub, hex_a, hex_b, u32_a, u32_b))

if not any_diff:
    print('  Still no differences found in pointer targets.')

# ── Staff finder (dynamic search for known coach names) ──────────────────────
print()
print('=== STAFF TABLE SCAN ===')
sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'nba2k26_generator'))

try:
    import staff_finder
    result = staff_finder.find_staff_table(hproc, module_base)
    if result:
        staff_base, stride = result
        print('Staff table found at 0x{:X}  stride={}'.format(staff_base, stride))
        # Scan head coaches (type=0 or similar) and show their playbook-range values
        for i in range(40):
            s_addr = staff_base + i * stride
            d = mem_read(hproc, s_addr, stride)
            if not d or all(b == 0 for b in d):
                continue
            # Find name
            name = ''
            for off in range(0, 80, 8):
                raw = d[off:off+40]
                s = raw.decode('utf-16le', errors='ignore')
                null = s.find('\x00')
                s = (s[:null] if null != -1 else s).strip()
                if (3 <= len(s) <= 20 and
                        s.replace(' ', '').replace('-', '').replace("'", '').replace('.', '').isalpha()):
                    name = s
                    break
            small = [(j, struct.unpack_from('<I', d, j)[0])
                     for j in range(0, stride - 3, 4)
                     if 1 <= struct.unpack_from('<I', d, j)[0] <= 100]
            if name:
                print('  [{}] {:20s}  small(1-100): {}'.format(i, repr(name), small[:6]))
    else:
        print('Staff table not found via staff_finder.')
        print('Trying RVA from Playbook/2k26_offsets.json...')
        offsets_path = pathlib.Path(__file__).parent / '2k26_offsets.json'
        with open(offsets_path) as f:
            offsets = json.load(f)
        staff_rva = offsets['base_pointers']['Staff']['address']
        print('Staff RVA from Playbook json: 0x{:X} ({})'.format(staff_rva, staff_rva))
        if staff_rva > 0:
            staff_ptr = module_base + staff_rva
            staff_base = struct.unpack('<Q', mem_read(hproc, staff_ptr, 8))[0]
            print('Staff table: 0x{:X}'.format(staff_base))
            for i in range(10):
                s_addr = staff_base + i * 432
                d = mem_read(hproc, s_addr, 432)
                if not d: continue
                hex_s = ' '.join('{:02X}'.format(b) for b in d[:32])
                print('  [{}] 0x{:X}: {}'.format(i, s_addr, hex_s))
except Exception as e:
    print('staff_finder error: {}'.format(e))
    import traceback; traceback.print_exc()

# ── Raw heap scan: look for playbook name strings ─────────────────────────────
print()
print('=== SEARCHING HEAP FOR PLAYBOOK STRINGS ===')
# NBA 2K playbooks are often named like "XXX_Playbook" or have team abbreviation + "playbook"
# Search for common patterns in the team's heap vicinity
search_terms = [b'playbook', b'PLAYBOOK', b'Playbook', b'play_book',
                b'76ers', b'PHI', b'phi']

# Scan 32MB around the team struct address
scan_base  = table_base & ~0xFFFFFF  # align down to 16MB
scan_size  = 64 * 1024 * 1024

data_chunk = mem_read(hproc, scan_base, scan_size)
if data_chunk:
    for term in search_terms:
        pos = 0
        hits = []
        while True:
            idx = data_chunk.find(term, pos)
            if idx == -1 or len(hits) >= 5:
                break
            hits.append(scan_base + idx)
            pos = idx + 1
        if hits:
            print('  "{}": found {} hits'.format(term.decode('latin1'), len(hits)))
            for addr in hits[:3]:
                context = mem_read(hproc, addr - 8, 64)
                if context:
                    hex_s = ' '.join('{:02X}'.format(b) for b in context)
                    try:
                        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
                    except:
                        asc = ''
                    print('    0x{:X}: {} | {}'.format(addr, hex_s[:47], asc[:24]))

kernel32.CloseHandle(hproc)
