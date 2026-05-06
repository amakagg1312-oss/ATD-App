"""
Parse Plays.playdata to find the record structure linking play identifiers
to name offsets in the string table.

File layout (from previous analysis):
  Header: u64 count=113, then 8 section offsets
  Section offsets: 0x8DE99, 0xA6C41, 0xE6FE9, 0xFE191, 0x37E349, 0x387E21, 0x388191, 0x38BE49
  String table: UTF-16LE null-terminated strings starting at ~0x3B5900

Known 76ers play name file offsets:
  0x3BEBB0: 'FIST DOWN 25'
  0x3C76EC: 'FIST POP 5'
  0x3DB6D0: 'PHI GIVE 51 SPREAD'
  0x3C9A4E: 'ISO 31 ELBOW'
  0x3E21D8: 'PUNCH ELBOW 54'
  0x3C4366: 'PHI HIGH 5 ELBOW'
"""
import sys, struct, os
from math import gcd
from functools import reduce

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

_here = os.path.dirname(os.path.abspath(__file__))
FILEPATH = os.path.join(_here, 'game files', 'playdata_extracted', 'Plays.playdata')

with open(FILEPATH, 'rb') as f:
    data = f.read()

print('File size: {:,} bytes (0x{:X})'.format(len(data), len(data)))

# Parse header
count = struct.unpack_from('<Q', data, 0)[0]
print('Header count: {}'.format(count))

section_offsets = []
for i in range(8):
    off = struct.unpack_from('<Q', data, 8 + i*8)[0]
    section_offsets.append(off)

# Compute section sizes
section_sizes = []
for i, off in enumerate(section_offsets):
    if i + 1 < len(section_offsets):
        sz = section_offsets[i+1] - off
    else:
        sz = len(data) - off
    section_sizes.append(sz)

print('\nSections:')
for i, (off, sz) in enumerate(zip(section_offsets, section_sizes)):
    print('  Section {}: offset=0x{:X}  size={:,} (0x{:X})'.format(i, off, sz, sz))

# Known 76ers play name locations in the file
KNOWN_NAMES = {
    0x3BEBB0: 'FIST DOWN 25',
    0x3C76EC: 'FIST POP 5',
    0x3DB6D0: 'PHI GIVE 51 SPREAD',
    0x3C9A4E: 'ISO 31 ELBOW',
    0x3E21D8: 'PUNCH ELBOW 54',
    0x3C4366: 'PHI HIGH 5 ELBOW',
}

STRING_TABLE_BASE = 0x3B5900
print('\nKnown name offsets relative to string table (0x{:X}):'.format(STRING_TABLE_BASE))
for file_off, name in sorted(KNOWN_NAMES.items()):
    rel = file_off - STRING_TABLE_BASE
    print('  0x{:X}  rel=0x{:X} ({:,})  "{}"'.format(file_off, rel, rel, name))

# ── Find the actual string table base ────────────────────────────────────────
print('\n=== Finding actual string table base ===')
# Scan the area around 0x3B5900 for where UTF-16 strings actually start
# Look for the transition from binary to readable UTF-16 text
for scan_off in range(0x3B5800, 0x3B6000, 2):
    if scan_off + 100 >= len(data):
        break
    s = data[scan_off:scan_off+100]
    # Check if this looks like UTF-16 printable text
    printable = sum(1 for i in range(0, 100, 2)
                    if s[i] in range(32, 127) and s[i+1] == 0)
    if printable > 30:
        print('  String table starts around 0x{:X} ({} printable UTF-16 chars in first 50 u16s)'.format(
            scan_off, printable))
        break

# ── Try multiple possible string table bases ─────────────────────────────────
print('\n=== Searching all sections for name cross-references ===')

def search_sections_for_offset(target_file_off, bases_to_try):
    """Try each base, compute relative offset, search all sections."""
    for base in bases_to_try:
        rel = target_file_off - base
        if rel < 0 or rel > 0x4000000:
            continue
        for si, (soff, ssz) in enumerate(zip(section_offsets, section_sizes)):
            sec = data[soff:soff+ssz]
            # Try as u32
            for stride in [4, 8, 12, 16, 20, 24, 32, 40, 48, 64]:
                idx = 0
                while True:
                    idx = sec.find(struct.pack('<I', rel & 0xFFFFFFFF), idx)
                    if idx == -1:
                        break
                    print('    base=0x{:X} rel=0x{:X}: found in sec{} at +0x{:X}'.format(
                        base, rel, si, idx))
                    # Show context
                    ctx = sec[max(0,idx-16):idx+32]
                    hex_c = ' '.join('{:02X}'.format(b) for b in ctx)
                    print('      {}'.format(hex_c))
                    idx += 4
                    break  # only first hit per section

