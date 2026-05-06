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
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# Search in wider range for playbook - look for arrays where many valid offsets exist
# Play offsets should be in range ~0x1000 to ~0x30000

print('Searching memory for valid playbook-like arrays...')

search_chunks = [
    (0x2D000000, 0x100000),
    (0x2E000000, 0x100000), 
    (0x2F000000, 0x100000),
    (0x30000000, 0x100000),
    (0x31000000, 0x100000),
]

total_found = 0
for start, size in search_chunks:
    data = mem_read(hproc, start, size)
    if data:
        for i in range(0, size - 64, 4):
            # Check if we have 16 consecutive entries in valid range
            valid_count = 0
            for j in range(16):
                if i+j*4+4 <= len(data):
                    val = struct.unpack('<I', data[i+j*4:i+j*4+4])[0]
                    if 0x1000 <= val <= 0x40000:
                        valid_count += 1
            
            if valid_count >= 10:
                addr = start + i
                print('Found at {} + {} = {}'.format(hex(start), hex(i), hex(addr)))
                total_found += 1
                if total_found >= 5:
                    break
    if total_found >= 5:
        break

print('Done. Found {}'.format(total_found))

CloseHandle(hproc)