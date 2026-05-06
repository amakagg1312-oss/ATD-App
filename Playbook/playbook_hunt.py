"""
Two-pronged hunt for the playbook ID:
1. Read all 76ers staff structs in full, compare A vs current (B)
2. Investigate the '76ers' string hits at 0x2B4A5AB04 area (possible playbook table)
"""
import sys, struct, json, pathlib
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'nba2k26_generator'))
from playbook_scanner import (find_pid, get_module_base, mem_read,
                               GAME_EXE, PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)
import staff_finder

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

# ── Load snapshot A ──────────────────────────────────────────────────────────
with open('ptr_snapshot_A.json') as f:
    snap_A = json.load(f)

table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]

# ── Get the staff table ───────────────────────────────────────────────────────
result = staff_finder.find_staff_table(hproc, module_base)
if not result:
    print('Staff table not found'); kernel32.CloseHandle(hproc); raise SystemExit
staff_base, staff_stride = result
print('Staff table: 0x{:X}  stride={}'.format(staff_base, staff_stride))

# ── Show full staff entries with uint16 dump ─────────────────────────────────
print()
print('Full staff entries (first 50) — all uint16 values 1..200:')
STAFF_ENTRY_COUNT = 50
for i in range(STAFF_ENTRY_COUNT):
    s_addr = staff_base + i * staff_stride
    d = mem_read(hproc, s_addr, staff_stride)
    if not d or all(b == 0 for b in d):
        continue
    # Decode name
    name = ''
    for off in [0, 8, 16, 40, 80]:
        raw = d[off:off+40] if off+40 <= len(d) else b''
        if not raw: continue
        s = raw.decode('utf-16le', errors='ignore')
        null = s.find('\x00')
        s = (s[:null] if null != -1 else s).strip()
        if 3 <= len(s) <= 25 and all(c.isalpha() or c in " -'." for c in s):
            name = s; break
    # Collect ALL small int values (1-100)
    vals = {}
    for j in range(0, staff_stride - 1, 2):
        v16 = struct.unpack_from('<H', d, j)[0]
        if 1 <= v16 <= 100:
            vals[j] = v16
    if name or vals:
        print('  [{}] {:25s}  {}'.format(i, repr(name), dict(list(vals.items())[:8])))

# ── Compare staff A vs current for ALL 50 entries ───────────────────────────
print()
print('Diffing staff entries: snapshot A vs NOW (state B):')
# The staff base (0x2B420D940) corresponds to team struct ptr at offset 0x1058 (4184)
staff_ptr_off = '4184'
if staff_ptr_off in snap_A:
    before_bytes = bytes.fromhex(snap_A[staff_ptr_off]['data'])  # 4096 bytes
    print('  Have {} bytes of pre-switch staff data'.format(len(before_bytes)))
    # Read same range now
    cur_bytes = mem_read(hproc, staff_base, len(before_bytes))
    diffs = [(j, before_bytes[j], cur_bytes[j]) for j in range(len(before_bytes))
             if before_bytes[j] != cur_bytes[j]]
    if diffs:
        print('  {} byte(s) differ!'.format(len(diffs)))
        for diff in diffs[:20]:
            j, a, b = diff
            entry_i = j // staff_stride
            entry_off = j % staff_stride
            print('    entry[{}] +{}: {} -> {}  (u16 frame: {} -> {})'.format(
                entry_i, entry_off, a, b,
                struct.unpack('<H', before_bytes[j-j%2:j-j%2+2])[0] if j >= 2 else 0,
                struct.unpack('<H', cur_bytes[j-j%2:j-j%2+2])[0] if j >= 2 else 0,
            ))
    else:
        print('  No differences in first {} bytes of staff table.'.format(len(before_bytes)))
else:
    print('  Staff ptr offset {} not in snapshot A'.format(staff_ptr_off))

# ── Investigate the 76ers string hits in 0x2B4A5... range ───────────────────
print()
print('=== INVESTIGATING PLAYBOOK MANAGER AREA (0x2B4A5AB04 region) ===')

candidates = [0x2B4A5AB04, 0x2B4A5AE4C]
stride_guess = candidates[1] - candidates[0]
print('Distance between 76ers hits: 0x{:X} = {} bytes'.format(stride_guess, stride_guess))

# Read a wider block to understand the structure
# Go back far enough to see if there are more entries with other team names
block_start = candidates[0] - stride_guess * 5
block_data  = mem_read(hproc, block_start, stride_guess * 40)

if block_data:
    print('Scanning for team-name-like strings every {} bytes...'.format(stride_guess))
    for idx in range(40):
        off = idx * stride_guess
        if off + 32 > len(block_data):
            break
        chunk = block_data[off:off+stride_guess]
        # Check for ASCII team-name strings
        for sub in range(0, min(64, len(chunk))):
            if all(32 <= chunk[sub+k] < 127 for k in range(min(4, len(chunk)-sub))):
                s = bytes(chunk[sub:sub+24]).split(b'\x00')[0].decode('ascii', errors='replace')
                if len(s) >= 3 and s.replace(' ', '').replace('-','').isalpha():
                    addr = block_start + off
                    # Also show uint32 values in this entry
                    u32s = [struct.unpack_from('<I', chunk, k)[0]
                            for k in range(0, min(64, len(chunk))-3, 4)
                            if 0 < struct.unpack_from('<I', chunk, k)[0] < 500]
                    print('  [idx {}] 0x{:X} name@+{}: {!r}  small: {}'.format(
                        idx, addr, sub, s[:20], u32s[:6]))
                    break

# Try reading 256 bytes around the first hit to understand the record structure
print()
print('Record at 0x{:X} (first 76ers hit):'.format(candidates[0]))
rec = mem_read(hproc, candidates[0] - 16, 256)
if rec:
    for row in range(0, 256, 16):
        chunk = rec[row:row+16]
        addr = candidates[0] - 16 + row
        hex_s = ' '.join('{:02X}'.format(b) for b in chunk)
        asc   = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print('  0x{:X}: {}  {}'.format(addr, hex_s, asc))

# ── Also dump snapshot_A for the staff ptr vs current at staff entries 9-30 ──
# (first 9 were in the 4096-byte window; extend further)
print()
print('Staff entries 9-20 full hex (first 64 bytes each):')
for i in range(9, 21):
    s_addr = staff_base + i * staff_stride
    d = mem_read(hproc, s_addr, 64)
    if not d: continue
    hex_s = ' '.join('{:02X}'.format(b) for b in d)
    asc   = ''.join(chr(b) if 32 <= b < 127 else '.' for b in d[:32])
    print('  [{}] 0x{:X}: {}  {}'.format(i, s_addr, hex_s[:47], asc))

kernel32.CloseHandle(hproc)
