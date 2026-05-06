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
team_data = mem_read(hproc, team_addr, 5672)

# The values at 0x458 area look like ASCII "col/sgolog" - might be from loaded playbook name
# Let's search for play COUNT field somewhere
# Usually count would be small integer like 30-60

print('Looking for play count (small integers around 30-80)...')
for offset in range(0x200, 0x600, 4):
    val = struct.unpack('<I', team_data[offset:offset+4])[0]
    if 1 <= val <= 100:
        print('  team+0x{:x}: {}'.format(offset, val))

# Also check for play OFFSET in team (where the array starts)
# The playbook list should be near 60 * 4 = 240 bytes or larger
# Let's look at what's at team+0x200 area

print('\nFirst bytes 0x200-0x300:')
for offset in range(0x200, 0x300, 4):
    val = struct.unpack('<I', team_data[offset:offset+4])[0]
    if val != 0:
        print('  team+0x{:x}: {}'.format(offset, hex(val)))

CloseHandle(hproc)