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
print('Process handle: {}'.format(hproc))

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

# Test reading module base
print('\nTest: reading module base (0x140000000)...')
test_data = mem_read(hproc, module_base, 16)
if test_data:
    print('  OK: {}'.format(test_data[:8].hex()))
else:
    print('  FAILED')
    exit(1)

# Read team table pointer
team_rva = 0x7E1E318
ptr_addr = module_base + team_rva
print('\nReading team table pointer at 0x{:X}...'.format(ptr_addr))
table_base = read_uint64(hproc, ptr_addr)
print('  Value: {}'.format('0x{:X}'.format(table_base) if table_base else 'None'))

if table_base:
    print('\nReading team struct at 0x{:X} (5672 bytes)...'.format(table_base))
    team_data = mem_read(hproc, table_base, 5672)
    if team_data:
        print('  OK: {} bytes read'.format(len(team_data)))
        # Print hex dump of first 512 bytes
        print('\n=== Team struct (first 512 bytes) ===')
        for i in range(0, min(512, len(team_data)), 16):
            hex_str = ' '.join('{:02X}'.format(b) for b in team_data[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in team_data[i:i+16])
            print('  0x{:04X}: {:48s} {}'.format(i, hex_str, ascii_str))
        
        # Look for potential play ID arrays
        print('\n=== Looking for potential play ID arrays ===')
        for offset in range(0, len(team_data) - 80, 4):
            values = []
            for i in range(0, 80, 4):
                if offset + i + 4 > len(team_data):
                    break
                val = struct.unpack_from('<I', team_data, offset + i)[0]
                values.append(val)
            
            # Check if values are in a reasonable range for play IDs (0-12506)
            in_range = sum(1 for v in values if 0 < v < 12506)
            if in_range > 10:
                print('  Offset 0x{:X}: {} of {} values in play ID range'.format(offset, in_range, len(values)))
                print('    Values: {}'.format(values[:15]))
    else:
        print('  FAILED')

CloseHandle(hproc)
print('\nDone.')
