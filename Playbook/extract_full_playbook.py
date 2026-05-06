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

def read_uint32(hproc, addr):
    data = mem_read(hproc, addr, 4)
    if data:
        return struct.unpack('<I', data)[0]
    return None

# Read the play string block
play_data = mem_read(hproc, 0x2FFCD8000, 0x10000)

# Parse plays
text = play_data.decode('utf-16-le', errors='replace')
plays = []
current_play = ''
current_start = 0
in_play = False

for i, char in enumerate(text):
    byte_offset = i * 2
    if char == '\x00':
        if in_play and len(current_play) > 3:
            plays.append((current_start, current_play.strip()))
        current_play = ''
        in_play = False
    elif char.isprintable() or char in ' \'-"':
        if not in_play:
            current_start = byte_offset
            in_play = True
        current_play += char
    else:
        if in_play and len(current_play) > 3:
            plays.append((current_start, current_play.strip()))
        current_play = ''
        in_play = False

offset_map = {}
for offset, name in plays:
    offset_map[offset] = name

def find_play(byte_offset):
    if byte_offset in offset_map:
        return offset_map[byte_offset]
    for delta in [-2, -1, 1, 2]:
        if byte_offset + delta in offset_map:
            return offset_map[byte_offset + delta]
    return None

# Search for more offset arrays in 0x2FFCA0000 to 0x2FFCBFFFF range
print('=== Scanning for offset arrays in 0x2FFCA0000-0x2FFCBFFFF ===\n')

# We know the arrays have 48-byte stride with play offsets at offset 0
# Scan in 4KB chunks, looking for sequences of valid play offsets
all_plays = []
found_arrays = []

pos = 0x2FFCA0000
end = 0x2FFCC0000
chunk_size = 0x1000

while pos < end:
    data = mem_read(hproc, pos, chunk_size)
    if data:
        # Look for sequences of valid play offsets with 48-byte stride
        for offset_in_chunk in range(0, chunk_size - 48, 4):
            val = struct.unpack_from('<I', data, offset_in_chunk)[0]
            if val and val < len(play_data):
                play_name = find_play(val)
                if play_name:
                    # Check if this is part of a sequence (check next entry at +48)
                    next_addr = pos + offset_in_chunk + 48
                    if next_addr < end:
                        next_val = read_uint32(hproc, next_addr)
                        if next_val and next_val < len(play_data):
                            next_play = find_play(next_val)
                            if next_play:
                                # Found a sequence, record this array
                                abs_addr = pos + offset_in_chunk
                                # Check if we already have this array
                                if not any(abs(abs_addr - a) < 48 for a in found_arrays):
                                    found_arrays.append(abs_addr)
    
    pos += chunk_size

print('Found {} potential array start addresses'.format(len(found_arrays)))

# Now extract plays from each array
for base in sorted(found_arrays):
    print('\n=== Array at 0x{:X} ==='.format(base))
    count = 0
    for i in range(100):
        addr = base + i * 0x30
        offset_val = read_uint32(hproc, addr)
        
        if offset_val and offset_val < len(play_data):
            play_name = find_play(offset_val)
            if play_name:
                all_plays.append({
                    'array': hex(base),
                    'index': i,
                    'byte_offset': offset_val,
                    'play_name': play_name
                })
                print('  [{}] {}'.format(i, play_name[:60]))
                count += 1
    
    if count == 0:
        print('  (no valid plays)')

print('\n\nTotal plays found: {}'.format(len(all_plays)))

# Save to file
output = {
    'total_plays': len(all_plays),
    'arrays': {}
}
for entry in all_plays:
    arr = entry['array']
    if arr not in output['arrays']:
        output['arrays'][arr] = []
    output['arrays'][arr].append({
        'index': entry['index'],
        'play_name': entry['play_name'],
        'byte_offset': entry['byte_offset']
    })

with open('D:\\project\\Playbook\\extracted_playbook.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print('\nSaved to D:\\project\\Playbook\\extracted_playbook.json')

CloseHandle(hproc)