# Test with FIST DOWN 25 (most distinctive)
print('\nSearching for "FIST DOWN 25" cross-references...')
search_sections_for_offset(0x3BEBB0, [0, 0x8DE99, 0xFE191, 0x37E349, 0x38BE49,
                                       STRING_TABLE_BASE, 0x3B5900, 0x3B4000])

# ── Try Section 7 as the main index ─────────────────────────────────────────
SEC7_OFF = section_offsets[7]
SEC7_SZ  = section_sizes[7]
sec7 = data[SEC7_OFF : SEC7_OFF + SEC7_SZ]
RECORD_SIZE_7 = 16
total_records_7 = SEC7_SZ // RECORD_SIZE_7

print('\n=== Section 7 ({} records of 16 bytes) ==='.format(total_records_7))
print('First 16 records:')
for i in range(min(16, total_records_7)):
    row = sec7[i*16:(i+1)*16]
    hex_r = ' '.join('{:02X}'.format(b) for b in row)
    u32s = [struct.unpack_from('<I', row, j)[0] for j in range(0, 16, 4)]
    print('  [{:4d}] {}  u32s={}'.format(i, hex_r, u32s))

# Check if u32[0] in record could be a name index or hash
# and u32[2]/u32[3] could be offsets
print('\nSection 7: sample every 100 records:')
for i in range(0, total_records_7, max(1, total_records_7//20)):
    row = sec7[i*16:(i+1)*16]
    u32s = [struct.unpack_from('<I', row, j)[0] for j in range(0, 16, 4)]
    print('  [{:4d}] {}'.format(i, u32s))

# ── Section 0 analysis ────────────────────────────────────────────────────────
SEC0_OFF = section_offsets[0]
SEC0_SZ  = section_sizes[0]
sec0 = data[SEC0_OFF : SEC0_OFF + SEC0_SZ]
print('\n=== Section 0: offset=0x{:X} size={:,} ==='.format(SEC0_OFF, SEC0_SZ))
# Try 4-byte aligned scan for values that look like string table relative offsets
# Relative offsets to known names would be in range 0x6000..0x800000
candidates = []
for i in range(0, min(SEC0_SZ, 256*1024), 4):
    v = struct.unpack_from('<I', sec0, i)[0]
    # Check if this could be an offset into the string table
    test_off = STRING_TABLE_BASE + v
    if 0x3B5900 <= test_off < len(data) - 2:
        # Check if that location has a readable UTF-16 string
        s = data[test_off:test_off+40]
        printable = sum(1 for j in range(0, 40, 2) if s[j] in range(32,127) and s[j+1] == 0)
        if printable >= 4:
            candidates.append((i, v, test_off, printable))

if candidates:
    print('Potential string refs in section 0 (first 256KB):')
    for ci, (i, v, test_off, printable) in enumerate(candidates[:20]):
        end = test_off
        while end + 1 < len(data) and not (data[end] == 0 and data[end+1] == 0):
            end += 2
        s = data[test_off:end].decode('utf-16-le', errors='replace')
        print('  sec0+0x{:X}: val=0x{:X} -> 0x{:X} "{}"'.format(i, v, test_off, s[:40]))
else:
    print('  No string refs found in section 0 (first 256KB) with base 0x{:X}'.format(STRING_TABLE_BASE))

# ── Try bruteforce: find ANY u32 value in sections that points to a UTF-16 string ──
print('\n=== Bruteforce: find u32 pointers to UTF-16 strings in each section ===')
for sec_idx in range(len(section_offsets)):
    soff = section_offsets[sec_idx]
    ssz  = section_sizes[sec_idx]
    # Only scan sections smaller than 5MB to avoid OOM
    scan_sz = min(ssz, 4*1024*1024)
    sec = data[soff:soff+scan_sz]
    string_refs = []
    for i in range(0, len(sec)-3, 4):
        v = struct.unpack_from('<I', sec, i)[0]
        # Is v a plausible file offset into the string area?
        if 0x3B0000 <= v <= 0x3FFFFF:
            # Check if that's a valid UTF-16 string start
            s_bytes = data[v:v+20]
            printable = sum(1 for j in range(0,20,2) if j+1<len(s_bytes) and s_bytes[j] in range(32,127) and s_bytes[j+1]==0)
            if printable >= 3:
                end = v
                while end+1 < len(data) and not (data[end]==0 and data[end+1]==0):
                    end += 2
                s = data[v:end].decode('utf-16-le', errors='replace')
                string_refs.append((i, v, s[:30]))
    if string_refs:
        print('  Section {}: {} absolute u32 file-offset pointers to strings'.format(sec_idx, len(string_refs)))
        for i, v, s in string_refs[:5]:
            print('    sec{}+0x{:X}: 0x{:X} -> "{}"'.format(sec_idx, i, v, s))
    else:
        print('  Section {}: no absolute u32 string pointers found'.format(sec_idx))
