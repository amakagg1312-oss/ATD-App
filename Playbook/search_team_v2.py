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

# Let's see what's at team+0x464 - that's 0x2e303030 which is ASCII '000'
# Look at what's AROUND this offset - maybe there's a pointer chain

print('Examining context around team+0x464:')
for offset in range(0x440, 0x500, 4):
    val = struct.unpack('<I', team_data[offset:offset+4])[0]
    print('  team+0x{:x}: {}'.format(offset, hex(val)))

# Try looking near that area for actual playbook arrays
# If team+0x464 is "000", maybe team+0x460 or nearby holds actual pointer

print('\nLooking at wider area...')
for offset in range(0x300, 0x600, 4):
    val = struct.unpack('<I', team_data[offset:offset+4])[0]
    if val > 0x10000000:
        print('  team+0x{:x}: {}'.format(offset, hex(val)))

# Try writing at different offsets - let's try finding play count or actual array pointer
# Look at earlier offsets (players have known offsets)

print('\nLooking at attribute offsets that work (from 2k26_offsets.json)...')
# Player attributes typically start around offset 0
# But for team, look at first 0x300 bytes
for offset in range(0, 0x300, 4):
    val = struct.unpack('<I', team_data[offset:offset+4])[0]
    if 0x20000000 <= val <= 0x34000000:
        print('  team+0x{:x}: {}'.format(offset, hex(val)))

CloseHandle(hproc)