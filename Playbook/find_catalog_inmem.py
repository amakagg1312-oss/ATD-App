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

# From playdata analysis: entries are 112 bytes, count at offset 0, first entry at 8
# Let's find play catalog and parse properly in memory

# Search for memory that has count=113 and entries at 112-byte intervals
# Looking for plays with valid string references (0x3Bxxxx - 0x3Exxxx)

print('Looking for play catalog in memory...')

for base in range(0x2D000000, 0x31000000, 0x100000):
    data = mem_read(hproc, base, 0x100000)
    if data:
        for offset in range(0, 0x100000 - 112, 112):
            # Check for count at this position
            count = struct.unpack('<I', data[offset:offset+4])[0]
            if count == 113:
                # Verify: first entry should have play string reference
                entry1_start = offset + 8
                if entry1_start + 112 < len(data):
                    # Find string reference in entry
                    entry1 = data[entry1_start:entry1_start+112]
                    has_ref = False
                    for i in range(0, 112, 4):
                        val = struct.unpack('<I', entry1[i:i+4])[0]
                        if 0x3B0000 <= val <= 0x3E0000:
                            has_ref = True
                            break
                    
                    if has_ref:
                        print('FOUND: {} + {}'.format(hex(base), hex(offset)))
                        print('  Contains play catalog with count=113')
                        break

CloseHandle(hproc)