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

playbook_addr = 0x2E05BB0

print('Checking playbook at {}'.format(hex(playbook_addr)))

# Read play data
data = mem_read(hproc, playbook_addr, 100)
if data:
    count = struct.unpack('<I', data[0:4])[0]
    print('Current play count:', count)
    print('First play offset:', struct.unpack('<I', data[4:8])[0])
    print('Second:', struct.unpack('<I', data[8:12])[0])

# Try writing - change to play offset 3937238 (0x3BBFB6 = SAS FIST 24 ANGLE from file)
# But we need to find the RIGHT offset that maps in memory

# First let's see where the play NAME is for offset 131489
# Maybe offset is relative to some string block

# Let's try different approaches:
# 1. Try 0 (empty)
# 2. Try 131489 + some offset

# Let's try writing test=0 at first play position
test_addr = playbook_addr + 4

print('\nWriting test value 0 to first play position...')
if mem_write(hproc, test_addr, struct.pack('<I', 0)):
    verify = mem_read(hproc, test_addr, 4)
    if verify and struct.unpack('<I', verify)[0] == 0:
        print('WRITE SUCCESS to {}! Check game.'.format(hex(test_addr)))

CloseHandle(hproc)