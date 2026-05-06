import struct
import ctypes
from ctypes import wintypes

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
module_base = 0x140000000

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

def read_uint64(hproc, addr):
    data = mem_read(hproc, addr, 8)
    if data:
        return struct.unpack('<Q', data)[0]
    return None

def read_uint32(hproc, addr):
    data = mem_read(hproc, addr, 4)
    if data:
        return struct.unpack('<I', data)[0]
    return None

def dump_hex(hproc, addr, size=256):
    data = mem_read(hproc, addr, size)
    if not data:
        print('  Failed to read at 0x{:X}'.format(addr))
        return
    for i in range(0, len(data), 16):
        hex_str = ' '.join('{:02X}'.format(b) for b in data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print('  0x{:08X}: {:48s} {}'.format(addr + i, hex_str, ascii_str))

# Examine the 76ers area
print('=== Examining 76ers area at 0x298C65038 ===')
dump_hex(hproc, 0x298C64F00, 0x300)

# Look for playbook data near the 76ers string
print('\n=== Searching for playbook data near 76ers ===')
# Scan backwards and forwards for arrays of play IDs
for base in [0x298C64F00, 0x298C65000, 0x298C65100]:
    data = mem_read(hproc, base, 0x200)
    if data:
        print('\n--- At 0x{:X} ---'.format(base))
        for i in range(0, len(data), 4):
            val = struct.unpack_from('<I', data, i)[0]
            if 0 < val < 12506:
                print('  Offset 0x{:X}: {} (0x{:X})'.format(i, val, val))

# Also examine the runtime play name area (0x2FFCD809C)
print('\n=== Examining runtime play name area at 0x2FFCD809C ===')
dump_hex(hproc, 0x2FFCD8000, 0x200)

# Search for a structure that contains multiple play IDs
print('\n=== Searching for playbook arrays in 0x298C00000-0x299000000 ===')
# Look for contiguous arrays of values in play ID range
pos = 0x298C00000
end = 0x299000000
while pos < end:
    chunk_size = min(0x10000, end - pos)
    data = mem_read(hproc, pos, chunk_size)
    if data:
        # Look for sequences of 10+ values in play ID range
        for i in range(0, len(data) - 80, 4):
            values = []
            for j in range(0, 80, 4):
                val = struct.unpack_from('<I', data, i + j)[0]
                values.append(val)
            in_range = sum(1 for v in values if 0 < v < 12506)
            if in_range > 15:
                print('  At 0x{:X}: {} of {} values in play ID range'.format(pos + i, in_range, len(values)))
                print('    Values: {}'.format([v for v in values if 0 < v < 12506][:25]))
                break  # Only show first match per chunk
    pos += chunk_size

CloseHandle(hproc)
print('\nDone.')
