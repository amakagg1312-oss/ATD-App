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

def read_uint32(hproc, addr):
    data = mem_read(hproc, addr, 4)
    if data:
        return struct.unpack('<I', data)[0]
    return None

# Read the entire play string block
play_data = mem_read(hproc, play_string_base, 0x10000)

# Build a list of all plays with their start and end offsets
print('=== Building play index ===\n')

play_list = []  # List of (start, end, name)
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

# Function to find play by byte offset
def find_play_by_offset(byte_offset):
    # Exact match
    for start, end, name in play_list:
        if start == byte_offset:
            return name
    
    # Find the play that contains this offset
    for start, end, name in play_list:
        if start <= byte_offset < end:
            return name
    
    # Try aligned offset
    aligned = byte_offset & ~1
    for start, end, name in play_list:
        if start == aligned:
            return name
    
    # Try nearby offsets (within 10 bytes)
    for delta in range(-10, 11):
        test_offset = byte_offset + delta
        for start, end, name in play_list:
            if start == test_offset:
                return name
    
    return None

# Debug: check a few specific offsets
print('\n=== Debug: checking specific offsets ===\n')

test_offsets = [2714, 3034, 2561, 2252, 1352, 1133, 557, 742, 2591, 1245]
for off in test_offsets:
    play = find_play_by_offset(off)
    # Show raw bytes at this offset
    raw = mem_read(hproc, play_string_base + off, 40)
    decoded = raw.decode('utf-16-le', errors='replace').split('\x00')[0]
    print('  Offset {}: found="{}", raw_decoded="{}"'.format(off, play, decoded))

# Now extract the 60 plays
print('\n=== Extracting 76ers playbook (60 plays) ===\n')

base = 0x2FFCA1910
stride = 0x30
plays_60 = []

for i in range(60):
    addr = base + i * stride
    offset_val = read_uint32(hproc, addr)
    
    if offset_val and offset_val < 0x10000:
        play_name = find_play_by_offset(offset_val)
        if play_name:
            plays_60.append((i, play_name, offset_val))
            print('  [{}] {} (offset={})'.format(i, play_name, offset_val))
        else:
            print('  [{}] NOT FOUND (offset={})'.format(i, offset_val))
    else:
        print('  [{}] EMPTY'.format(i))

print('\nTotal valid plays: {}'.format(len(plays_60)))

# Save to file
output = {
    'base_address': hex(base),
    'plays': [{'index': idx, 'play_name': name, 'byte_offset': off} for idx, name, off in plays_60]
}

with open('D:\\project\\Playbook\\76ers_playbook.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print('\nSaved to D:\\project\\Playbook\\76ers_playbook.json')

CloseHandle(hproc)
