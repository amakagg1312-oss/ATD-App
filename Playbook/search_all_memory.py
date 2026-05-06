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
WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL

pid = 58172
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# The playbook must be stored somewhere in the team data when used by roster
# Try searching ALL of game memory for playbook references

# Search our playbook addresses in a large region
# Start from lower game memory
game_bases = [0x100000, 0x2D000000, 0x2FF00000]

print('=== Searching all game memory ===')

search_bytes = [
    b'\xd0\x19\xca\x2f',  # 0x2FFCA19D0
    b'\x10\x19\xca\x2f',  # 0x2FFCA1910
    b'\x00\x18\xca\x2f',  # 0x2FFCA1800 (approx)
]

for search_bytes in [b'\xd0\x19\xca\x2f']:
    print('Searching for {}'.format(repr(search_bytes)))
    
    total = 0
    for base in [0x2D000000, 0x2FFC0000, 0x2FFB0000, 0x140000000]:
        try:
            size = 0x2000000
            data = mem_read(hproc, base, size)
            if data:
                pos = data.find(search_bytes)
                while pos >= 0:
                    total += 1
                    print('  Found at {} + {}'.format(hex(base), pos))
                    pos = data.find(search_bytes, pos + 1)
        except:
            pass
    
    print('  Total: {}'.format(total))

# If we can't find a reference, let's try WRITING to multiple addresses
# to find if ANY one works

print('\n=== Writing to ALL possible playbook addresses ===')

test_plays = [
    (0x2FFCA1910, 550),  # Original base, FIST 21 IVERSON
    (0x2FFCA19D0, 550),  # Alternate base
]

for addr, off in test_plays:
    data = struct.pack('<I', off)
    written = ctypes.c_size_t(0)
    result = WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, 4, ctypes.byref(written))
    if result:
        print('Wrote to {}'.format(hex(addr)))

CloseHandle(hproc)