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

# 76ers team address
team_addr = 0x2A82E17D0
team_size = 5672

team_data = mem_read(hproc, team_addr, team_size)

if not team_data:
    print('Failed to read team')
    CloseHandle(hproc)
    exit()

print('76ers team at {}'.format(hex(team_addr)))
print('Team size: {} bytes'.format(team_size))

# Search for values in the playbook region (0x2E0xxxxx - current loaded playbook area)
print('\nSearching for pointers to playbook area (0x2E0xxxxx - 0x300xxxxx)...')

playbook_ptrs = []
for offset in range(0, team_size, 4):
    val = struct.unpack('<I', team_data[offset:offset+4])[0]
    if 0x2E000000 <= val <= 0x31000000:
        playbook_ptrs.append((offset, val))

print('Found {} playbook pointers'.format(len(playbook_ptrs)))

if playbook_ptrs:
    for offset, val in playbook_ptrs[:10]:
        print('  team+0x{:x}: {}'.format(offset, hex(val)))
else:
    print('No pointers to that region. Search for any high values...')
    for offset in range(0, team_size, 4):
        val = struct.unpack('<I', team_data[offset:offset+4])[0]
        if val > 0x10000000 and val < 0x40000000:
            print('  team+0x{:x}: {}'.format(offset, hex(val)))

CloseHandle(hproc)