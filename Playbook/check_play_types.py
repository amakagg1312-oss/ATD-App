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

# Let me think about this: we know offsets for plays exist in memory. 
# The game displays plays in order based on what?? 
# The "BLOB 01" through "BLOB 06" might show filtered results - maybe "BLOB" groups are based on play TYPE (like "all FIST plays", "all ISO plays", etc.)

# Let's verify if this is true - check type grouping in our arrays
# If BLOB=play type, let's check if our array has such grouping

# We know FIST plays should all be together? Check our array at 0x2FFCA19D0
base = 0x2FFCA19D0

print('=== Checking play grouping by type ===')

play_offsets = []
for i in range(60):
    data = mem_read(hproc, base + i * 0x30, 4)
    if data:
        off = struct.unpack('<I', data)[0]
        play_offsets.append((i, off))

# Get play names and group by first word
from collections import defaultdict
by_type = defaultdict(list)

# Read play names from string block 
str_base = 0x2FFCD8000
str_data = mem_read(hproc, str_base, 0x10000)

play_names = {}  # offset -> name
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
            name = play_bytes.decode('utf-16-le', errors='replace').strip()
            if name and len(name) > 2:
                play_names[start] = name
        except:
            pass
    i = null_pos + 2

print('Built name index for {} plays'.format(len(play_names)))

# Now check play types in the array
for idx, off in play_offsets:
    name = play_names.get(off)
    if not name:
        # Search nearby
        for delta in range(-10, 11):
            if off + delta in play_names:
                name = play_names[off + delta]
                break
    
    if name:
        first_word = name.split()[0]
        by_type[first_word].append((idx, name))

# Show play types
for ptype, plays in sorted(by_type.items(), key=lambda x: -len(x[1])):
    if len(plays) >= 3:
        print('\n{} ({} plays):'.format(ptype, len(plays)))
        # Show first few indices
        for idx, name in plays[:5]:
            print('  [{}] {}'.format(idx, name))

# Hmm if we have different groups - this explains the BLOB groups!
# BLOB groups = play type filters

print('\n=== So what shows in each BLOB? ===')
# BLOB 01 should show plays 0-9 sorted by some logic - probably by type or maybe the ORDER in menu

# What if BLOB_01 = plays indexed 0-9 in array? Let's see what's there
print('Plays at indices 0-9:')
for idx in range(10):
    off = play_offsets[idx][1] if idx < len(play_offsets) else 0
    name = play_names.get(off, '???')
    print('[{}] offset {}: {}'.format(idx, off, name[:20]))

CloseHandle(hproc)