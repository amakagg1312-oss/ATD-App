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

# Read play strings
play_data = mem_read(hproc, play_string_base, 0x10000)

play_list = []
i = 0
while i < len(play_data) - 1:
    null_pos = play_data.find(b'\x00\x00', i)
    if null_pos == -1:
        break
    start = null_pos + 2
    if start % 2 != 0:
        start += 1
    next_null = play_data.find(b'\x00\x00', start)
    if next_null == -1:
        next_null = len(play_data)
    play_bytes = play_data[start:next_null]
    if len(play_bytes) >= 4:
        try:
            play_name = play_bytes.decode('utf-16-le', errors='replace').strip()
            if play_name and len(play_name) > 2:
                play_list.append((start, next_null, play_name))
        except:
            pass
    i = null_pos + 2

print('Indexed {} plays'.format(len(play_list)))

def find_play_by_offset(byte_offset):
    for start, end, name in play_list:
        if start == byte_offset:
            return name
    for start, end, name in play_list:
        if start <= byte_offset < end:
            return name
    aligned = byte_offset & ~1
    for start, end, name in play_list:
        if start == aligned:
            return name
    for delta in range(-10, 11):
        test_offset = byte_offset + delta
        for start, end, name in play_list:
            if start == test_offset:
                return name
    return None

# Try multiple potential playbook addresses
addresses_to_try = [
    0x2FFCA1910,  # Original found
    0x2FFCA1000,  # Slightly before
    0x2FFCA2000,  # After
    0x2FFC90000,  # Different region
    0x2FFCB0000,  # Different region
]

print('\n=== Searching for 76ers Playbook ===')

for base_addr in addresses_to_try:
    print('\n--- Trying base: {} ---'.format(hex(base_addr)))
    stride = 0x30
    plays = []
    
    for i in range(60):
        addr = base_addr + i * stride
        data = mem_read(hproc, addr, 4)
        if data:
            offset_val = struct.unpack('<I', data)[0]
            if offset_val and offset_val < 0x10000:
                play_name = find_play_by_offset(offset_val)
                if play_name:
                    plays.append('[{}] {}'.format(i, play_name))
    
    if plays:
        print('Found {} plays:'.format(len(plays)))
        for p in plays[:15]:
            print('  ' + p)
        if len(plays) > 15:
            print('  ... and {} more'.format(len(plays) - 15))

# Also search around original address for play-like patterns
print('\n=== Scanning around base 0x2FFCA1910 ===')
scan_range = 0x10000  # 64KB
data = mem_read(hproc, 0x2FFCA0000, scan_range)
if data:
    # Look for pointers that look like play offsets
    print('Scanning for valid play offsets...')
    found = []
    for i in range(0, len(data) - 4, 4):
        val = struct.unpack('<I', data[i:i+4])[0]
        if val and 0 < val < 0x10000:
            play = find_play_by_offset(val)
            if play:
                found.append((i, val, play))
    
    print('Found {} valid play offset entries'.format(len(found)))
    if found:
        # Group by potential array
        print('\nFirst 20 plays:')
        for off, val, name in found[:20]:
            print('  [{}] offset={}: {}'.format(hex(0x2FFCA0000 + off), val, name))

CloseHandle(hproc)