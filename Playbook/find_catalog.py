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

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    if WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count)):
        return write_count.value == len(data)
    return False

# Find the global play catalog - we found earlier at ~0x2ea90000 with ~1700 entries
# Each entry has: playID (4 bytes), maybe some metadata

# Let's read and understand the structure at 0x2ea90000
catalog_base = 0x2ea90000
cat_data = mem_read(hproc, catalog_base, 0x1000)

if cat_data:
    print('Play Catalog at {}'.format(hex(catalog_base)))
    print('\nFirst 20 catalog entries (play IDs):')
    for i in range(20):
        entry = struct.unpack('<I', cat_data[i*4:i*4+4])[0]
        if entry > 0:
            print('  [{}]: {} ({})'.format(i, entry, hex(entry)))

# The play catalog seems to have IDs directly (maybe 0,1,2... or game indices)
# But our file offsets were in millions (0x3BBFB6 etc)

# Let me search for another catalog structure - maybe a mapping from file offset to catalog ID
print('\nSearching for catalog with IDs matching our file offset patterns...')

# Our file offsets: 0x3BBFB6 (3937238), 0x3DCC58 (4037208), etc.
# Let's search in a different way - find the second structure after the play strings

# Search for catalog 2 - play names
search_areas = [0x2eb00000, 0x2ec00000, 0x2ed00000]

for start in search_areas:
    data = mem_read(hproc, start, 0x10000)
    if data:
        # Look for structure with count + entries pattern
        for i in range(0, 0x10000, 0x100):
            count = struct.unpack('<I', data[i:i+4])[0]
            if 1000 <= count <= 2000:
                # This looks like the play count!
                print('Found catalog at {} + {} = {}'.format(hex(start), hex(i), hex(start+i)))
                print('  Play count: {}'.format(count))
                
                # Read a few play entries
                print('  First few play entries:')
                for j in range(min(10, count)):
                    entry = struct.unpack('<I', data[i+4+j*4:i+4+(j+1)*4])[0]
                    print('    [{}]: {}'.format(j, hex(entry)))
                break

CloseHandle(hproc)