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

# Let's check 0x2ea90000 which has 1186 entries
# That's very close to ~1731 total plays in the game

play_catalog = 0x2ea90000

print('Checking play catalog at {}'.format(hex(play_catalog)))

# Read first 100 entries
data = mem_read(hproc, play_catalog, 0x1000)
if data:
    print('First 50 play offsets:')
    for i in range(50):
        offset_val = struct.unpack('<I', data[i*4:i*4+4])[0]
        if offset_val > 0:
            print('  [{}]: {} ({})'.format(i, offset_val, hex(offset_val)))

# Now try to find the string at one of these offsets
# The offset might be relative to THIS base - let's see what string is at one offset
print('\nSearching for play names...')

# Search for "SAS" in this region to find the string itself
search_for = b'SAS\x00'

# Try different bases
for base in [0x2EA90000, 0x2EA90000 + 0x100000, 0x2EB30000]:
    data = mem_read(hproc, base, 0x10000)
    if data:
        pos = data.find(search_for)
        if pos >= 0:
            print('Found "SAS" at {} + {}'.format(hex(base), hex(pos)))
            
            # Check what's around it - might be offset into string block from same base
            near_data = mem_read(hproc, base + pos - 20, 40)
            if near_data:
                print('Nearby:')
                for i in range(0, 40, 4):
                    val = struct.unpack('<I', near_data[i:i+4])[0]
                    if val > 0:
                        print('  +0x{:x}: {}'.format(i, hex(val)))

CloseHandle(hproc)