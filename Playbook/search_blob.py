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

# Let's search for the BLOB play ID format in memory
# Looking for strings like "76ers_BLOB_01"
searches = [
    b'BLOB',
    b'76ers',
]

# Search in different memory regions
print('=== Searching for BLOB references ===')

# Try searching in the playbook data region
test_regions = [
    (0x2FFCA0000, 0x20000),  # Around playbook area
    (0x2FFCD0000, 0x20000),  # Around play string area
    (0x2FF800000, 0x100000),  # Larger area
]

for base, size in test_regions:
    data = mem_read(hproc, base, size)
    if data:
        for search in searches:
            pos = data.find(search)
            if pos >= 0:
                print('Found {} at offset {} from base {}'.format(search, pos, hex(base)))
                # Print context
                start = max(0, pos - 20)
                end = min(len(data), pos + 40)
                context = data[start:end]
                try:
                    decoded = context.decode('utf-16-le', errors='replace')
                    print('  Context: {}'.format(repr(decoded[:50])))
                except:
                    pass

# Also read full 64KB around our known playbook area and scan for patterns
print('\n=== Full scan around playbook ===')
play_data = mem_read(hproc, 0x2FFCA0000, 0x20000)

# Build play lookup first
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

def find_play(b):
    for s, e, n in play_list:
        if s == b: return n
    for s, e, n in play_list:
        if s <= b < e: return n
    return None

# Now scan the playbook region at stride 0x30 looking for our plays
# This is the ORIGINAL base but also include stride variations

# Check if BLOB index blocks might exist elsewhere
print('\n=== Looking for patterns ===')

# Try: the game uses BLOB_01 = plays 0-9, BLOB_02 = 10-19, etc.
# Check if there's a mapping elsewhere in memory

# Scan for sequences containing our first 10 plays within small region
for base_test in [0x2FFCA1800, 0x2FFCA19D0, 0x2FFCA1A00, 0x2FFCA1B00]:
    print('\n--- At {} ---'.format(hex(base_test)))
    # Read 10 * 0x30 = 300 bytes = 10 plays
    for idx in range(10):
        test_addr = base_test + idx * 0x30
        raw = mem_read(hproc, test_addr, 4)
        if raw:
            off = struct.unpack('<I', raw)[0]
            if off and off < 0x10000:
                name = find_play(off)
                print('  [{}] offset {}: {}'.format(idx, off, name))

CloseHandle(hproc)