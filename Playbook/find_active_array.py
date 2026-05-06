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

# The plays from screenshot BLOB 01 were: FIST 21 IVERSON, FIST CHEST FLARE, etc.
# Let me search in memory that GAME is ACTUALLY reading from for display

# Search in a MUCH larger region for any pointer to these specific offsets
target_offsets = [550, 712, 896, 1216, 1352, 1133, 2252]

# Search in all game memory - try different base regions
search_regions = [
    (0x10000000, 0x10000000),  # Lower memory
    (0x2D000000, 0x10000000),  # Team area
    (0x2FFE00000, 0x2000000),  # Near play area
]

print('=== Searching all game memory for active playbook pointers ===')

# These offsets in little-endian form
search_bytes = [struct.pack('<I', off) for off in target_offsets]

for base, size in search_regions:
    print('\nSearching region {} - {}'.format(hex(base), hex(base + size)))
    
    try:
        data = mem_read(hproc, base, size)
        if not data:
            continue
            
        # Count references
        for sb in search_bytes:
            count = data.count(sb)
            if count > 0:
                print('  Offset {} has {} references'.format(struct.unpack('<I', sb)[0], count))
    except Exception as e:
        print('  Error: {}'.format(e))

# Let's try a simpler approach - search backwards from where we KNOW these offset VALUES appear
# to find the actual array used in-game

# Find address 550 in memory, then see if it's part of an array
print('\n=== Looking for array containing offset 550 ===')

search_bytes = struct.pack('<I', 550)

for base, size in search_regions:
    try:
        data = mem_read(hproc, base, size)
        if data:
            pos = data.find(search_bytes)
            while pos >= 0:
                # Found reference to 550
                addr = base + pos
                
                # Check if it's in an array - look at nearby for more offsets
                nearby = data[pos:pos+200]
                offsets_found = []
                for i in range(0, 200, 4):
                    if i + 4 <= len(nearby):
                        try:
                            val = struct.unpack('<I', nearby[i:i+4])[0]
                            if val < 0x10000:
                                offsets_found.append(val)
                        except:
                            pass
                
                # If we find multiple valid offsets in sequence, this is likely an array
                if len(offsets_found) > 5:
                    print('Found array candidate at {}'.format(hex(addr - 0x30)))
                    print('  First 10: {}'.format(offsets_found[:10]))
                    break
                    
                pos = data.find(search_bytes, pos + 1)
    except:
        pass

CloseHandle(hproc)