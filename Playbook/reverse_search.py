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

# Search: find byte sequence D0 19 CA 2F (little-endian of 0x2FFCA19D0)
# D0 19 CA 2F = \xd0\x19\xca\x2f
search_bytes = b'\xd0\x19\xca\x2f'

print('=== Searching for playbook reference ===')

search_base = 0x2D000000
search_size = 0x400000

data = mem_read(hproc, search_base, search_size)
if data:
    pos = data.find(search_bytes)
    count = 0
    while pos >= 0:
        count += 1
        if count <= 10:
            addr = search_base + pos
            print('Ref {} at {}'.format(count, hex(addr)))
        pos = data.find(search_bytes, pos + 1)
    
    print('Total: {} references'.format(count))

# Also find other playbook references
search2 = b'\x10\x19\xca\x2f'  # 0x2FFCA1910
pos = data.find(search2)
if pos >= 0:
    print('\nAlso found ref to 0x2FFCA1910 at {}'.format(hex(search_base + pos)))

CloseHandle(hproc)