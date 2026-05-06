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
play_string_base = 0x2FFCD8000

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# Build play index
data = mem_read(hproc, play_string_base, 0x10000)

play_list = []
i = 0
while i < len(data) - 1:
    null_pos = data.find(b'\x00\x00', i)
    if null_pos == -1:
        break
    start = null_pos + 2
    if start % 2 != 0:
        start += 1
    next_null = data.find(b'\x00\x00', start)
    if next_null == -1:
        next_null = len(data)
    play_bytes = data[start:next_null]
    if len(play_bytes) >= 4:
        try:
            play_name = play_bytes.decode('utf-16-le', errors='replace').strip()
            if play_name and len(play_name) > 2:
                play_list.append((start, next_null, play_name))
        except:
            pass
    i = null_pos + 2

print('Indexed {} plays'.format(len(play_list)))

def find_play(byte_offset):
    for start, end, name in play_list:
        if start == byte_offset:
            return name
    for start, end, name in play_list:
        if start <= byte_offset < end:
            return name
    for delta in range(-10, 11):
        for start, end, name in play_list:
            if start == byte_offset + delta:
                return name
    return None

# Known plays from screenshot (that would match if offset was correct)
target_plays = ["FIST 64 STS", "CLE FIST 15 DRA", "SAS FIST 15 FLAT OU", "FIST 21 IVERSON", "FIST CHEST FLAR", 
                "'06 POR FIST 15 U", "MIL FIST 34 DOWN SLI", "'16 MEM PUNCH 5 WEA"]

# Find their offsets
target_offsets = {}
for target in target_plays:
    for start, end, name in play_list:
        if target in name or name in target:
            target_offsets[target] = start
            break

print('\nTarget play offsets:')
for name, off in target_offsets.items():
    print('  {}: {}'.format(name, off))

# Now scan around 0x2FFCA1910 to find matches for these plays
print('\n=== Scanning around base 0x2FFCA1910 ===')

base_scan = 0x2FFCA1910
stride = 0x30

# Check different offsets from known offset
for base_offset in [0, -0x30, -0x60, -0x90, -0xC0, 0x30, 0x60, 0x90, 0xC0, -0x100, 0x100]:
    test_base = base_scan + base_offset
    print('\n--- Base: {} ({:+x}) ---'.format(hex(test_base), base_offset))
    
    found_plays = []
    for idx in range(60):
        addr = test_base + idx * stride
        data = mem_read(hproc, addr, 4)
        if data:
            off = struct.unpack('<I', data)[0]
            if off and off < 0x10000:
                name = find_play(off)
                found_plays.append(name)
    
    # Compare first 10 with screenshot targets
    matches = 0
    for i, expected in enumerate(target_plays[:10]):
        if i < len(found_plays) and found_plays[i]:
            if expected in found_plays[i]:
                matches += 1
    
    if matches > 0:
        print('  First 10: {}'.format([p[:18] if p else 'None' for p in found_plays[:10]]))
        print('  MATCHES: {}/10'.format(matches))

# Also try stride variations
for test_stride in [0x30, 0x28, 0x38, 0x40, 0x20]:
    test_base = 0x2FFCA1910
    print('\n--- Base: {} stride: {} ---'.format(hex(test_base), test_stride))
    
    found = []
    for idx in range(60):
        addr = test_base + idx * test_stride
        data = mem_read(hproc, addr, 4)
        if data:
            off = struct.unpack('<I', data)[0]
            if off and off < 0x10000:
                name = find_play(off)
                found.append(name)
    
    matches = 0
    for i, exp in enumerate(target_plays[:10]):
        if i < len(found) and found[i]:
            if exp in found[i]:
                matches += 1
    
    if matches > 0:
        print('  Matches: {}/10 = {}'.format(matches, [p[:15] if p else '' for p in found[:10]]))

CloseHandle(hproc)