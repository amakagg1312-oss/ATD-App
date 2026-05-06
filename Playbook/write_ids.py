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

team_base = 0x2A82E17D0

print('Writing test catalog IDs...')

# Try write small catalog ID = 50
test_id = 50

if mem_write(hproc, team_base + 0x464, struct.pack('<I', test_id)):
    verify = mem_read(hproc, team_base + 0x464, 4)
    if verify and struct.unpack('<I', verify)[0] == test_id:
        print('Written {} to team+0x464'.format(test_id))

# Write a few more test entries for different plays
test_entries = [
    (0x34c, 25, 1, 1),   # entry at 0x34c: id=25, type=1, shot=1
    (0x358, 30, 1, 2),   # entry at 0x358: id=30, type=1, shot=2  
    (0x364, 35, 2, 1),   # entry at 0x364: id=35, type=2, shot=1
]

for offset, pid, ptype, shot in test_entries:
    if mem_write(hproc, team_base + offset, struct.pack('<III', pid, ptype, shot)):
        print('Wrote [{}/{} at +0x{:x}]'.format(pid, ptype, shot, offset))

print('\nCheck game - has anything changed?')

CloseHandle(hproc)