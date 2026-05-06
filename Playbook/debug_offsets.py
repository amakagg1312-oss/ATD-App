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

# Read the play string block
play_data = mem_read(hproc, 0x2FFCD8000, 0x10000)

# Find "MEM ISO 3 GO" in the raw data
search = b'M\x00E\x00M\x00 \x00I\x00S\x00O\x00 \x003\x00 \x00G\x00O\x00'
pos = play_data.find(search)
print('Found "MEM ISO 3 GO" at byte offset: {}'.format(pos))

# Show the raw bytes around this position
if pos >= 0:
    snippet = play_data[pos:pos+40]
    print('Raw bytes: {}'.format(snippet.hex()))
    
    # Find the null terminator after this play
    null_pos = play_data.find(b'\x00\x00', pos)
    print('Null terminator at: {}'.format(null_pos))
    
    # Extract the play name
    if null_pos >= 0:
        play_bytes = play_data[pos:null_pos]
        play_name = play_bytes.decode('utf-16-le', errors='replace')
        print('Play name: "{}"'.format(play_name))
        print('Play length: {} bytes'.format(null_pos - pos))

# Now let's see what offsets the parser found
print('\n=== Parser offsets ===')
offset_map = {}
i = 0
while i < len(play_data) - 1:
    null_pos = play_data.find(b'\x00\x00', i)
    if null_pos == -1:
        break
    play_bytes = play_data[i:null_pos]
    if len(play_bytes) > 4:
        try:
            play_name = play_bytes.decode('utf-16-le', errors='replace')
            if play_name.strip():
                offset_map[i] = play_name.strip()
                if 'MEM ISO 3 GO' in play_name:
                    print('  Found "MEM ISO 3 GO" at parser offset: {}'.format(i))
        except:
            pass
    i = null_pos + 2

print('Total plays parsed: {}'.format(len(offset_map)))

# Check if offset 156 is in the map
print('\nOffset 156 in map: {}'.format(156 in offset_map))
if 156 in offset_map:
    print('  Value: "{}"'.format(offset_map[156]))

# Find the closest offset to 156
closest = min(offset_map.keys(), key=lambda x: abs(x - 156))
print('Closest offset to 156: {} -> "{}"'.format(closest, offset_map[closest][:40]))

CloseHandle(hproc)
