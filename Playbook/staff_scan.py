import sys, struct, json, pathlib
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playbook_scanner import (find_pid, get_module_base, mem_read, read_uint64,
                               GAME_EXE, PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

offsets_path = pathlib.Path('..') / 'nba2k26_generator' / '2k26_offsets.json'
with open(offsets_path) as f:
    offsets = json.load(f)
staff_rva    = offsets['base_pointers']['Staff']['address']
staff_stride = int(offsets['game_info']['staffSize'])
print('Staff RVA=0x{:X}  stride={}'.format(staff_rva, staff_stride))

staff_ptr_addr = module_base + staff_rva
staff_table    = struct.unpack('<Q', mem_read(hproc, staff_ptr_addr, 8))[0]
print('Staff table base=0x{:X}'.format(staff_table))
print()

# Also read the two "back-pointer" structs from the team at +0x0FE8 and +0x0FF0
table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]
team_data  = mem_read(hproc, table_base, TEAM_STRIDE)
ptr_FE8 = struct.unpack_from('<Q', team_data, 0x0FE8)[0]
ptr_FF0 = struct.unpack_from('<Q', team_data, 0x0FF0)[0]
ptr_12F8 = struct.unpack_from('<Q', team_data, 0x12F8)[0]

print('Back-pointer structs (team-related manager objects):')
for label, ptr in [('team+0x0FE8', ptr_FE8), ('team+0x0FF0', ptr_FF0), ('team+0x12F8', ptr_12F8)]:
    if not (0x100000000 < ptr < 0x7FF000000000):
        continue
    # Read 8KB from this struct
    big = mem_read(hproc, ptr, 8192)
    if not big:
        continue
    # Find small ints (1-200) and pointers
    items = []
    for j in range(0, len(big) - 3, 4):
        v = struct.unpack_from('<I', big, j)[0]
        if 1 <= v <= 200:
            items.append((j, v))
    # Also check for wstrings
    strings = []
    for j in range(0, min(512, len(big)) - 1, 2):
        raw = big[j:j+40]
        try:
            s = raw.decode('utf-16le', errors='ignore')
            null = s.find('\x00')
            s = s[:null] if null != -1 else s
            if len(s) >= 3 and s.replace(' ', '').replace('-', '').replace("'", '').isalpha():
                strings.append((j, s))
        except:
            pass
    print()
    print('  {} -> 0x{:X}'.format(label, ptr))
    if strings:
        print('    Strings: {}'.format(strings[:4]))
    if items:
        print('    Small ints (1-200): {}'.format(items[:12]))
    else:
        print('    No small ints found in first 8KB')
    # Show hex of first 64 bytes
    hex_s = ' '.join('{:02X}'.format(b) for b in big[:64])
    print('    First 64 bytes: {}'.format(hex_s))

print()
print('--- Staff entries ---')
for i in range(80):
    s_addr = staff_table + i * staff_stride
    d = mem_read(hproc, s_addr, staff_stride)
    if not d:
        break
    if all(b == 0 for b in d):
        continue
    # Find name (wstring)
    name = ''
    for off in range(0, 80, 8):
        try:
            candidate = d[off:off+40].decode('utf-16le', errors='ignore')
            null = candidate.find('\x00')
            candidate = candidate[:null] if null != -1 else candidate
            candidate = candidate.strip()
            if (len(candidate) >= 3 and
                    candidate.replace(' ', '').replace('-', '').replace("'", '').replace('.', '').isalpha()):
                name = candidate
                break
        except:
            pass
    # Find small ints that could be playbook IDs
    small = []
    for j in range(0, staff_stride - 3, 4):
        v = struct.unpack_from('<I', d, j)[0]
        if 1 <= v <= 200:
            small.append((j, v))
    print('  [{}] 0x{:X}  {:<20}  {}'.format(i, s_addr, repr(name), small[:6]))

kernel32.CloseHandle(hproc)
