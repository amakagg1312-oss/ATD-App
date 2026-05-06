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

pid = 58172
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    ok = WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count))
    return ok and write_count.value == len(data)

# The issue might be that each team has its OWN playbook and the game loads 
# playbook from a DIFFERENT location based on active team in editor

# Let's try scanning more carefully for where the team's playbook pointer IS
# First, get from 2k26_offsets what the team structure looks like

# Actually - the simplest test: modify ALL potential 76ers playbook locations with unique values
# Then see which changes in-game

# Known potential bases, we'll write unique offsets to test which changes
test_bases = [
    0x2FFCA1910,
    0x2FFCA19D0,
    0x2FFCA1850,
    0x2FFCA1A00,
    0x2FFCA1800,
    0x2FFCB0000,
]

# Use distinct signature offsets: 550 = FIST 21 IVERSON at some bases, 712 = FIST CHEST, etc.
# Write to indices 50-54

from ctypes import c_ubyte

test_offset = 0x5555  # Unique test value

print('Writing test offset {} to multiple addresses...'.format(hex(test_offset)))

wrote_addrs = []
for base in test_bases:
    try:
        # Write to index 50
        target = base + (50 * 0x30)
        data = struct.pack('<I', test_offset)
        if mem_write(hproc, target, data):
            print('Wrote to {}'.format(hex(target)))
            wrote_addrs.append(target)
    except Exception as e:
        pass

# Now verify which one "sticks"
print('\nVerifying which address took the change:')

for base in test_bases:
    target = base + (50 * 0x30)
    data = mem_read(hproc, target, 4)
    if data:
        val = struct.unpack('<I', data)[0]
        if val == test_offset:
            print('{} = {} - MATCH!'.format(hex(target), hex(val)))

# If nothing matches, need different approach
# Let's look at what plays exist at these potential playbook arrays
# to figure out which IS the active playbook

print('\n=== Looking at potential playbook arrays ===')
for base in test_bases:
    # Read first 10 plays - check which contain our known plays
    first_10 = []
    for i in range(10):
        data = mem_read(hproc, base + i * 0x30, 4)
        if data:
            val = struct.unpack('<I', data)[0]
            first_10.append(val)
    
    print('\nBase {}:'.format(hex(base)))
    print('  First 10 offsets: {}'.format(first_10[:5]))

# The actual playbook should match some of our known offsets
# Known real offsets: 550, 712, 896, 1216, 1352 (the real plays)
known_real = [550, 712, 896, 1216, 1352]

for base in test_bases:
    data = mem_read(hproc, base, 4)
    if data:
        val = struct.unpack('<I', data)[0]
        if val in known_real:
            print('\nFOUND real playbook at {}! First play offset = {}'.format(hex(base), val))

CloseHandle(hproc)