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

# What if we search via team playbook data the way the game expects?
# The value 0x226 (550) we found might NOT be an offset but just a small index
# And the actual play offset mapping happens elsewhere

# Let's try: find a playbook array that has many valid entries and work from there
print('Searching for playbook arrays...')

# The game has many plays - need array of many 4-byte entries
# Look for sequences of values in range 0x300000 to 0x400000 (millions)

found_arrays = []
for base in range(0x2D000000, 0x34000000, 0x50000):
    data = mem_read(hproc, base, 0x10000)
    if data:
        # Count entries in valid range
        valid = 0
        for i in range(0, 0x10000, 4):
            val = struct.unpack('<I', data[i:i+4])[0]
            if 0x300000 <= val <= 0x400000:
                valid += 1
        if valid >= 20:
            found_arrays.append((base, valid))

if found_arrays:
    for addr, count in found_arrays[:5]:
        print('Found {} valid entries at {}'.format(count, hex(addr)))
else:
    print('No valid playbook arrays found')

# Let's try searching for our play by actual string search in game memory
print('\nSearching for string "08 SAS" in memory...')
search_str = b'08 SAS'

for start in range(0x2D000000, 0x34000000, 0x500000):
    data = mem_read(hproc, start, 0x500000)
    if data:
        pos = data.find(search_str)
        if pos >= 0:
            print('Found at {} + {}'.format(hex(start), hex(pos)))
            print('Address: {}'.format(hex(start + pos)))
            
            # Try to find neighboring play entries
            # Read around that address to find offsets
            search_data = mem_read(hproc, start + pos - 100, 200)
            if search_data:
                print('Nearby area:')
                for i in range(0, 200, 4):
                    val = struct.unpack('<I', search_data[i:i+4])[0]
                    if 0x300000 <= val <= 0x400000:
                        print('  +0x{:x}: {}'.format(i, hex(val)))
            break

CloseHandle(hproc)