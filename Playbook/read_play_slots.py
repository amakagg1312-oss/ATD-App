"""
Read the pb24 playbook object, follow every sub-struct pointer,
then read the play object at sub+0x048 to understand the play format.

From diff_all_playbooks output:
  - pb24 @ 0x127714770 is the 76ers playbook
  - sub+0x048 = 8-byte pointer to play data (zero = empty slot)
  - sub+0x1D8 = 1-byte flag (active/inactive)
  - obj+0x33C8 / +0x33CC = play counts (changed 2->1)
"""
import sys, struct, json, os
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
     if os.path.exists(p)),
    'playbook_map.json'
)

with open(MAP_FILE) as f:
    pb_map = {int(k): v for k, v in json.load(f).items()}

PB24_ADDR = pb_map[24]
OBJ_SIZE  = 0x5000
SUB_SIZE  = 0x200   # 512 bytes per sub-struct
PLAY_SIZE = 0x100   # 256 bytes per play object

HEAP_MIN = 0x100000000
HEAP_MAX = 0x200000000

print('Reading pb24 @ 0x{:X}'.format(PB24_ADDR))
obj = bytes(mem_read(hproc, PB24_ADDR, OBJ_SIZE) or b'')
print('Object size: {} bytes'.format(len(obj)))

# Extract sub-struct pointers (unique 0x127xxxxxxx addresses)
sub_ptrs = {}
for i in range(0, len(obj) - 7, 8):
    v = struct.unpack_from('<Q', obj, i)[0]
    if HEAP_MIN <= v < HEAP_MAX and v not in sub_ptrs:
        sub_ptrs[v] = i  # addr -> offset_in_object

print('Found {} unique sub-struct pointers'.format(len(sub_ptrs)))

# ── Read each sub-struct and follow sub+0x048 (play pointer) ─────────────────
CATEGORY_NAMES = ['3PT', 'P&R', 'ISO', 'POST-H', 'CUTTER', 'POST-L', 'MID', 'GUARD', 'HANDOFF']

print('\n=== PLAY SLOTS (sub+0x048 pointer → play object) ===\n')

plays_found = {}   # play_ptr -> (sub_addr, data)
empty_slots  = 0
active_plays = []

for sub_addr in sorted(sub_ptrs.keys()):
    obj_off = sub_ptrs[sub_addr]
    elem = obj_off // 0x910
    cat  = CATEGORY_NAMES[elem] if elem < len(CATEGORY_NAMES) else '?'

    sub = mem_read(hproc, sub_addr, SUB_SIZE)
    if not sub:
        continue
    sub = bytes(sub)

    # Play pointer at sub+0x048
    play_ptr = struct.unpack_from('<Q', sub, 0x048)[0]
    flag_1d8 = sub[0x1D8] if len(sub) > 0x1D8 else 0xFF

    if play_ptr == 0:
        empty_slots += 1
        continue

    if play_ptr not in plays_found:
        # Read the play object
        play_data = mem_read(hproc, play_ptr, PLAY_SIZE)
        if play_data:
            plays_found[play_ptr] = bytes(play_data)

    play_data = plays_found.get(play_ptr, b'')
    active_plays.append((sub_addr, obj_off, elem, cat, play_ptr, flag_1d8, play_data))

print('Active play slots: {}'.format(len(active_plays)))
print('Empty play slots:  {}'.format(empty_slots))
print()

# Show each active play
print('{:<6} {:<8} {:<18} {:<18} {:<5} {:<4}  First 32 bytes of play object'.format(
    'elem', 'cat', 'sub_addr', 'play_ptr', 'flag', 'u16s_0'))
print('-' * 110)

for sub_addr, obj_off, elem, cat, play_ptr, flag, play_data in sorted(active_plays, key=lambda x: (x[2], x[0])):
    hex_preview = ' '.join('{:02X}'.format(b) for b in play_data[:32]) if play_data else '(no data)'
    # Try to extract first few u16 values (potential play IDs)
    u16s = []
    for j in range(0, min(16, len(play_data)), 2):
        u16s.append(struct.unpack_from('<H', play_data, j)[0])
    print('{:<6} {:<8} 0x{:<16X} 0x{:<16X} {:<5} {}'.format(
        elem, cat, sub_addr, play_ptr, flag, hex_preview[:50]))

# ── Dump first 128 bytes of the first 3 unique play objects ──────────────────
print('\n=== PLAY OBJECT DUMPS (first 3 unique) ===')
seen = set()
count = 0
for _, _, _, cat, play_ptr, _, play_data in active_plays:
    if play_ptr in seen or not play_data:
        continue
    seen.add(play_ptr)
    count += 1
    if count > 3:
        break
    print('\nPlay object @ 0x{:X} (cat={}) - {} bytes:'.format(play_ptr, cat, len(play_data)))
    for i in range(0, min(0x80, len(play_data)), 16):
        row = play_data[i:i+16]
        hex_part = ' '.join('{:02X}'.format(b) for b in row)
        asc_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        u32s = [struct.unpack_from('<I', row, j)[0] for j in range(0, len(row)-3, 4)]
        print('  +0x{:03X}: {:<48}  {}  {}'.format(i, hex_part, asc_part,
              [v for v in u32s if 0 < v < 100000]))

# ── Show count fields we know about ──────────────────────────────────────────
print('\n=== KNOWN COUNT FIELDS IN OBJECT ===')
for off in [0x33C8, 0x33CC]:
    if off < len(obj):
        v = obj[off]
        print('  obj+0x{:04X}: u8 = {}'.format(off, v))

# Also check element 5 area (where 2->1 changes were seen)
print('\n  Element 5 area (around obj+0x33B0):')
for i in range(0x33A0, 0x3400, 16):
    if i >= len(obj): break
    row = obj[i:i+16]
    if any(b != 0 for b in row):
        hex_part = ' '.join('{:02X}'.format(b) for b in row)
        print('  obj+0x{:04X}: {}'.format(i, hex_part))

kernel32.CloseHandle(hproc)
