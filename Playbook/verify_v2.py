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
full_data = mem_read(hproc, play_string_base, 0x10000)

# Better parsing: 
# Each play string starts at a position where there's a 2-byte null before it
# and the bytes before that are not null
# We want the first string starting at each position

play_starts = set()
for i in range(2, len(full_data) - 4, 2):
    # Check for null-termination pattern: \x00\x00 followed by non-null
    if full_data[i] == 0 and full_data[i+1] == 0:
        if i+2 < len(full_data) and full_data[i+2] != 0:
            # This could be start of a new string
            # Validate: try to decode as UTF-16
            try:
                raw = full_data[i:i+100]
                decoded = raw.decode('utf-16-le', errors='replace')
                first_word = decoded.split('\x00')[0].strip()
                # Must have at least 3 chars and looks like a play name
                if len(first_word) >= 3 and any(c.isalpha() for c in first_word[:5]):
                    play_starts.add(i)
            except:
                pass

# Also check start of block (offset 0)
play_starts.add(0)

# Convert to sorted list
play_starts = sorted(list(play_starts))
print('Found {} potential play start positions'.format(len(play_starts)))

# Build dictionary: offset -> first play name
play_map = {}
for start in play_starts:
    try:
        raw = full_data[start:start+100]
        decoded = raw.decode('utf-16-le', errors='replace')
        first_play = decoded.split('\x00')[0].strip()
        if first_play and len(first_play) >= 3:
            play_map[start] = first_play
    except:
        pass

print('Built map with {} plays'.format(len(play_map)))

# Show first 30 to verify
print('\nFirst 30 plays from map:')
for i, (off, name) in enumerate(sorted(play_map.items())[:30]):
    print('  {:4d}: {}'.format(off, name))

# Now read playbook and look up each offset
print('\n=== Reading 76ers Playbook ===')

playbook_plays = []
for idx in range(60):
    addr = playbook_base + idx * stride
    data = mem_read(hproc, addr, 4)
    if data:
        offset = struct.unpack('<I', data)[0]
        
        # Exact match
        name = play_map.get(offset)
        
        # If not found, search nearby
        if not name:
            for delta in range(-8, 9):
                if offset + delta in play_map:
                    name = play_map[offset + delta]
                    break
        
        playbook_plays.append({'index': idx, 'offset': offset, 'name': name or '<NOT FOUND>'})
        
        if name:
            print('[{:2d}] {:5d}: {}'.format(idx, offset, name))
        else:
            print('[{:2d}] {:5d}: <NOT FOUND>'.format(idx, offset))

# Save
with open('D:\project\Playbook\76ers_verify_v2.json', 'w', encoding='utf-8') as f:
    json.dump(playbook_plays, f, indent=2, ensure_ascii=False)

print('\nSaved to 76ers_verify_v2.json')

# Compare with screenshot (first 10)
screenshot = ["FIST 64 STS", "CLE FIST 15 DRA", "SAS FIST 15 FLAT OU", "FIST 21 IVERSON", "FIST CHEST FLAR", 
              "'06 POR FIST 15 U", "MIL FIST 34 DOWN SLI", "FIST 64 ST", "'06 POR FIST 15 U", "'16 MEM PUNCH 5 WEA"]

print('\n=== COMPARISON ===')
match_count = 0
for i in range(10):
    if i < len(playbook_plays):
        mem_name = playbook_plays[i]['name']
        screen_name = screenshot[i]
        
        # Check if match (partial ok)
        is_match = mem_name and (screen_name in mem_name or mem_name in screen_name)
        if is_match:
            match_count += 1
            status = '✓ MATCH'
        else:
            status = '✗'
        
        print('[{}] Expected: {} | Got: {} | {}'.format(i, screen_name[:20], str(mem_name)[:20], status))

print('\nMatches: {}/10'.format(match_count))

CloseHandle(hproc)