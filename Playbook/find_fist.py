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

table_base = 0x2A82E17D0
stride = 5672

# Save current snapshot - save before clearing plays
before_data = mem_read(hproc, table_base, 5672)

# Wait - this would only save changes after we run compare, so don't do that
# The user said removing plays didn't change team data - maybe the game stores playbook externally
# But they can LOAD a playbook that changes game state

# The question is where the modification occurs - maybe in PlayStation or similar

# Let me try something else - modify team+0x464 with a MUCH different value and see what happens
# Since our small offset tests don't work, maybe we need a pointer-based addressing

# Current 76ers first play value is 712 
# Let's try something very large - maybe 3937238 (our known play offset)

phi_addr = 0x2A82E17D0
team_data = mem_read(hproc, phi_addr, 5672)
current_val = struct.unpack('<I', team_data[0x464:0x468])[0]

print('Current first play value: {} ({})'.format(current_val, hex(current_val)))

# Let's try writing a large value that might map to a real play string
# From file offset 0x3BBFB6 might map somewhere

# If file base 0x380000 maps to memory around 0x2EB00000, let's try offset 0x3BBFB6 + difference

# First, let's find where ANY of our known play strings exist in memory
# Search for any valid play name like FIST

print('\nSearching for valid play in memory...')
search_for = b'FIST\x00'

for start in range(0x2D000000, 0x31000000, 0x500000):
    data = mem_read(hproc, start, 0x500000)
    if data:
        pos = data.find(search_for)
        if pos >= 0:
            print('Found FIST at {} + {}'.format(hex(start), hex(pos)))
            addr_found = start + pos
            print('Address: {}'.format(hex(addr_found)))
            
            # Try reading offsets nearby
            near = mem_read(hproc, addr_found - 20, 50)
            if near:
                print('Nearby area:')
                for i in range(0, 50, 4):
                    val = struct.unpack('<I', near[i:i+4])[0]
                    if 0x3000000 < val < 0x4000000:
                        print('  +0x{:x}: {}'.format(i, hex(val)))
            break
        else:
            print('Nothing at {}'.format(hex(start)))

CloseHandle(hproc)