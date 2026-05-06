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

# The group offsets from comparison were in the snapshots
# Let's read them from memory directly

# Check around our difference addresses
check_addrs = [
    0x2d010078,
    0x2d010194,
]

for addr in check_addrs:
    data = mem_read(hproc, addr, 10)
    if data:
        print('{}: {}'.format(hex(addr), data.hex()))
    else:
        print('Failed at {}'.format(hex(addr)))

# Let's take a fresh snapshot and search for playbook structure
# The playbook probably isn't stored where we were looking

# Search for a better candidate - look for count=64 somewhere
print('\nSearching for count=64...')

regions = [(0x2D000000, 0x200000), (0x2E000000, 0x200000)]

for start, size in regions:
    for base in range(start, start + size, 1000):
        data = mem_read(hproc, base, 100)
        if data:
            count = struct.unpack('<I', data[0:4])[0]
            if count == 64:
                print('Found count=64 at {}'.format(hex(base)))
                # Check if next bytes are play pointers
                first = struct.unpack('<I', data[4:8])[0]
                if first > 0x10000 and first < 0x400000:
                    print('  First play offset: {}'.format(hex(first)))
                    break

CloseHandle(hproc)