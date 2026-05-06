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

def find_play(off):
    for s, e, n in play_list:
        if s == off: return n
    for s, e, n in play_list:
        if s <= off < e: return n
    return None

# My output vs Screenshot BLOB_01 (plays 0-9 in screenshot):
print('=== My playbook vs Screenshot comparison ===')
base = 0x2FFCA19D0
stride = 0x30

# Screenshot shows: ["FIST 15 MIDDLE", "FIST 15 MIDDLE", "52 FLAT", "FIST 21 IVERSON", "FIST CHEST FLARE", "'06 POR FIST 15", "MIL FIST 34 DOWN SLIP", "FIST 64 STS", "'06 POR FIST 15", "'16 MEM PUNCH 5 WEAK"]
screenshot_shown = [
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

# Read first 10 from memory
memory_plays = []
for i in range(10):
    data = mem_read(hproc, base + i * stride, 4)
    if data:
        off = struct.unpack('<I', data)[0]
        name = find_play(off)
        memory_plays.append((i, off, name))
        print('[{:2d}] offset {:5d}: {}'.format(i, off, name))

# Match them
print('\n=== Finding indices matching screenshot plays ===')
for target in screenshot_shown:
    indices = []
    for i, off, mem_name in memory_plays:
        if mem_name and target in mem_name:
            indices.append(i)
            break
    if not indices:
        # Check if any substring matches
        for i, off, mem_name in memory_plays:
            if mem_name:
                # Check first word
                target_words = target.split()
                mem_words = mem_name.split()
                if any(tw in mem_name or mw in target for tw in target_words for mw in mem_words if len(mw) > 3):
                    indices.append(i)
                    break
    print('"{}" -> index {}'.format(target, indices[0] if indices else 'NOT FOUND'))

CloseHandle(hproc)