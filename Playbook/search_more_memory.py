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

# The screenshot plays DON'T exist in the known string block
# Let's search more memory for these missing plays

# Try searching in larger memory block
print('=== Searching for missing plays in FULL memory ===')

# Target plays from screenshot we can't find:
missing = ["FIST 15 MIDDLE", "52 FLAT"]

# Search in wider region
search_regions = [
    (0x2FF800000, 0x100000),   # Around play strings
    (0x2FFD0000, 0x100000),    # More string area
    (0x2FA00000, 0x200000),   # Different region
    (0x2E000000, 0x1000000),   # Generic game data
]

# Let's find the EXACT plays we need by searching by WORDS
target_searches = [
    b'MIDDLE',
    b'FLAT',
]

for base, size in search_regions:
    print('\nSearching region {} size {}'.format(hex(base), size))
    data = mem_read(hproc, base, size)
    if not data:
        continue
    
    for search in target_searches:
        pos = data.find(search)
        if pos >= 0:
            print('  Found "{}" at offset {} from {}'.format(search, pos, hex(base)))
            # Show context
            start = max(0, pos - 30)
            end = min(len(data), pos + 50)
            context = data[start:end]
            try:
                decoded = context.decode('utf-16-le', errors='replace')
                print('    Context: {}'.format(repr(decoded[:60])))
            except:
                try:
                    decoded = context.decode('utf-8', errors='replace')
                    print('    Context (ASCII): {}'.format(repr(decoded[:60])))
                except:
                    pass

# Alternatively - read the FIRST bytes of the playdata.iff file to see format
print('\n=== Checking playdata file ===')
playdata_path = r'D:\project\Playbook\game files\playdata_extracted\Plays.playdata'
try:
    with open(playdata_path, 'rb') as f:
        pd = f.read(2000)
    
    print('First 200 bytes of playdata file:')
    print(pd[:200])
    
    # Look for play names
    for search in [b'MIDDLE', b'FLAT', b'FIST']:
        pos = pd.find(search)
        if pos >= 0:
            print('\nFound {} at position {} in file'.format(search, pos))
            print('  Context: {}'.format(pd[pos-10:pos+40]))
except Exception as e:
    print('Error: {}'.format(e))

CloseHandle(hproc)