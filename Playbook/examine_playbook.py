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

# Focus on 0x29A188830 which has QUICK 1 CHEST
print('=== Examining 0x29A188830 area (QUICK 1 CHEST) ===')
dump_hex(hproc, 0x29A188700, 0x300)

# Look at the values as uint32
print('\n=== Values as uint32 ===')
data = mem_read(hproc, 0x29A188800, 0x200)
if data:
    for i in range(0, len(data), 4):
        val = struct.unpack_from('<I', data, i)[0]
        if 0 < val < 12506:
            print('  Offset 0x{:X}: {} (0x{:X})'.format(i, val, val))

# Follow the pointer at 0x29A188820 (0x02A288BC)
print('\n=== Following pointer at 0x29A188820 ===')
ptr = read_uint64(hproc, 0x29A188820)
if ptr:
    print('  Pointer: 0x{:X}'.format(ptr))
    dump_hex(hproc, ptr, 0x100)

# Also examine the team struct pointers more closely
team_rva = 0x7E1E318
ptr_addr = module_base + team_rva
table_base = read_uint64(hproc, ptr_addr)

print('\n=== Examining team struct pointers ===')
for i in range(0, 0x160, 8):
    ptr = read_uint64(hproc, table_base + i)
    if ptr and ptr > 0x200000000 and ptr < 0x300000000:
        # Read 128 bytes from the pointer
        data = mem_read(hproc, ptr, 128)
        if data:
            # Count values in play ID range
            play_count = 0
            for j in range(0, 128, 4):
                val = struct.unpack_from('<I', data, j)[0]
                if 0 < val < 12506:
                    play_count += 1
            if play_count > 5:
                print('  Offset 0x{:X}: pointer to 0x{:X} ({} play IDs)'.format(i, ptr, play_count))
                vals = [struct.unpack_from('<I', data, j)[0] for j in range(0, 64, 4)]
                play_vals = [v for v in vals if 0 < v < 12506]
                print('    Play IDs: {}'.format(play_vals[:20]))

CloseHandle(hproc)
print('\nDone.')
