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
WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL

import subprocess
result = subprocess.run(['powershell', '-Command', '(Get-Process NBA2K26).Id'], capture_output=True, text=True)
pid = int(result.stdout.strip())
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    if ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count)):
        return bytes(buf)
    return None

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    if WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count)):
        return write_count.value == len(data)
    return False

# Maybe the system works differently - look at a global playbook table
# The game must have a table connecting team to a playbook assignment structure

# Let's search memory near 0x2ea90000 for pattern 0x3BBFB6 (3937238)
# This value might be stored as a pointer or offset

target = 3937238  # 0x3BBFB6 from file

print('Searching for {} ({}) in memory...'.format(target, hex(target)))

# Search large region
for start in range(0x2D000000, 0x32000000, 0x100000):
    data = mem_read(hproc, start, 0x100000)
    if data:
        for i in range(0, 0x100000-4, 4):
            val = struct.unpack('<I', data[i:i+4])[0]
            if val == target:
                print('Found at {} + {}'.format(hex(start), hex(i)))
                print('Address: {}'.format(hex(start + i)))
                
                # Check around this for other play entries
                near = mem_read(hproc, start + i - 30, 80)
                if near:
                    for j in range(0, 80, 4):
                        v = struct.unpack('<I', near[j:j+4])[0]
                        if 0x3000000 < v < 0x4000000:
                            print('  +0x{:x}: {}'.format(j, hex(v)))
                break

# Let's try a different approach - look at the team's current "play index" value
# Check what value at team+0x464 corresponds to

phi_addr = 0x2A82E17D0
team_data = mem_read(hproc, phi_addr, 5672)

current_first = struct.unpack('<I', team_data[0x464:0x468])[0]
print('\n76ers first play value: {} ({})'.format(current_first, hex(current_first)))

# Maybe it's an INDEX into the catalog array at 0x2ea90000?
# If each entry is 4 bytes, then index 0 = entry at 0x2ea90000, index 1 = 0x2ea90004, etc

# Let's see if value matches an index
# The catalog at 0x2ea90000 - what's the 0-index entry?

catalog = 0x2ea90000
cat_data = mem_read(hproc, catalog, 20)
if cat_data:
    entry_0 = struct.unpack('<I', cat_data[0:4])[0]
    print('\nCatalog[0] = {} ({})'.format(entry_0, hex(entry_0)))
    print('Current play value {} / 4 = index {}'.format(current_first, current_first // 4))

# Try changing value to 0 and see what happens in catalog[0]
# But we need to find what value would show something different in-game

# Actually, let's try: value is an INDEX into the catalog
# So if current_first = 712, let's see catalog[712/4] or similar

idx = current_first // 4
cat_entry = mem_read(hproc, catalog + idx * 4, 4)
if cat_entry:
    print('Catalog[{}] = {} ({})'.format(idx, struct.unpack('<I', cat_entry)[0], hex(struct.unpack('<I', cat_entry)[0])))

CloseHandle(hproc)