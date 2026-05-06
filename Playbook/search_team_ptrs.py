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
print('NBA2K26 PID: {}'.format(pid))

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

team_base = 0x2D1952A0  # Our team base
team_size = 5672

team_data = mem_read(hproc, team_base, team_size)

if not team_data:
    print('Failed to read team data')
    CloseHandle(hproc)
    exit()

print('Searching for any pointer to known playbook locations...')
print('Looking for values in range 0x2FFCA000 - 0x2FFD0000')

pointers_found = []
for offset in range(0, team_size, 4):
    val = struct.unpack('<I', team_data[offset:offset+4])[0]
    if 0x2FFCA000 <= val <= 0x2FFD0000:
        pointers_found.append((offset, val))

print('Found {} pointers'.format(len(pointers_found)))

if pointers_found:
    for offset, val in pointers_found[:20]:
        print('  team+0x{:x}: {}'.format(offset, hex(val)))
else:
    print('No pointers found in team to that region')
    
    # Try searching entire team area for ANY non-zero values that might be pointers
    print('\nAll non-zero values in team:')
    count = 0
    for offset in range(0, team_size, 4):
        val = struct.unpack('<I', team_data[offset:offset+4])[0]
        if val > 0x10000000:
            print('  team+0x{:x}: {}'.format(offset, hex(val)))
            count += 1
            if count > 30:
                break

CloseHandle(hproc)