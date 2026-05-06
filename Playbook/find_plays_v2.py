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

# Search for count = 64 (or nearby like 60-70) in larger area
print('Searching for play count 60-70...')

found = 0
for base in range(0x2D000000, 0x32000000, 0x10000):
    data = mem_read(hproc, base, 0x10000)
    if data:
        for i in range(0, 0x10000, 4):
            try:
                count = struct.unpack('<I', data[i:i+4])[0]
            except:
                continue
            if 60 <= count <= 70:
                # Check if next entries look like play offsets
                valid = 0
                for j in range(10):
                    try:
                        offset = struct.unpack('<I', data[i+4+j*4:i+4+j*4+4])[0]
                        if 0x10000 <= offset <= 0x400000:
                            valid += 1
                    except:
                        pass
                if valid >= 5:
                    print('Playbook at {} + {} = {}'.format(hex(base), hex(i), hex(base+i)))
                    print('  Count: {}'.format(count))
                    print('  First play offsets:')
                    for j in range(min(5, count)):
                        offset = struct.unpack('<I', data[i+4+j*4:i+4+j*4+4])[0]
                        print('    [{}]: {}'.format(j, hex(offset)))
                    found += 1
                    if found >= 3:
                        break
    if found >= 3:
        break

CloseHandle(hproc)