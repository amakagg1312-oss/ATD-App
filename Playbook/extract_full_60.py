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

# Build play index first
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

# Now let's carefully check my known working address 0x2FFCA19D0
# I want to compare its FIRST 10 plays with what's actually in the screenshot

# Known plays from screenshot BLOB_01 (indices 0-9):
# FIST 15 MIDDLE, FIST 15 MIDDLE, 52 FLAT, FIST 21 IVERSON, FIST CHEST FLARE, '06 POR FIST 15, MIL FIST 34 DOWN SLIP, FIST 64 STS, '06 POR FIST 15, '16 MEM PUNCH 5 WEAK

# Let me check ALL offsets in the playbook at 0x2FFCA19D0
base = 0x2FFCA19D0
stride = 0x30

print('\n=== Full playbook at {} ==='.format(hex(base)))

all_offsets = []
for i in range(60):
    data = mem_read(hproc, base + i * stride, 4)
    if data:
        off = struct.unpack('<I', data)[0]
        name = find_play(off)
        all_offsets.append((i, off, name))
        if i < 15 or (i >= 50):
            print('[{:2d}] offset {:5d}: {}'.format(i, off, name))

# Save full list
print('\n=== Writing full 60 to file ===')
import json
output = {
    'base': hex(base),
    'stride': stride,
    'plays': [{'index': i, 'offset': off, 'name': n} for i, off, n in all_offsets]
}
with open(r'D:\project\Playbook\76ers_full_memory.json', 'w') as f:
    json.dump(output, f, indent=2)

print('Saved to 76ers_full_memory.json')

# Now let's identify what we have vs screenshot
print('\n=== Identifying specific play offsets in memory ===')
# I found: FIST 21 IVERSON at 550, FIST CHEST FLARE at 712, FIST 64 STS at 2246/2252, MIL FIST 34 DOWN SLIP at 896

for target_offset, target_name in [(550, "FIST 21 IVERSON"), (712, "FIST CHEST FLARE"), (2246, "FIST 64 STS"), (896, "MIL FIST 34")]:
    if target_offset in [off for i, off, n in all_offsets]:
        indices = [i for i, off, n in all_offsets if off == target_offset]
        print('"{}" at offset {} is at playbook indices: {}'.format(target_name, target_offset, indices))

# Find where '16 MEM PUNCH 5 WEAK' is (offset 1216)
mem_punch_off = None
for s, e, n in play_list:
    if "MEM PUNCH 5 WEAK" in n:
        mem_punch_off = s
        break

if mem_punch_off:
    indices = [i for i, off, n in all_offsets if off == mem_punch_off]
    print("'16 MEM PUNCH 5 WEAK' at offset {} at indices: {}".format(mem_punch_off, indices))

CloseHandle(hproc)