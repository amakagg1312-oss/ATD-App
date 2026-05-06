"""
The small values at sub+0x048 (e.g. 0x645A1B) appear to be play identifiers.
Hypothesis: they are RVAs from module_base pointing into the play catalog in .data.

This script:
1. Collects all unique play ID values from pb24
2. Tests if module_base + value is readable (RVA hypothesis)
3. Also tests if the value itself is readable in process memory
4. Dumps data at each potential play catalog entry
5. Searches for known play name substrings near each address
"""
import sys, struct, json, os, ctypes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

_here = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = next(
    (p for p in [os.path.join(_here, 'playbook_map.json'), 'playbook_map.json']
     if os.path.exists(p)), 'playbook_map.json'
)
with open(MAP_FILE) as f:
    pb_map = {int(k): v for k, v in json.load(f).items()}

PB24_ADDR = pb_map[24]
OBJ_SIZE  = 0x5000
SUB_SIZE  = 0x200
HEAP_MIN  = 0x100000000
HEAP_MAX  = 0x200000000

CATEGORY_NAMES = ['3PT','P&R','ISO','POST-H','CUTTER','POST-L','MID','GUARD','HANDOFF']

obj = bytes(mem_read(hproc, PB24_ADDR, OBJ_SIZE) or b'')

sub_ptrs = {}
for i in range(0, len(obj)-7, 8):
    v = struct.unpack_from('<Q', obj, i)[0]
    if HEAP_MIN <= v < HEAP_MAX and v not in sub_ptrs:
        sub_ptrs[v] = i

# Collect all unique play ID values (small non-zero values that failed mem_read)
play_ids = {}   # value -> (list of (sub_addr, elem, cat))
for sub_addr in sorted(sub_ptrs.keys()):
    obj_off = sub_ptrs[sub_addr]
    elem = obj_off // 0x910
    cat  = CATEGORY_NAMES[elem] if elem < len(CATEGORY_NAMES) else '?'
    sub  = mem_read(hproc, sub_addr, SUB_SIZE)
    if not sub:
        continue
    sub = bytes(sub)
    play_ptr = struct.unpack_from('<Q', sub, 0x048)[0]
    if play_ptr == 0:
        continue
    # Classify: real pointer vs small ID
    if not (HEAP_MIN <= play_ptr < HEAP_MAX):
        if play_ptr > 0x10000 and play_ptr < 0x10000000:  # 64KB - 256MB range
            if play_ptr not in play_ids:
                play_ids[play_ptr] = []
            play_ids[play_ptr].append((sub_addr, elem, cat))

print('Unique play ID values found: {}'.format(len(play_ids)))
print('Values: {}'.format(sorted(hex(v) for v in play_ids.keys())))

print('\n=== TESTING RVA HYPOTHESIS (module_base + value) ===')
print('module_base = 0x{:X}'.format(module_base))

readable_rvas = []
for val in sorted(play_ids.keys()):
    rva_addr = module_base + val
    d = mem_read(hproc, rva_addr, 64)
    if d:
        readable_rvas.append((val, bytes(d)))
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in d[:32])
        hex_p = ' '.join('{:02X}'.format(b) for b in d[:16])
        print('  0x{:X} -> mod+RVA 0x{:X}: [{}]  {}'.format(val, rva_addr, hex_p, asc))
    else:
        print('  0x{:X} -> mod+RVA 0x{:X}: NOT READABLE'.format(val, rva_addr))

if readable_rvas:
    print('\n>>> RVA hypothesis: CONFIRMED for {} values'.format(len(readable_rvas)))
    print('\n=== FULL DUMP of first 5 play catalog entries ===')
    for val, data in readable_rvas[:5]:
        cats = [c for _, _, c in play_ids[val]]
        rva_addr = module_base + val
        print('\n  Play ID 0x{:X} (cats: {}) at RVA+0x{:X}:'.format(val, cats, val))
        for i in range(0, min(0x40, len(data)), 16):
            row = data[i:i+16]
            hex_p = ' '.join('{:02X}'.format(b) for b in row)
            asc_p = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
            u32s  = [struct.unpack_from('<I', row, j)[0] for j in range(0, len(row)-3, 4)]
            print('    +0x{:02X}: {}  {}  {}'.format(i, hex_p, asc_p,
                  [v for v in u32s if 0 < v < 100000]))
else:
    print('\nRVA hypothesis FAILED. Trying direct read of values as absolute addresses...')
    for val in sorted(play_ids.keys()):
        d = mem_read(hproc, val, 64)
        if d:
            asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in d[:32])
            print('  0x{:X} direct: {}'.format(val, asc))

# Also: search for the play names from the screenshot near module data
print('\n=== SEARCHING MODULE DATA FOR KNOWN PLAY NAMES ===')
PLAY_NAMES = [b'FIST DOWN', b'FIST POP', b'PHI GIVE', b'ISO 31', b'PUNCH ELBOW', b'PHI HIGH']

# Read module data in chunks around the play ID values
if play_ids:
    min_val = min(play_ids.keys())
    max_val = max(play_ids.keys())
    # Read a window around the play IDs
    window_start = (min_val // 0x10000) * 0x10000
    window_size  = min(0x80000, max_val - window_start + 0x1000)
    print('Reading module window RVA+0x{:X} .. +0x{:X} ({} KB)'.format(
        window_start, window_start + window_size, window_size // 1024))
    window_data = mem_read(hproc, module_base + window_start, window_size)
    if window_data:
        window_data = bytes(window_data)
        for name in PLAY_NAMES:
            idx = window_data.find(name)
            if idx != -1:
                rva = window_start + idx
                print('  Found "{}" at RVA+0x{:X}'.format(name.decode(), rva))
                # Show surrounding context
                ctx = window_data[max(0, idx-8):idx+64]
                hex_c = ' '.join('{:02X}'.format(b) for b in ctx)
                asc_c = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
                print('    {}'.format(asc_c))
            else:
                print('  "{}" not found in window'.format(name.decode()))
    else:
        print('  Could not read module window')

kernel32.CloseHandle(hproc)
