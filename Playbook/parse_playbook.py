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

def read_uint32(hproc, addr):
    data = mem_read(hproc, addr, 4)
    if data:
        return struct.unpack('<I', data)[0]
    return None

# Read the play string block
play_data = mem_read(hproc, 0x2FFCD8000, 0x10000)

# Build offset -> play name map using byte offsets
offset_map = {}
i = 0
while i < len(play_data) - 1:
    null_pos = play_data.find(b'\x00\x00', i)
    if null_pos == -1:
        break
    play_bytes = play_data[i:null_pos]
    if len(play_bytes) > 4:  # At least 2 characters
        try:
            play_name = play_bytes.decode('utf-16-le', errors='replace')
            if play_name.strip():
                offset_map[i] = play_name.strip()
        except:
            pass
    i = null_pos + 2

def get_play(byte_offset):
    if byte_offset in offset_map:
        return offset_map[byte_offset][:50]
    return None

# Check what's at 0x2FFCA1910 specifically
print('Value at 0x2FFCA1910: {}'.format(read_uint32(hproc, 0x2FFCA1910)))
print('Value at 0x2FFCA1914: {}'.format(read_uint32(hproc, 0x2FFCA1914)))

# Read a larger area and find non-zero values
print('\n=== Scanning 0x2FFCA1800-0x2FFCA2000 for non-zero play offsets ===')
data = mem_read(hproc, 0x2FFCA1800, 0x800)
if data:
    for i in range(0, len(data), 4):
        val = struct.unpack_from('<I', data, i)[0]
        if val > 0 and val < 0x10000:
            name = get_play(val)
            if name:
                print('  0x{:X}: {} -> {}'.format(0x2FFCA1800 + i, val, name))
            else:
                # Check what's at this byte offset in play_data
                if val < len(play_data):
                    snippet = play_data[val:val+40]
                    try:
                        text = snippet.decode('utf-16-le', errors='replace')
                        print('  0x{:X}: {} -> (text: "{}")'.format(0x2FFCA1800 + i, val, text[:30]))
                    except:
                        print('  0x{:X}: {} -> (raw: {})'.format(0x2FFCA1800 + i, val, snippet[:20].hex()))

# Also check the area around 0x298C505E0 which had play-like values
print('\n=== Examining 0x298C505E0 area for playbook structure ===')
data = mem_read(hproc, 0x298C50500, 0x300)
if data:
    # Look for structure: maybe pairs of (play_id, category) or similar
    for i in range(0, len(data), 4):
        val = struct.unpack_from('<I', data, i)[0]
        if 0 < val < 12506:
            print('  0x{:X}: {} (possible play ID)'.format(0x298C50500 + i, val))

CloseHandle(hproc)
print('\nDone.')
