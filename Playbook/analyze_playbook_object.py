"""
Parse the live playbook heap object to find where the 60 plays are stored.

We know:
  - Object address from volatile entry u64[1]
  - Object is ~16KB (0x4000 bytes)
  - Playbook ID at object+0x0173 and +0x019B
  - The 76ers playbook has exactly 60 plays

Strategy:
  1. Dump the full object
  2. Find the number 60 (play count) as u8/u16/u32
  3. Find sequences of small u16/u32 values that could be play IDs
  4. Cross-check with known category counts (4, 22, 8, 13, 3, 3, 0, 0, 7)
  5. Dump the play array candidates
"""
import sys, struct, time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

VOLATILE_RVA = 0x741F9E0
OBJ_SIZE = 0x4000  # 16KB

def read_entry():
    e = mem_read(hproc, module_base + VOLATILE_RVA, 16)
    if e:
        return e[3], struct.unpack_from('<Q', e, 8)[0]
    return None, None

pb_id, obj_addr = read_entry()
print('Current playbook: pb_id={} obj=0x{:X}'.format(pb_id, obj_addr))

data = mem_read(hproc, obj_addr, OBJ_SIZE)
if not data:
    print('ERROR: Could not read playbook object at 0x{:X}'.format(obj_addr))
    kernel32.CloseHandle(hproc)
    sys.exit(1)

print('Read {} bytes from playbook object'.format(len(data)))
print('Confirmed pb_id at +0x173: {} at +0x19B: {}'.format(data[0x173], data[0x19B]))

# Save full object dump for offline analysis
with open('playbook_obj_{}.bin'.format(pb_id), 'wb') as f:
    f.write(data)
print('Saved to playbook_obj_{}.bin'.format(pb_id))

# ── FIND 60 (play count) ──────────────────────────────────────────────────────
print('\n=== SEARCHING FOR PLAY COUNT (60 = 0x3C) ===')

# From screenshot: total=60, by category: 4 3pt, 22 P&R, 8 ISO, 13 POST-H, 3 CUTTER, 3 POST-L, 0 MID, 0 GUARD, 7 HANDOFF
CATEGORY_COUNTS = [4, 22, 8, 13, 3, 3, 0, 0, 7]
TOTAL_PLAYS = 60

hits_60_u16 = []
hits_60_u32 = []

for i in range(len(data) - 3):
    # u16
    if i + 2 <= len(data):
        v16 = struct.unpack_from('<H', data, i)[0]
        if v16 == TOTAL_PLAYS:
            hits_60_u16.append(i)
    # u32
    if i + 4 <= len(data):
        v32 = struct.unpack_from('<I', data, i)[0]
        if v32 == TOTAL_PLAYS:
            hits_60_u32.append(i)

print('u16==60 at offsets: {}'.format(['0x{:X}'.format(x) for x in hits_60_u16[:20]]))
print('u32==60 at offsets: {}'.format(['0x{:X}'.format(x) for x in hits_60_u32[:20]]))

# ── FIND CATEGORY COUNT SEQUENCE ─────────────────────────────────────────────
print('\n=== SEARCHING FOR CATEGORY COUNTS [4,22,8,13,3,3,0,0,7] ===')

def find_seq_u8(data, seq):
    results = []
    for i in range(len(data) - len(seq) + 1):
        if list(data[i:i+len(seq)]) == list(seq):
            results.append(i)
    return results

def find_seq_u16(data, seq):
    results = []
    for i in range(0, len(data) - len(seq)*2 + 1, 2):
        vals = [struct.unpack_from('<H', data, i + j*2)[0] for j in range(len(seq))]
        if vals == list(seq):
            results.append(i)
    return results

def find_seq_u32(data, seq):
    results = []
    for i in range(0, len(data) - len(seq)*4 + 1, 4):
        vals = [struct.unpack_from('<I', data, i + j*4)[0] for j in range(len(seq))]
        if vals == list(seq):
            results.append(i)
    return results

cat_u8  = find_seq_u8(data, CATEGORY_COUNTS)
cat_u16 = find_seq_u16(data, CATEGORY_COUNTS)
cat_u32 = find_seq_u32(data, CATEGORY_COUNTS)

print('u8  sequence found at: {}'.format(['0x{:X}'.format(x) for x in cat_u8]))
print('u16 sequence found at: {}'.format(['0x{:X}'.format(x) for x in cat_u16]))
print('u32 sequence found at: {}'.format(['0x{:X}'.format(x) for x in cat_u32]))

