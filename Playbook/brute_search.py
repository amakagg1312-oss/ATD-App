import struct
import ctypes
from ctypes import wintypes
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_ALL_ACCESS = 0x1F0FFF

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE
CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL
ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
ReadProcessMemory.restype = wintypes.BOOL

pid = 58172
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# The plays we KNOW exist in the 76ers playbook:
# Looking for sequence in screenshot order:
target_plays = [
    "FIST 15 MIDDLE",  # Could be different name
    "52 FLAT",
    "FIST 21 IVERSON", 
    "FIST CHEST FLARE",
    "'06 POR FIST 15",
    "MIL FIST 34 DOWN SLIP",
    "FIST 64 STS",
    "'16 MEM PUNCH 5 WEAK"
]

# Get actual offsets for plays we can find
string_base = 0x2FFCD8000
str_data = mem_read(hproc, string_base, 0x10000)

# Build simple index
def find_plays():
    plays = {}
    i = 0
    while i < len(str_data) - 1:
        null_pos = str_data.find(b'\x00\x00', i)
        if null_pos == -1:
            break
        start = null_pos + 2
        if start % 2 != 0:
            start += 1
        next_null = str_data.find(b'\x00\x00', start)
        if next_null == -1:
            next_null = len(str_data)
        play_bytes = str_data[start:next_null]
        if len(play_bytes) >= 4:
            try:
                play_name = play_bytes.decode('utf-16-le', errors='replace').strip()
                if play_name and len(play_name) > 2:
                    plays[start] = play_name
            except:
                pass
        i = null_pos + 2
    return plays

play_dict = find_plays()
print('Indexed {} plays'.format(len(play_dict)))

# Find actual offsets for our targets
targets = {
    "FIST 21 IVERSON": None,
    "FIST CHEST FLARE": None,
    "FIST 64 STS": None,
    "MIL FIST 34 DOWN SLIP": None,
    "'06 POR FIST 15 UP": None,
    "'16 MEM PUNCH 5 WEAK": None
}

for target in targets:
    for off, name in play_dict.items():
        if target in name or name in target:
            targets[target] = off
            print('Target "{}" at offset {}'.format(name, off))
            break

# Search more systematically - any address region containing ALL these play offsets
# Target offset set
target_offsets = set(targets.values()) - {None}
print('\nTarget offsets: {}'.format(target_offsets))

# Scan across larger memory region looking for ANY sequence containing our target plays
print('\n=== Brute force search for playbook with these plays ===')

# Check many base addresses with 60 entries
found_bases = []
stride = 0x30

for base in range(0x2FFCA0000, 0x2FFCC0000, 0x10):
    # Read 10 entries
    entries = []
    for i in range(10):
        data = mem_read(hproc, base + i * stride, 4)
        if data:
            off = struct.unpack('<I', data)[0]
            if off and off < 0x10000:
                entries.append(off)
    
    if len(entries) >= 10:
        # Check how many of our target offsets are present
        matches = sum(1 for o in entries if o in target_offsets)
        if matches >= 6:
            found_bases.append((base, matches, entries[:10]))

if found_bases:
    print('Found {} potential bases'.format(len(found_bases)))
    for base, matches, entries in found_bases[:10]:
        print('\nBase {} ({} matches):'.format(hex(base), matches))
        for i, off in enumerate(entries[:10]):
            name = play_dict.get(off, '???')
            print('  [{}] offset {}: {}'.format(i, off, name))
else:
    print('No matches found in that range')

# Try even wider search
print('\n=== Wider search around team data ===')
# Teams are typically around 0x2FFCA0000-0x2FFCF0000
for base in range(0x2FFCA0000, 0x2FFCF0000, 0x1000):
    data = mem_read(hproc, base, 1000)
    if data:
        # Look for strings
        try:
            decoded = data.decode('utf-16-le', errors='replace')
            if 'PHI' in decoded or '76ers' in decoded or 'FIST' in decoded[:100]:
                print('Interesting at {}: {}'.format(hex(base), decoded[:80]))
        except:
            pass

CloseHandle(hproc)