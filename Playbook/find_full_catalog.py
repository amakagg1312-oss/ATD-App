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

# Find the play catalog - look for count around 1700
# The catalog should have: [count:4][play1_string_ptr:4][play2_string_ptr:4]...

print('Searching for play catalog (~1700 entries)...')

search_ranges = [(0x2D000000, 0x200000), (0x2F000000, 0x200000), (0x30000000, 0x1000000)]

for start, size in search_ranges:
    print(f'Region {hex(start)}...')
    
    for chunk_start in range(start, start + size, 0x50000):
        data = mem_read(hproc, chunk_start, 0x50000)
        if not data:
            continue
            
        for offset in range(0, 0x50000 - 16, 8):
            try:
                count = struct.unpack('<I', data[offset:offset+4])[0]
            except:
                continue
                
            if 1500 <= count <= 2000:
                # Check if subsequent values look like string offsets (0x3Bxxxx - 0x40xxxx)
                valid = 0
                for i in range(5):
                    val = struct.unpack('<I', data[offset+4+i*4:offset+8+i*4])[0]
                    if 0x3B0000 <= val <= 0x410000:
                        valid += 1
                
                if valid >= 5:
                    print(f'FOUND at {hex(chunk_start + offset)}: count={count}')
                    # That's likely our catalog!
                    print(f'First few string offsets:')
                    for i in range(10):
                        val = struct.unpack('<I', data[offset+4+i*4:offset+8+i*4])[0]
                        print(f'  {hex(val)}')
                    break
        else:
            continue
        break

CloseHandle(hproc)