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

# Get team table base
team_rva = 0x7E1E318
ptr_addr = module_base + team_rva
table_base = read_uint64(hproc, ptr_addr)
print('Team table base: 0x{:X}'.format(table_base))

# Play offsets from Plays.playdata file
play_offsets = {
    'MEM ISO 3 GO': 0x3B61AC,
    "'90 FIST 14 QUICK 2": 0x3BEF04,
    'QUICK 1 CHEST': 0x3D9D20,
}

print('\n=== Searching for play offsets in memory ===')

# Search in a 50MB range around the team struct
search_start = 0x200000000
search_end = 0x300000000

for play_name, play_offset in play_offsets.items():
    print('\nSearching for "{}" (offset 0x{:X})...'.format(play_name, play_offset))
    
    found = 0
    pos = search_start
    while pos < search_end and found < 10:
        chunk_size = min(0x100000, search_end - pos)
        data = mem_read(hproc, pos, chunk_size)
        if data is None:
            pos += chunk_size
            continue
        
        target_bytes = struct.pack('<I', play_offset)
        idx = data.find(target_bytes)
        while idx != -1 and found < 10:
            abs_pos = pos + idx
            # Show context
            ctx_start = max(0, idx - 8)
            ctx_end = min(chunk_size, idx + 12)
            ctx = data[ctx_start:ctx_end]
            print('  Found at 0x{:X}: {}'.format(abs_pos, ctx.hex()))
            found += 1
            idx = data.find(target_bytes, idx + 1)
        pos += chunk_size
        
        if (pos - search_start) % (50 * 1024 * 1024) == 0:
            print('  Scanned {}MB...'.format((pos - search_start) // (1024 * 1024)))
    
    if found == 0:
        print('  Not found')

CloseHandle(hproc)
print('\nDone.')
