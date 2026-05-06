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

# Extract all play names from the runtime area
print('=== Extracting play names from runtime area ===')
data = mem_read(hproc, 0x2FFCD8000, 0x10000)
if data:
    # Parse UTF-16LE strings separated by double null
    text = data.decode('utf-16-le', errors='replace')
    # Split by double null (which appears as \x00\x00 in UTF-16LE)
    # Actually in the decoded text, null bytes are \x00
    parts = text.split('\x00\x00')
    plays = [p.strip() for p in parts if p.strip() and len(p.strip()) > 2]
    print('Found {} play names:'.format(len(plays)))
    for i, play in enumerate(plays[:50]):
        print('  {}: {}'.format(i, play))

# Also look at the structure around 0x298C505E0
print('\n=== Examining 0x298C505E0 area ===')
data = mem_read(hproc, 0x298C50500, 0x200)
if data:
    for i in range(0, len(data), 4):
        val = struct.unpack_from('<I', data, i)[0]
        if 0 < val < 12506:
            print('  Offset 0x{:X}: {} (0x{:X})'.format(i, val, val))

# Look for pointers from team struct to the runtime play data
team_rva = 0x7E1E318
ptr_addr = module_base + team_rva
table_base = read_uint64(hproc, ptr_addr)

print('\n=== Looking for pointers to runtime play data ===')
# Search for pointers to 0x2FFCD8xxx range
for i in range(0, 0x200, 8):
    ptr = read_uint64(hproc, table_base + i)
    if ptr and ptr > 0x2FFC00000 and ptr < 0x300000000:
        print('  Offset 0x{:X}: pointer to 0x{:X}'.format(i, ptr))

# Also search in the 0x2A12xxxxx area (play catalog) for pointers
print('\n=== Searching for playbook structure in catalog area ===')
# The catalog at 0x2A12xxxxx has play names. Let's look for associated data
# Search for "MEM ISO 3 GO" and see what's nearby
search = b'M\x00E\x00M\x00 \x00I\x00S\x00O\x00 \x003\x00 \x00G\x00O\x00'
data = mem_read(hproc, 0x2A1439C00, 0x200)
if data:
    idx = data.find(search)
    if idx >= 0:
        print('Found MEM ISO 3 GO at offset 0x{:X}'.format(idx))
        # Show surrounding data
        for i in range(max(0, idx-32), min(len(data), idx+64), 4):
            val = struct.unpack_from('<I', data, i)[0]
            print('  Offset 0x{:X}: 0x{:08X} ({})'.format(i, val, val))

CloseHandle(hproc)
print('\nDone.')
