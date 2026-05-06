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

# SAS FIST 24 ANGLE is at offset 0x3BBFB6 in game files
# Let's search memory for where this offset exists

target_offset = 0x3BBFB6
print('Searching for offset {} ({}) in memory...'.format(target_offset, hex(target_offset)))

# Search regions where playbook data might be
search_regions = [
    (0x2E000000, 0x200000),
    (0x2F000000, 0x200000),
    (0x30000000, 0x1000000),
    (0x31000000, 0x1000000),
]

for start, size in search_regions:
    data = mem_read(hproc, start, size)
    if data:
        # Look for the 32-bit value matching target_offset
        for i in range(0, size - 4, 4):
            val = struct.unpack('<I', data[i:i+4])[0]
            if val == target_offset:
                print('Found {} at {} + {}'.format(hex(target_offset), hex(start), hex(i)))
                print('Address: {}'.format(hex(start + i)))
                # Try reading around this to see if it's part of an array
                print('Surrounding values:')
                for j in range(max(0, i-20), min(size-4, i+40), 4):
                    val2 = struct.unpack('<I', data[j:j+4])[0]
                    if 0x300000 <= val2 <= 0x400000:  # Valid offset range
                        print('  +0x{:x}: {}'.format(j, hex(val2)))

CloseHandle(hproc)