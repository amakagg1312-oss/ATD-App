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
print('NBA2K26 PID: {}'.format(pid))

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# Search large memory for playbook strings
# Let's search regions for play name patterns

search_regions = [
    (0x2E000000, 0x200000),   # We got data from here
    (0x31000000, 0x2000000),  # Try higher addresses
]

# Try searching in parts
print('Searching for play data in memory...')

for start, size in search_regions:
    print('Searching {} to {}...'.format(hex(start), hex(start + size)))
    
    # Read in chunks
    chunk_size = 0x100000
    for offset in range(0, size, chunk_size):
        data = mem_read(hproc, start + offset, chunk_size)
        if data:
            # Look for sequence of pointer-sized values - look for multiple offsets in valid range
            # Play offsets should be around 0x1000 to 0x30000 range typically
            pass_count = 0
            for i in range(0, chunk_size - 16, 4):
                vals = []
                for j in range(4):
                    val = struct.unpack('<I', data[i+j*4:i+j*4+4])[0]
                    if 0x1000 <= val <= 0x40000:
                        vals.append(val)
                    else:
                        break
                
                if len(vals) >= 4:  # At least 4 consecutive valid offsets
                    print('Found potential array at {} + {}'.format(hex(start + offset), hex(i)))
                    print('  First few: {}'.format(vals[:4]))
                    pass_count += 1
                    if pass_count >= 3:
                        break
        if pass_count >= 3:
            break

CloseHandle(hproc)