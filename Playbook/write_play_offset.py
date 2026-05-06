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

# 76ers team
phi_addr = 0x2A82E17D0

# The playbook data might be at a different location entirely
# Maybe the game stores playbook in a separate global table

# Let's search for any location that has "1 play" - look in memory for count of 1
# Search in the 0x2E0xxxxx region which had playbook data

print('Searching memory for value 1 (play count)...')

# Search wider memory regions
search_regions = [
    (0x2D000000, 0x500000),
    (0x2E000000, 0x500000),
    (0x2F000000, 0x500000),
]

for start, size in search_regions:
    data = mem_read(hproc, start, size)
    if data:
        # Look for count = 1 near other playbook data
        # But let's just see if there's a structure we can modify

# Actually let's try a simpler approach: search for ALL values within team that change when you modify playbook!
# We already found some offsets that look like play count
# Let's try team+0x460 directly as we found first play offset

team_data = mem_read(hproc, phi_addr, 5672)

# Get current values at known offsets
print('Current 76ers team playbook data:')
print('  +0x33c (count?):', struct.unpack('<I', team_data[0x33c:0x340])[0])
print('  +0x348 (count?):', struct.unpack('<I', team_data[0x348:0x34c])[0])
print('  +0x464 (first offset):', struct.unpack('<I', team_data[0x464:0x468])[0])
print('  +0x468:', struct.unpack('<I', team_data[0x468:0x46c])[0])

# Try writing directly to change the first play offset and see if anything changes in game

# Maybe we interpret the value differently - could be an INDEX not offset
# Let's try: value / stride = index into play array

# Another possibility: The playbook might work like player attributes where it's a pointer + offset
# Let's look at what team+0x460 has
val_460 = struct.unpack('<I', team_data[0x460:0x464])[0]
print('\n  +0x460:', hex(val_460))

# If 0x6f676f6c = " clog" - might be a string pointer or from filename

# Let's try the SIMPLE test - write a different first play value
test_val = 896  # MIL FIST 34 DOWN SLIP

print('\nWriting test value {} to team+0x464...'.format(test_val))
if mem_write(hproc, phi_addr + 0x464, struct.pack('<I', test_val)):
    verify = mem_read(hproc, phi_addr + 0x464, 4)
    if verify and struct.unpack('<I', verify)[0] == test_val:
        print('Write successful - check game if first play changed!')

CloseHandle(hproc)