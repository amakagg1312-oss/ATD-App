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

# Let's find ANY valid play string in memory by looking at catalogs we found earlier
# The catalog at 0x2ea90000 - what's one of those offsets actually pointing to?

# Try looking up what play name is at offset from play catalog entry to string in memory
play_catalog = 0x2ea90000

# Get a sample offset
cat_data = mem_read(hproc, play_catalog, 100)
if cat_data:
    offset1 = struct.unpack('<I', cat_data[0:4])[0]
    print('Catalog[0] offset:', offset1, '({})'.format(hex(offset1)))
    
    # Try to resolve as pointer - offset might add to something
    # Try base + offset
    possible_bases = [0x2ea90000, 0x2eb00000, 0x2eb80000, 0x2ec00000]
    
    for base in possible_bases:
        try_addr = base + offset1
        data = mem_read(hproc, try_addr, 30)
        if data:
            # Check if looks like string
            has_valid = any(32 <= b <= 126 for b in data[:20])
            if has_valid:
                print('String at {}: {}'.format(hex(try_addr), data[:20]))
                break

# Try search for the SPECIFIC string "SAS FIST" again and look for offset reference nearby
search_str = b'SAS\x00'
print('\nSearching for SAS in memory...')

for base_check in [0x2e000000, 0x2eb00000, 0x2ec00000, 0x2ed00000]:
    data = mem_read(hproc, base_check, 0x100000)
    if data:
        pos = data.find(search_str)
        if pos >= 0:
            print('Found SAS at {} + {}'.format(hex(base_check), hex(pos)))
            print('Address: {}'.format(hex(base_check + pos)))
            
            # Try to find offset in catalog that references this
            near_data = mem_read(hproc, base_check + pos - 30, 50)
            if near_data:
                print('Nearby:')
                for i in range(0, 50, 4):
                    val = struct.unpack('<I', near_data[i:i+4])[0]
                    if 0 < val < 0x400000:
                        print('  +0x{:x}: {}'.format(i, hex(val)))
            break

CloseHandle(hproc)