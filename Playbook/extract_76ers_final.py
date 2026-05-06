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
playbook_base = 0x2FFCA19D0  # CORRECT BASE!
stride = 0x30

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

# Read playbook at CORRECT address
print('\n=== 76ers Playbook at {} ==='.format(hex(playbook_base)))
print('=' * 60)

all_plays = []
for idx in range(60):
    addr = playbook_base + idx * stride
    data = mem_read(hproc, addr, 4)
    if data:
        off = struct.unpack('<I', data)[0]
        if off and off < 0x10000:
            name = find_play(off)
            all_plays.append({'index': idx, 'offset': off, 'name': name})
            print('[{:2d}] {:5d}: {}'.format(idx, off, name))
        else:
            all_plays.append({'index': idx, 'offset': off, 'name': '<EMPTY>'})
            print('[{:2d}] <EMPTY>'.format(idx))

# Save to file
output = {
    'source': 'memory',
    'team': '76ers',
    'base_address': hex(playbook_base),
    'stride': stride,
    'play_string_base': hex(play_string_base),
    'plays': all_plays
}

with open(r'D:\project\Playbook\76ers_final.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print('\nSaved to 76ers_final.json')

# Compare with screenshot plays
print('\n=== COMPARISON WITH SCREENSHOT ===')
screenshot = [
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

matches = 0
for i in range(10):
    got = all_plays[i]['name'] if i < len(all_plays) else ''
    exp = screenshot[i]
    
    if got and (exp in got or got in exp):
        matches += 1
        status = '✓'
    else:
        status = '✗'
    
    print('[{}] {} | {} | {}'.format(i, exp[:20], str(got)[:20], status))

print('\nResult: {}/10 matches'.format(matches))

CloseHandle(hproc)