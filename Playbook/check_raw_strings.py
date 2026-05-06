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

string_block = mem_read(hproc, 0x2FFCD8000, 0x40000)

# Check raw bytes at offsets we know work (4096, 4863, etc)
known_offsets = [4096, 4863, 4832, 712, 896, 1216, 2558]

print('Raw UTF-16 bytes at known offsets:')
for offset in known_offsets:
    if offset + 20 < len(string_block):
        raw = string_block[offset:offset+20]
        print('Offset {}: {}'.format(offset, raw.hex()))

# Try looking for FIST pattern anywhere in block
print('\nSearching for "FIST" in string block...')
search_for = b'FIST\x00\x00'
pos = string_block.find(search_for)
while pos >= 0:
    print('Found at offset {}'.format(pos))
    pos = string_block.find(search_for, pos + len(search_for))
    if pos > 0 and pos < 0x100:
        break

# Try "IVERS" (part of IVERSON)
print('\nSearching for "IVER" in string block...')
search_for2 = b'IVER\x00\x00'
pos2 = string_block.find(search_for2)
if pos2 >= 0:
    print('Found IVER at offset {}'.format(pos2))
else:
    # Try case insensitive
    for i in range(0, min(5000, len(string_block)), 2):
        if i+1 < len(string_block):
            w = struct.unpack('<H', string_block[i:i+2])[0]
            if w == 0:
                break
            # Check if all ASCII letters
            if 0x40 <= w <= 0x5A:
                pass

CloseHandle(hproc)