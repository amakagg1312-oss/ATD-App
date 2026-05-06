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

def find_play(off):
    for s, e, n in play_list:
        if s == off:
            return n
    for s, e, n in play_list:
        if s <= off < e:
            return n
    return None

print('=== FINAL COMPARISON ===')
print('')
print('Screenshot BLOB 01 plays (in order):')
print('  [0] FIST 15 MIDDLE')
print('  [1] FIST 15 MIDDLE')
print('  [2] 52 FLAT')
print('  [3] FIST 21 IVERSON')
print('  [4] FIST CHEST FLARE')
print('  [5] (06 POR) FIST 15')
print('  [6] MIL FIST 34 DOWN SLIP')
print('  [7] FIST 64 STS')
print('  [8] (06 POR) FIST 15')
print('  [9] (16 MEM) PUNCH 5 WEAK')

# Test addresses
test_addresses = [
    ('0x2FFCA1910', 0x2FFCA1910),
    ('0x2FFCA19D0', 0x2FFCA19D0),
]

for name, addr in test_addresses:
    print('')
    print('=== BASE: {} ==='.format(name))
    for idx in range(10):
        data = mem_read(hproc, addr + idx * 0x30, 4)
        if data:
            off = struct.unpack('<I', data)[0]
            play_name = find_play(off)
            print('[{:2d}] {:5d}: {}'.format(idx, off, play_name))
    print('')

# Also show unique play types
print('=== Unique plays in first 10 ===')
unique = []
for idx in range(10):
    data = mem_read(hproc, 0x2FFCA19D0 + idx * 0x30, 4)
    if data:
        off = struct.unpack('<I', data)[0]
        play_name = find_play(off)
        if play_name and play_name not in unique:
            unique.append(play_name)
            
for p in unique:
    print('  - {}'.format(p))

CloseHandle(hproc)