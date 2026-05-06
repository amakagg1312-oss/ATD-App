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

# Let me try to locate where strings are stored by using file-based mapping
# The game file might load playlists at known offsets relative to some base

# Try: maybe the game loads 2k's playbook data at base around 0x2F000000
# Offset 0x3BBFB6 from file could map with offset 0x3BBFB6 - 0x380000 = 0x3BFB6
# That would be something like 0x2F00000 + 0x3BFB6 = 0x2F+3BFB6 = 0x32FBFB6... but we can only address lower

# Instead, let's search more systematically - search for ANY valid offset format from file offsets
# We know from file: plays at 0x3BBFB6, 0x3DCC58, 0x3D214E

# Try smaller: maybe it's 0x3B FB6 mapping to a 32-bit value in memory
# Let's try searching for near ANY valid play string at multiple possible base

# Actually, let's check if ANY values in 76ers team at offset 0x464 work:
# What if we look at a global pointer stored in team?

# The team playbook pointer might be pointer at some OTHER offset
# Let's search where 0x2e05bb0 (playbook) is referenced

search_for = 0x2e05bb0
print('Searching for reference to {} in memory...'.format(hex(search_for)))

# Search in team address range
for start in [0x2A800000, 0x2A82E000]:
    data = mem_read(hproc, start, 0x50000)
    if data:
        for i in range(0, 0x50000, 4):
            val = struct.unpack('<I', data[i:i+4])[0]
            if val == search_for:
                print('Found at {} + {} (team+0x{:x})'.format(hex(start), hex(i), i))
                
                # Also search for ANY reference in memory to 0x2e05bb0
for region_start in [0x2D000000, 0x2E000000, 0x300000000]:
    data = mem_read(hproc, region_start, 0x10000)
    if data:
        for i in range(0, 0x10000, 4):
            val = struct.unpack('<I', data[i:i+4])[0]
            if val == search_for:
                print('Found at {} + {} (global reference)'.format(hex(region_start), hex(i)))

CloseHandle(hproc)