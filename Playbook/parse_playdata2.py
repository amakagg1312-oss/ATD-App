"""
Focused analysis:
1. Search all sections for exact relative u32 offsets of known 76ers play names
2. Analyze Section 3 record stride by looking at where absolute string pointers cluster
3. Find the play->name mapping
"""
import sys, struct, os
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

_here = os.path.dirname(os.path.abspath(__file__))
FILEPATH = os.path.join(_here, 'game files', 'playdata_extracted', 'Plays.playdata')

with open(FILEPATH, 'rb') as f:
    data = f.read()

# Parse header
count = struct.unpack_from('<Q', data, 0)[0]
section_offsets = [struct.unpack_from('<Q', data, 8 + i*8)[0] for i in range(8)]
section_sizes = []
for i, off in enumerate(section_offsets):
    if i + 1 < len(section_offsets):
        sz = section_offsets[i+1] - off
    else:
        sz = len(data) - off
    section_sizes.append(sz)

STRING_TABLE_BASE = 0x3B5900  # verified from previous run

# Known 76ers play names → relative offsets from string table base
KNOWN_76ERS = {
    'FIST DOWN 25':     0x3BEBB0 - STRING_TABLE_BASE,   # 0x92B0
    'FIST POP 5':       0x3C76EC - STRING_TABLE_BASE,   # 0x11DEC
    'PHI GIVE 51 SPREAD': 0x3DB6D0 - STRING_TABLE_BASE, # 0x25DD0
    'ISO 31 ELBOW':     0x3C9A4E - STRING_TABLE_BASE,   # 0x1414E
    'PUNCH ELBOW 54':   0x3E21D8 - STRING_TABLE_BASE,   # 0x2C8D8
    'PHI HIGH 5 ELBOW': 0x3C4366 - STRING_TABLE_BASE,   # 0xEA66
    'PHI GIVE 41 GO':   0x3DBDC6 - STRING_TABLE_BASE,   # 0x264C6
    'PHI GIVE 23 GO':   0x3E266A - STRING_TABLE_BASE,   # 0x2CD6A
    'PHI GIVE 54 SHAKE': 0x3CD300 - STRING_TABLE_BASE,  # 0x17A00
}

print('=== SEARCHING ALL SECTIONS FOR 76ERS PLAY NAME RELATIVE OFFSETS ===')
print('String table base: 0x{:X}\n'.format(STRING_TABLE_BASE))

for name, rel in sorted(KNOWN_76ERS.items(), key=lambda x: x[1]):
    print('  "{}" rel_u32=0x{:X}:'.format(name, rel))
    found_any = False
    for si, (soff, ssz) in enumerate(zip(section_offsets, section_sizes)):
        sec = data[soff:soff+ssz]
        target = struct.pack('<I', rel)
        idx = 0
        while True:
            idx = sec.find(target, idx)
            if idx == -1:
                break
            ctx = sec[max(0,idx-16):idx+32]
            hex_c = ' '.join('{:02X}'.format(b) for b in ctx)
            print('    SEC{} +0x{:X}: {}'.format(si, idx, hex_c))
            found_any = True
            idx += 4
    if not found_any:
        print('    NOT FOUND in any section')

# ── Analyze Section 0 record structure ───────────────────────────────────────
print('\n=== SECTION 0 RECORD STRUCTURE ANALYSIS ===')
SEC0_OFF = section_offsets[0]
SEC0_SZ  = section_sizes[0]
sec0 = data[SEC0_OFF:SEC0_OFF+SEC0_SZ]

# Find ALL relative offsets that point to starts of UTF-16 strings
def is_string_start(rel_off):
    """True if STRING_TABLE_BASE + rel_off is the start of a non-trivial UTF-16 string."""
    abs_off = STRING_TABLE_BASE + rel_off
    if abs_off < 0 or abs_off + 4 >= len(data):
        return False
    # Previous 2 bytes should be null (end of previous string or pre-table)
    if abs_off >= 2 and not (data[abs_off-2] == 0 and data[abs_off-1] == 0):
        return False
    # First char should be printable ASCII
    if not (data[abs_off] in range(32, 127) and data[abs_off+1] == 0):
        return False
    return True

def read_str(rel_off):
    abs_off = STRING_TABLE_BASE + rel_off
    end = abs_off
    while end + 1 < len(data):
        if data[end] == 0 and data[end+1] == 0:
            break
        end += 2
    return data[abs_off:end].decode('utf-16-le', errors='replace')

# Collect all string-start offsets within section 0
string_refs_sec0 = []
for i in range(0, SEC0_SZ - 3, 4):
    v = struct.unpack_from('<I', sec0, i)[0]
    if 0 <= v < 0x100000 and is_string_start(v):
        string_refs_sec0.append((i, v, read_str(v)))

print('Section 0: {} positions with aligned relative string-start pointers'.format(len(string_refs_sec0)))
print('First 30:')
for i, v, s in string_refs_sec0[:30]:
    print('  sec0+0x{:04X}: 0x{:05X} -> "{}"'.format(i, v, s[:40]))

# Find the stride between consecutive string refs
if len(string_refs_sec0) >= 4:
    positions = [x[0] for x in string_refs_sec0]
    diffs = [positions[i+1] - positions[i] for i in range(min(len(positions)-1, 20))]
    print('\nDiffs between consecutive string ref positions: {}'.format(diffs))

    # Look for the most common diff
    diff_counts = Counter(diffs)
    print('Most common diffs: {}'.format(diff_counts.most_common(5)))

