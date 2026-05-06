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

# Extract all play names from runtime area
print('=== Extracting all play names from runtime area ===')
data = mem_read(hproc, 0x2FFCD8000, 0x10000)
if data:
    # Parse UTF-16LE strings separated by double null
    # In UTF-16LE, a null terminator is 00 00 (two bytes)
    # So we look for \x00\x00\x00\x00 (double null in UTF-16LE = two null chars)
    text = data.decode('utf-16-le', errors='replace')
    # Split by double null (which appears as \x00\x00 in the decoded text)
    parts = text.split('\x00\x00')
    plays = [p for p in parts if p.strip() and len(p.strip()) > 2]
    print('Found {} plays:'.format(len(plays)))
    for i, play in enumerate(plays):
        print('  [{}] {}'.format(i, play))

# Now find the structure that maps plays to slots
# Look for an array of indices or offsets pointing to these plays
print('\n=== Searching for play index/offset array ===')
# The plays are at 0x2FFCD8000. Look for pointers or offsets to this area
# Search in nearby memory for an array of uint32 offsets

# First, let's find the offset of "MEM ISO 3 GO" within the play data
text = data.decode('utf-16-le', errors='replace')
mem_iso_pos = text.find('MEM ISO 3 GO')
quick_chest_pos = text.find('QUICK 1 CHEST')
fist14_pos = text.find("'90 FIST 14 QUICK 2")

print('MEM ISO 3 GO at text offset: {}'.format(mem_iso_pos))
print('QUICK 1 CHEST at text offset: {}'.format(quick_chest_pos))
print("'90 FIST 14 QUICK 2 at text offset: {}".format(fist14_pos))

# Now search for these offsets as uint32 values in nearby memory
if mem_iso_pos >= 0:
    target = mem_iso_pos * 2  # UTF-16LE uses 2 bytes per char
    print('\nSearching for offset {} (0x{:X}) in memory...'.format(target, target))
    # Search in 0x2FFC00000 to 0x300000000 range
    pos = 0x2FFC00000
    end = 0x300000000
    found = 0
    while pos < end and found < 20:
        chunk_size = min(0x10000, end - pos)
        chunk = mem_read(hproc, pos, chunk_size)
        if chunk:
            target_bytes = struct.pack('<I', target)
            idx = chunk.find(target_bytes)
            while idx != -1 and found < 20:
                abs_pos = pos + idx
                print('  Found at 0x{:X}'.format(abs_pos))
                found += 1
                idx = chunk.find(target_bytes, idx + 1)
        pos += chunk_size

CloseHandle(hproc)
print('\nDone.')
