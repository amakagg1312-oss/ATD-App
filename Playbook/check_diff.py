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

# Check what these addresses contain
diff_addrs = [
    0x2d010078,
    0x2d010194,
    0x2d0101a0,
    0x2d0101e8,
    0x2d010304,
    0x2d010310,
    0x2d010470,
    0x2d0104a8,
]

print('Current values at difference addresses:')
for addr in diff_addrs:
    data = mem_read(hproc, addr, 8)
    if data:
        val = struct.unpack('<I', data[0:4])[0]
        val2 = struct.unpack('<I', data[4:8])[0]
        print('  {}: {} {}'.format(hex(addr), hex(val), hex(val2)))

# These look like they could be pointers or IDs
# Let's try writing to one to see if it affects the playbook

print('\nTrying test write to first address {}...'.format(hex(diff_addrs[0])))
test_data = b'\x00\x00\x00\x00\x01\x00\x00\x00'

if mem_write(hproc, diff_addrs[0], test_data):
    verify = mem_read(hproc, diff_addrs[0], 8)
    if verify:
        print('Write successful')

CloseHandle(hproc)