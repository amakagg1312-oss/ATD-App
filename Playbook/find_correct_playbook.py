import struct
import ctypes
from ctypes import wintypes
import sys
import io
import json

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

# Plays from screenshot (first 10 from BLOB_01)
screenshot_plays = [
    "FIST 15 MIDDLE",
    "FIST 15 MIDDLE", 
    "52 FLAT",
    "FIST 21 IVERSON",
    "FIST CHEST FLARE",
    "'06 POR FIST 15",
    "MIL FIST 34 DOWN SLIP",
    "FIST 64 STS",
    "'06 POR FIST 15",
    "'16 MEM PUNCH 5 WEAK"
]

# Build play index
string_base = 0x2FFCD8000
str_data = mem_read(hproc, string_base, 0x10000)

play_list = []
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
                play_list.append((start, next_null, play_name))
        except:
            pass
    i = null_pos + 2

print('Indexed {} plays'.format(len(play_list)))

# Find target plays in memory
target_offsets = {}
for target in screenshot_plays:
    found = False
    for start, end, name in play_list:
        if target in name or name in target:
            target_offsets[target] = start
            print('Found "{}" at offset {}'.format(name, start))
            found = True
            break
    if not found:
        # Try partial
        for start, end, name in play_list:
            if target.split()[0] in name:
                print('Partial: "{}" matches "{}" at offset {}'.format(target, name, start))
                target_offsets[target] = start
                break

print('\nTarget offsets:')
for name, off in target_offsets.items():
    print('  {}: offset {}'.format(name, off))

# Now search for array containing these specific offsets in sequence
# We need to find a base where plays[0:10] would contain these offsets in some order

def find_play(off):
    for s, e, n in play_list:
        if s == off: return n
    return None

print('\n=== Searching for correct playbook base ===')

# The correct base should contain specific plays in order
test_bases = []
for base in range(0x2FFCA0000, 0x2FFCC0000, 0x1000):
    test_bases.append(base)

# More focused search around known areas
search_regions = []
for base in range(0x2FFCA1000, 0x2FFCB0000, 0x30):
    search_regions.append(base)

for test_base in search_regions[:100]:
    # Read first 10 plays
    plays = []
    for idx in range(10):
        data = mem_read(hproc, test_base + idx * 0x30, 4)
        if data:
            off = struct.unpack('<I', data)[0]
            if off and off < 0x10000:
                name = find_play(off)
                plays.append(name)
    
    if len(plays) >= 10:
        # Check if we have matches
        matches = 0
        for i, p in enumerate(plays[:10]):
            if p:
                for target in screenshot_plays:
                    if target in p:
                        matches += 1
                        break
        
        if matches >= 5:
            print('\nBase {} has {} matches:'.format(hex(test_base), matches))
            for i, p in enumerate(plays[:10]):
                print('  [{}] {}'.format(i, p))

CloseHandle(hproc)