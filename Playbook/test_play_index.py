import struct
import ctypes
from ctypes import wintypes
import subprocess

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
ReadProcessMemory.restype = wintypes.BOOL
WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL

result = subprocess.run(['powershell', '-Command', '(Get-Process NBA2K26).Id'], capture_output=True, text=True)
pid = int(result.stdout.strip())
hproc = kernel32.OpenProcess(0x1F0FFF, False, pid)

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

# Team address
team_addr = 0x2A82E17D0
team_data = mem_read(hproc, team_addr, 6000)

# Look at structure around 0x33c
print('=== Team offsets 0x330 to 0x400 ===')
for i in range(0x330, 0x400, 4):
    val = struct.unpack('<I', team_data[i:i+4])[0]
    if val != 0:
        print(f'+0x{i:03x}: {val} ({hex(val)})')

# Now check what's at team+0x340 (right after first count at 0x33c)
print('\n=== Entries at +0x340 (after 73 count at 0x33c) ===')
for i in range(0x340, 0x340+40, 4):
    val = struct.unpack('<I', team_data[i:i+4])[0]
    print(f'+0x{i:03x}: {val}')

# Write test - change a play entry to see if game shows change
# Let's try changing entry at +0x340 to index 50 (small value)
print('\nTesting write at +0x340...')

test_val = 50
if mem_write(hproc, team_addr + 0x340, struct.pack('<I', test_val)):
    verify = mem_read(hproc, team_addr + 0x340, 4)
    if verify and struct.unpack('<I', verify)[0] == test_val:
        print(f'Wrote {test_val} - check game!')

import ctypes
ctypes.WinDLL('kernel32').CloseHandle(hproc)