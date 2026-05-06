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

pid = 40028
module_base = 0x140000000

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t()
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

def read_uint64(hproc, addr):
    data = mem_read(hproc, addr, 8)
    if data:
        return struct.unpack('<Q', data)[0]
    return None

# Search for "Plays" or "playdata" string in memory to find where the catalog is loaded
search_terms = [
    b'Plays.playdata',
    b'playdata',
    b'PLAYS',
    b'MEM ISO',
    b'QUICK 1 CHEST',
    b'FIST 14',
]

# Search in a 500MB range starting from module base
print('Searching for play catalog data in memory...')
print('This may take a while...')

search_start = module_base + 0x10000000  # Start 256MB into the module
search_end = module_base + 0x100000000  # Search 4GB range

for search_bytes in search_terms:
    print('\nSearching for "{}"...'.format(search_bytes))
    
    found = 0
    pos = search_start
    while pos < search_end and found < 5:
        chunk_size = min(0x100000, search_end - pos)  # 1MB chunks
        data = mem_read(hproc, pos, chunk_size)
        if data is None:
            pos += chunk_size
            continue
        
        idx = data.find(search_bytes)
        while idx != -1 and found < 5:
            abs_pos = pos + idx
            ctx_start = max(0, idx - 10)
            ctx_end = min(chunk_size, idx + len(search_bytes) + 30)
            ctx = data[ctx_start:ctx_end]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print('  Found at 0x{:X}: ...{}...'.format(abs_pos, ascii_ctx))
            found += 1
            idx = data.find(search_bytes, idx + 1)
        pos += chunk_size
        
        # Progress indicator
        if (pos - search_start) % (50 * 1024 * 1024) == 0:
            print('  Scanned {}MB...'.format((pos - search_start) // (1024 * 1024)))
    
    if found == 0:
        print('  Not found')

CloseHandle(hproc)
print('\nDone.')
