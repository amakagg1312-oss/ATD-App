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
playbook_base = 0x2FFCA1910
stride = 0x30

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# Read string block
data = mem_read(hproc, play_string_base, 0x10000)

# Use the exact same method as find_60_plays.py
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

# Show some examples
print('\nFirst 20 plays:')
for start, end, name in play_list[:20]:
    print('  {:4d}: {}'.format(start, name))

def find_play_by_offset(byte_offset):
    # Exact match
    for start, end, name in play_list:
        if start == byte_offset:
            return name
    # Containment
    for start, end, name in play_list:
        if start <= byte_offset < end:
            return name
    # Aligned
    aligned = byte_offset & ~1
    for start, end, name in play_list:
        if start == aligned:
            return name
    # Nearby
    for delta in range(-10, 11):
        test_offset = byte_offset + delta
        for start, end, name in play_list:
            if start == test_offset:
                return name
    return None

# Read playbook
print('\n=== Reading 76ers Playbook ===')

playbook_plays = []
for idx in range(60):
    addr = playbook_base + idx * stride
    data_addr = mem_read(hproc, addr, 4)
    if data_addr:
        offset_val = struct.unpack('<I', data_addr)[0]
        
        if offset_val and offset_val < 0x10000:
            play_name = find_play_by_offset(offset_val)
            if play_name:
                playbook_plays.append({'index': idx, 'offset': offset_val, 'name': play_name})
                print('[{:2d}] {:5d}: {}'.format(idx, offset_val, play_name))
            else:
                playbook_plays.append({'index': idx, 'offset': offset_val, 'name': '<NOT FOUND>'})
                print('[{:2d}] {:5d}: <NOT FOUND>'.format(idx, offset_val))
        else:
            print('[{:2d}] EMPTY'.format(idx))

# Save
output = {'base': hex(playbook_base), 'plays': playbook_plays}
with open(r'D:\project\Playbook\76ers_verify_v3.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print('\nSaved to 76ers_verify_v3.json')

# Compare with screenshot
screenshot = ["FIST 64 STS", "CLE FIST 15 DRA", "SAS FIST 15 FLAT OU", "FIST 21 IVERSON", "FIST CHEST FLAR", 
              "'06 POR FIST 15 U", "MIL FIST 34 DOWN SLI", "FIST 64 ST", "'06 POR FIST 15 U", "'16 MEM PUNCH 5 WEA"]

print('\n=== COMPARISON WITH SCREENSHOT ===')
matches = 0
for i in range(10):
    if i < len(playbook_plays):
        got = playbook_plays[i].get('name', '')
        expect = screenshot[i]
        
        if got and (expect in got or got in expect):
            matches += 1
            status = 'MATCH'
        else:
            status = 'DIFF'
        
        print('[{}] Expected: {:22s} | Got: {:22s} | {}'.format(i, expect[:22], str(got)[:22], status))

print('\nResult: {}/10 matches'.format(matches))

CloseHandle(hproc)