# ── Section 0 full scan: positions of all string-start refs ───────────────────
print('\n\nSection 0: find record size by looking at field positions')
# Within each candidate record, what offset does the name appear at?
# If records are N bytes, then string refs should appear at (K*N + offset_within_record)
# for some fixed offset_within_record.
# Try candidate record sizes and find which one makes refs align:
for rec_size in [0xE0, 0xE4, 0x910, 0x900, 0x1B4, 0xD8, 0xC8, 0xB4, 0x5C, 0x78]:
    if rec_size == 0:
        continue
    # Check what fraction of string refs appear at a consistent offset within record
    offsets_within = [pos % rec_size for pos, v, s in string_refs_sec0]
    oc = Counter(offsets_within)
    top = oc.most_common(3)
    total = len(string_refs_sec0)
    consistency = top[0][1] / total if total > 0 else 0
    if consistency >= 0.3:
        print('  Record size 0x{:X}: top field offset = 0x{:X} ({:.0%} of refs)'.format(
            rec_size, top[0][0], consistency))

# ── Section 3 record structure ────────────────────────────────────────────────
print('\n=== SECTION 3 RECORD STRUCTURE ===')
SEC3_OFF = section_offsets[3]
SEC3_SZ  = section_sizes[3]
sec3 = data[SEC3_OFF:SEC3_OFF+SEC3_SZ]

# Find all absolute file-offset pointers into string area in Section 3
# String area is approximately 0x3B5900 to 0x430000
STRING_MIN = 0x3B5900
STRING_MAX = 0x430000
abs_string_refs = []
for i in range(0, min(SEC3_SZ, 8*1024*1024) - 3, 4):
    v = struct.unpack_from('<I', sec3, i)[0]
    if STRING_MIN <= v < STRING_MAX:
        # Check it points to start of a UTF-16 string
        if data[v] in range(32, 127) and data[v+1] == 0:
            end = v
            while end+1 < len(data) and not (data[end]==0 and data[end+1]==0):
                end += 2
            s = data[v:end].decode('utf-16-le', errors='replace')
            if len(s) >= 3:
                abs_string_refs.append((i, v, s))

print('Section 3: {} absolute string pointers'.format(len(abs_string_refs)))
print('First 20:')
for i, v, s in abs_string_refs[:20]:
    print('  sec3+0x{:05X}: 0x{:X} -> "{}"'.format(i, v, s[:40]))

# Find stride
if len(abs_string_refs) >= 4:
    positions = [x[0] for x in abs_string_refs]
    diffs = [positions[j+1] - positions[j] for j in range(min(len(positions)-1, 30))]
    print('\nDiffs: {}'.format(diffs[:20]))
    diff_counts = Counter(diffs)
    print('Most common: {}'.format(diff_counts.most_common(5)))

    for rec_size in [0x60, 0x80, 0x100, 0x200, 0x400, 0xC40, 0x1000, 0x4000]:
        offsets_within = [pos % rec_size for pos, v, s in abs_string_refs]
        oc = Counter(offsets_within)
        top = oc.most_common(3)
        total = len(abs_string_refs)
        consistency = top[0][1] / total if total > 0 else 0
        if consistency >= 0.3:
            print('  Rec size 0x{:X}: top field offset 0x{:X} ({:.0%}), second 0x{:X} ({:.0%})'.format(
                rec_size, top[0][0], consistency,
                top[1][0] if len(top)>1 else 0, top[1][1]/total if len(top)>1 else 0))

# ── Look at what's near a known 76ers play in Section 3 ──────────────────────
print('\n=== Section 3: scan for 76ers play names (absolute u32 pointers) ===')
for name, rel in KNOWN_76ERS.items():
    abs_off = STRING_TABLE_BASE + rel
    target = struct.pack('<I', abs_off)
    idx = 0
    found = False
    while True:
        idx = sec3.find(target, idx)
        if idx == -1:
            break
        ctx = sec3[max(0,idx-32):idx+64]
        hex_c = ' '.join('{:02X}'.format(b) for b in ctx)
        asc_c = ''.join(chr(b) if 32<=b<127 else '.' for b in ctx)
        print('  "{}" at sec3+0x{:X}'.format(name, idx))
        print('    hex: {}'.format(hex_c))
        print('    asc: {}'.format(asc_c))
        found = True
        idx += 4
    if not found:
        print('  "{}" abs=0x{:X} NOT FOUND in sec3'.format(name, abs_off))

# ── Look at Section 3 with a different interpretation: maybe offsets use u64 ──
print('\n=== Section 3: u64 absolute string pointers ===')
abs_string_refs64 = []
for i in range(0, min(SEC3_SZ, 4*1024*1024) - 7, 8):
    v = struct.unpack_from('<Q', sec3, i)[0]
    if STRING_MIN <= v < STRING_MAX:
        if data[v] in range(32, 127) and data[v+1] == 0:
            end = v
            while end+1 < len(data) and not (data[end]==0 and data[end+1]==0):
                end += 2
            s = data[v:end].decode('utf-16-le', errors='replace')
            if len(s) >= 3:
                abs_string_refs64.append((i, v, s))

print('Section 3: {} u64 absolute string pointers in first 4MB'.format(len(abs_string_refs64)))
if abs_string_refs64:
    for i, v, s in abs_string_refs64[:10]:
        print('  sec3+0x{:X}: 0x{:X} -> "{}"'.format(i, v, s[:40]))
