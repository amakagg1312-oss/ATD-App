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

# Search for exact play NAME in memory - maybe stored differently
# Looking for "FIST 21 IVERSON" as display string

# Encode in UTF-16 (game display format)
play_search = "FIST 21 IVERSON".encode('utf-16-le') + b'\x00\x00'

print('=== Searching for exact play name in memory ===')

# Search various memory regions
search_regions = [
    (0x1000000, 0x10000000),  # Low memory  
    (0x2000000, 0x10000000),  
    (0x3000000, 0x10000000), 
    (0x140000000, 0x10000000),
]

count = 0
for base, size in search_regions:
    data = mem_read(hproc, base, size)
    if data:
        pos = data.find(play_search)
        while pos >= 0:
            count += 1
            if count <= 5:
                print('Found at {} + {}'.format(hex(base), pos))
            pos = data.find(play_search, pos + 2)
        if count > 0:
            print('Region {} total: {}'.format(hex(base), count))
            break

if count == 0:
    # Try ASCII
    play_search = b'FIST 21 IVERSON\x00'
    for base, size in search_regions:
        data = mem_read(hproc, base, size)
        if data:
            pos = data.find(b'FIST')
            if pos >= 0:
                print('FIST found at {}'.format(hex(base + pos)))

# The game might read from playdata file which I saw earlier - let's examine the playdata IFF more closely
# The Plays.playdata file from earlier - let's use the offsets from there

print('\n=== Checking playdata file references ===')

# Earlier we found playdata file at D:\PROJECT\PLAYBOOK\GAME FILES\PLAYDATA_EXTRACTED\PLAYS.PLAYDATA
# Check if this correlates with memory

CloseHandle(hproc)