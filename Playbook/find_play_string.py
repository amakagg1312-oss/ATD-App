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

import subprocess
result = subprocess.run(['powershell', '-Command', '(Get-Process NBA2K26).Id'], capture_output=True, text=True)
pid = int(result.stdout.strip())
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    if ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count)):
        return bytes(buf)
    return None

# Let's search the file offsets we found - these might map 1:1 to a different base
# The play names in game files are at offset ~0x3B0000-0x3E0000 in the original files

# Let's try mapping the file offset to a memory address
# Maybe it's offset from NBA2K26.exe base + specific RVA

# Try searching entire memory for string "SAS FIST 24 ANGLE" as UTF-16LE
search_for = b'S\x00A\x00S\x00 \x00F\x00I\x00S\x00T\x00 \x002\x004\x00 \x00A\x00N\x00G\x00L\x00E\x00'

print('Searching for "SAS FIST 24 ANGLE" as UTF-16LE string...')

search_regions = [
    (0x2D000000, 0x10000000),
]

for start, size in search_regions:
    print('Searching {} to {}...'.format(hex(start), hex(start+size)))
    chunk_size = 0x100000
    for chunk_start in range(start, start + size, chunk_size):
        data = mem_read(hproc, chunk_start, chunk_size)
        if data:
            pos = data.find(search_for)
            if pos >= 0:
                print('FOUND at {} + {}'.format(hex(chunk_start), hex(pos)))
                print('Address: {}'.format(hex(chunk_start + pos)))
                break
        if pos >= 0:
            break

# If not found as UTF-16, try ANSI
print('\nTrying ANSI search...')
search_ansi = b'SAS FIST 24 ANGLE'

for start, size in [(0x2D000000, 0x10000000)]:
    chunk_size = 0x100000
    for chunk_start in range(start, start + size, chunk_size):
        data = mem_read(hproc, chunk_start, chunk_size)
        if data:
            pos = data.find(search_ansi)
            if pos >= 0:
                print('FOUND at {} + {}'.format(hex(chunk_start), hex(pos)))
                print('Address: {}'.format(hex(chunk_start + pos)))
                break

CloseHandle(hproc)