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

pid = 58172
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# Let's read what we wrote and see the addresses
# First read our modified regions to verify

# Let's read around 0x3030xxxx addresses we found
modified_addrs = [
    0x30305ad4,
    0x303130d4,
    0x303131d0,
]

print('=== Reading modified addresses ===')
for addr in modified_addrs:
    data = mem_read(hproc, addr - 0x30, 0x40)
    if data:
        print('\nData around {}:'.format(hex(addr - 0x30)))
        # Show first few 4-byte values as ints
        for i in range(0, 16, 4):
            val = struct.unpack('<I', data[i:i+4])[0]
            print('  +0x{:x}: {}'.format(i, val))

# What IS this region?
print('\n=== What region is 0x303xxxxx? ===')
# Check what kind of data is at these addresses
test = mem_read(hproc, 0x30300000, 100)
if test:
    # Show as hex
    print('First 100 bytes at 0x30300000:')
    for i in range(0, 100, 16):
        hex_dump = ' '.join('{:02x}'.format(b) for b in test[i:i+16])
        print('  {} +{}: {}'.format(hex(test[i]), i, hex_dump))

CloseHandle(hproc)