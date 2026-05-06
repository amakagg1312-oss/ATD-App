import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Sorry, we've tried many things without success. 
# This is actually more complex because the game may:
# 1. Cache playbook data from a file on startup
# 2. Use a different memory format 
# 3. Load playbook data fresh each time you open the menu

# The key thing is: We can read plays from memory, and our offsets DO map to actual play names.
# The problem is writing to make changes appear in-game

# Let me ask: when you saw no change - was ANY section different? Even one play?
# Or completely unchanged?

# For now - let's find out if the game even has the right values we're writing in memory

# Try reading from the START, using index 0 of ALL the addresses we can find

print('=== Checking current play at index 0 of all found arrays ===')

# These were from our earlier search - let's verify what's at index 0 for each
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
WriteProcessMemory = ctypes.WinDLL('kernel32', use_last_error=True).WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL

pid = 58172
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, 58172)

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

# Let's try writing EXACTLY unique values at index 0 of each potential playbook address and see WHICH changes. This is our best bet to find the right array. Use VERY unique values

test_value = 0xCAFE  # Very different from any real offset (should not map to any play)

# Find playbook addresses - use known ones plus around 0x2FFCAxxx range from earlier
test_addresses = [
    0x2FFCA1910,
    0x2FFCA19D0,
    0x2FFCA1A00,
    0x2FFCA1A30,
    0x2FFCA1850,
    0x2FFCA1800,
    0x2FFCB0000,
]

print('Writing test value {} at index 0 of each address...'.format(hex(test_value)))

for addr in test_addresses:
    if mem_write(hproc, addr, struct.pack('<I', test_value)):
        print('Wrote to {}'.format(hex(addr)))
    else:
        print('Failed: {}'.format(hex(addr)))

# Now read each back to verify
print('\nVerification - values at index 0:')
for addr in test_addresses:
    data = mem_read(hproc, addr, 4)
    if data:
        val = struct.unpack('<I', data)[0]
        marker = '*** GOT OUR VALUE ***' if val == test_value else ''
        print('{} = {} {}'.format(hex(addr), hex(val), marker))

CloseHandle(hproc)

print('\n\nIf any address shows our test value after verification: that is the active playbook.')
print('Tell me what you see!')

CloseHandle