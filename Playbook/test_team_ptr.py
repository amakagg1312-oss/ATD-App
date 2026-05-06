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

team_addr = 0x2A82E17D0
team_data = mem_read(hproc, team_addr, 5672)

# Let's focus on offset around 0x464 which has value 0x2e303030
print('Examining team+0x464:')
val_464 = struct.unpack('<I', team_data[0x464:0x468])[0]
print('  value: {}'.format(hex(val_464)))

# ASCII decode
ascii_bytes = struct.pack('<I', val_464)
print('  ASCII: {}'.format(ascii_bytes))

# Try writing test at potential playbook locations in team
# Let's look at offset areas that could be pointers
print('\nSearching for array pointers in team...')

pointers = []
for offset in range(0, 5672, 4):
    val = struct.unpack('<I', team_data[offset:offset+4])[0]
    # Any value in higher memory ranges
    if 0x20000000 <= val <= 0x34000000 and val % 4 == 0:
        pointers.append((offset, val))

print('Found {} potential pointers'.format(len(pointers)))
for offset, val in pointers[:15]:
    print('  team+0x{:x}: {}'.format(offset, hex(val)))

# Try writing to first few to test
print('\nTesting writes...')
test_val = 550

for offset, val in pointers[:3]:
    test_addr = team_addr + offset
    if mem_write(hproc, test_addr, struct.pack('<I', test_val)):
        verify = mem_read(hproc, test_addr, 4)
        if verify and struct.unpack('<I', verify)[0] == test_val:
            print('  SUCCESS at team+0x{:x}! Check game!'.format(offset))

CloseHandle(hproc)