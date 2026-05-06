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

# The gameplay might work via a "pointer to array of indices"
# Maybe team+0x464 contains a POINTER (address) not an offset

phi_addr = 0x2A82E17D0
team_data = mem_read(hproc, phi_addr, 5672)

# Let's look at 0x464 again - it looks like it's 0x2c8 = 712
# What if we interpret it as an address?

current_val = struct.unpack('<I', team_data[0x464:0x468])[0]
print('Current value at team+0x464:', current_val, '({})'.format(hex(current_val)))

# Try interpreting 0x464 as a pointer to the playbook array
# If 712 is actually an address 0x2c8, that would be too low for playbook
# But maybe it's an offset from some base?

# Let's find where plays ARE in memory
# Try searching: find ANY valid sequence of 60+ play indices in a row in memory

print('\nLooking for play list arrays...')

# Play arrays have format: [count][offset1][offset2][offset3]...
# Let's look for patterns

search_data = mem_read(hproc, 0x2E040000, 0x50000)
if search_data:
    # Look for count at start, and then many valid play offsets 
    for base in range(0, 0x50000 - 0x100, 16):
        count_bytes = struct.unpack('<I', search_data[base:base+4])[0]
        if 1 <= count_bytes <= 65:  # play count between 1 and 65
            # Check if next 'count' entries are valid play offsets in range
            valid = 0
            for i in range(count_bytes):
                offset = base + 4 + i*4
                if offset + 4 > len(search_data):
                    break
                play_val = struct.unpack('<I', search_data[offset:offset+4])[0]
                if 0x10000 <= play_val <= 0x400000:  # valid play offsets
                    valid += 1
            
            if valid >= count_bytes * 0.8:  # 80% valid
                print('Found potential playbook at 0x2E040000 + {}'.format(hex(base)))
                print('  Count:', count_bytes)
                print('  First few offsets:', [struct.unpack('<I', search_data[base+4+i*4:base+4+i*4+4])[0] for i in range(min(5, count_bytes))])
                found_addr = 0x2E040000 + base
                break

CloseHandle(hproc)