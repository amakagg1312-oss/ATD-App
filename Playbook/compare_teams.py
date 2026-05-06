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

team_addr = 0x2A82E17D0
stride = 5672

# First team (76ers)
first_team = mem_read(hproc, team_addr, stride)
# Second team (Bucks)
second_team = mem_read(hproc, team_addr + stride, stride)

if first_team and second_team:
    print('First team count at +0x33c:', struct.unpack('<I', first_team[0x33c:0x340])[0])
    print('Second team count at +0x33c:', struct.unpack('<I', second_team[0x33c:0x340])[0])
    
    # Check for any pointers/values to 0x2e or 0x2f regions in each team
    print('\nSearching for 0x2Exxxxxx pointers in first team...')
    for offset in range(0, stride, 4):
        val = struct.unpack('<I', first_team[offset:offset+4])[0]
        if 0x2E000000 <= val <= 0x2F000000:
            print('  team+0x{:x}: {}'.format(offset, hex(val)))

    print('\nSearching for 0x2Exxxxxx pointers in second team...')
    for offset in range(0, stride, 4):
        val = struct.unpack('<I', second_team[offset:offset+4])[0]
        if 0x2E000000 <= val <= 0x2F000000:
            print('  team+0x{:x}: {}'.format(offset, hex(val)))

CloseHandle(hproc)