# ── FIND PLAY ID ARRAY ────────────────────────────────────────────────────────
# Play IDs are likely small integers (< 65535), densely packed
# Look for runs of 60 consecutive u16 or u32 values that are all > 0 and < 10000
print('\n=== SEARCHING FOR PLAY ID ARRAY (60 small nonzero values) ===')

def score_run(vals, min_v=1, max_v=9999, min_unique=10):
    if not vals:
        return 0
    in_range = sum(1 for v in vals if min_v <= v <= max_v)
    unique = len(set(v for v in vals if min_v <= v <= max_v))
    return in_range, unique

play_array_candidates = []

# Scan for 60 consecutive u16 values (all in valid play ID range)
PLAY_ID_MAX = 5000  # play IDs are probably < 5000
for i in range(0, len(data) - 120, 2):
    vals = [struct.unpack_from('<H', data, i + j*2)[0] for j in range(60)]
    in_range = sum(1 for v in vals if 1 <= v <= PLAY_ID_MAX)
    if in_range >= 55:  # at least 55 of 60 in valid range
        unique = len(set(v for v in vals if 1 <= v <= PLAY_ID_MAX))
        play_array_candidates.append(('u16', i, in_range, unique, vals))

# Scan for 60 consecutive u32 values
for i in range(0, len(data) - 240, 4):
    vals = [struct.unpack_from('<I', data, i + j*4)[0] for j in range(60)]
    in_range = sum(1 for v in vals if 1 <= v <= PLAY_ID_MAX)
    if in_range >= 55:
        unique = len(set(v for v in vals if 1 <= v <= PLAY_ID_MAX))
        play_array_candidates.append(('u32', i, in_range, unique, vals))

# Sort by uniqueness (most unique play IDs = most likely the real array)
play_array_candidates.sort(key=lambda x: -x[3])

print('Found {} candidate play arrays:'.format(len(play_array_candidates)))
for dtype, offset, in_range, unique, vals in play_array_candidates[:5]:
    print('\n  {} at +0x{:X} ({} in range, {} unique):'.format(dtype, offset, in_range, unique))
    print('  Values: {}'.format(vals[:30]))
    if len(vals) > 30:
        print('  ...and {} more'.format(len(vals) - 30))

# ── DUMP SURROUNDINGS OF 60-HITS ─────────────────────────────────────────────
print('\n=== CONTEXT AROUND u32==60 HITS ===')
for off in hits_60_u32[:10]:
    ctx_start = max(0, off - 16)
    ctx_end   = min(len(data), off + 64)
    chunk = data[ctx_start:ctx_end]
    hex_row = ' '.join('{:02X}'.format(b) for b in chunk)
    u32s = [struct.unpack_from('<I', data, off + j*4)[0]
            for j in range(8) if off + j*4 + 4 <= len(data)]
    print('\n  +0x{:X}: ...{} [{}] -> next u32s: {}'.format(
        off, data[max(0,off-4):off].hex(), data[off:off+4].hex(), u32s[:8]))

# ── LOOK FOR COUNT+ARRAY PATTERN ─────────────────────────────────────────────
# Pattern: u32 = 60, immediately followed by 60 play IDs
print('\n=== COUNT+ARRAY PATTERN CHECK ===')
for off in hits_60_u32:
    arr_start = off + 4
    if arr_start + 60*4 > len(data):
        arr_start_16 = off + 2
        if arr_start_16 + 60*2 <= len(data):
            vals16 = [struct.unpack_from('<H', data, arr_start_16 + j*2)[0] for j in range(60)]
            in_range = sum(1 for v in vals16 if 1 <= v <= PLAY_ID_MAX)
            if in_range >= 40:
                print('  +0x{:X} u32==60 followed by u16 array ({} in range):'.format(off, in_range))
                print('    {}'.format(vals16[:20]))
        continue
    vals32 = [struct.unpack_from('<I', data, arr_start + j*4)[0] for j in range(60)]
    in_range = sum(1 for v in vals32 if 1 <= v <= PLAY_ID_MAX)
    if in_range >= 40:
        print('  +0x{:X} u32==60 followed by u32 array ({}/60 in range):'.format(off, in_range))
        print('    {}'.format(vals32[:20]))

# ── FULL HEX DUMP (first 0x500 bytes) ────────────────────────────────────────
print('\n=== HEX DUMP: first 0x400 bytes of playbook object ===')
for i in range(0, min(0x400, len(data)), 16):
    row = data[i:i+16]
    hex_part = ' '.join('{:02X}'.format(b) for b in row)
    asc_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
    print('  +0x{:04X}: {:<48}  {}'.format(i, hex_part, asc_part))

kernel32.CloseHandle(hproc)
