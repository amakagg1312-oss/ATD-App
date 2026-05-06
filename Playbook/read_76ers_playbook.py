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
play_string_base = 0x2FFCD8000  # Play name strings block
playbook_base = 0x2FFCA1910      # 76ers playbook array
stride = 0x30                   # 48 bytes per play entry

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

# Read the play string block to build index
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

print('=== Indexed {} plays from string block ==='.format(len(play_list)))

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

# Read 76ers playbook (60 plays)
print('\n=== Reading 76ers Playbook from Memory ===')
print('Base: {}'.format(hex(playbook_base)))
print('=' * 60)

plays = []
for i in range(60):
    addr = playbook_base + i * stride
    offset_val = read_uint32(hproc, addr)
    
    if offset_val and offset_val < 0x10000:
        play_name = find_play_by_offset(offset_val)
        if play_name:
            plays.append({'index': i, 'play_name': play_name, 'byte_offset': offset_val})
            print('[{:2d}] {}'.format(i, play_name))
        else:
            print('[{:2d}] <UNKNOWN offset={}>'.format(i, offset_val))
    else:
        print('[{:2d}] <EMPTY>'.format(i))

print('\n=== Total: {} plays found ==='.format(len(plays)))

# Save to file
output = {
    'source': 'memory',
    'team': '76ers',
    'play_string_base': hex(play_string_base),
    'playbook_base': hex(playbook_base),
    'stride': stride,
    'plays': plays
}

with open('D:\\project\\Playbook\\76ers_playbook_memory.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print('\nSaved to 76ers_playbook_memory.json')
CloseHandle(hproc)