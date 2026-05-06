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
playbook_base = 0x2FFCA1910  # Our candidate
stride = 0x30

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# Build complete play index
play_data = mem_read(hproc, play_string_base, 0x10000)
print('Play data block size: {} bytes'.format(len(play_data)))

play_dict = {}  # offset -> name
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
                play_dict[start] = play_name
        except:
            pass
    i = null_pos + 2

print('Indexed {} plays'.format(len(play_dict)))

# Target plays from screenshot (first 10)
target_plays_from_screenshot = [
    "FIST 64 STS",
    "CLE FIST 15 DRA",
    "SAS FIST 15 FLAT OU", 
    "FIST 21 IVERSON",
    "FIST CHEST FLAR",
    "'06 POR FIST 15 U",
    "MIL FIST 34 DOWN SLI",
    "FIST 64 ST",
    "'06 POR FIST 15 U",
    "'16 MEM PUNCH 5 WEA"
]

# Find these in our play dictionary
print('\n=== Finding screenshot plays in memory ===')
target_offsets = {}
for name in target_plays_from_screenshot:
    found = False
    for offset, play_name in play_dict.items():
        if play_name.startswith(name) or name in play_name:
            print('Found: "{}" at offset {}'.format(play_name, offset))
            target_offsets[name] = offset
            found = True
            break
    if not found:
        print('NOT FOUND: "{}"'.format(name))

# Now read the 76ers playbook and see which offsets we get
print('\n=== Reading 76ers playbook at {} ==='.format(hex(playbook_base)))

read_offsets = []
for i in range(60):
    addr = playbook_base + i * stride
    data = mem_read(hproc, addr, 4)
    if data:
        offset_val = struct.unpack('<I', data)[0]
        read_offsets.append(offset_val)
        if offset_val and offset_val < 0x10000:
            name = play_dict.get(offset_val, '<UNKNOWN>')
            print('[{:2d}] offset={:4d}: {}'.format(i, offset_val, name))
        else:
            print('[{:2d}] offset={:5d}: <EMPTY>'.format(i, offset_val))

print('\n=== Comparison ===')
print('Screenshot plays and their actual offsets:')
for i, name in enumerate(target_plays_from_screenshot[:10]):
    actual_offset = target_offsets.get(name)
    read_offset = read_offsets[i] if i < len(read_offsets) else None
    
    match = 'MATCH' if actual_offset == read_offset else 'MISMATCH'
    print('[{}] "{}"'.format(i, name))
    print('    Expected offset: {}'.format(actual_offset))
    print('    Found offset:    {}'.format(read_offset))
    print('    Status: {}'.format(match))

CloseHandle(hproc)