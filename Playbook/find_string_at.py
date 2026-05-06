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

# Check at offset 0x226 (550)
string_block = mem_read(hproc, 0x2FFCD8000, 0x40000)

print('String block starts at 0x2FFCD8000')
print('Looking at offset 550 (0x226):')

if string_block and 550 < len(string_block):
    name_bytes = b''
    for j in range(550, min(550+60, len(string_block)), 2):
        if j+1 < len(string_block):
            w = struct.unpack('<H', string_block[j:j+2])[0]
            if w == 0:
                break
            name_bytes += struct.pack('<H', w)
    try:
        name = name_bytes.decode('utf-16le')
        print('Name at 550: "{}"'.format(name))
    except Exception as e:
        print('Error:', e)
        print('Raw bytes:', string_block[550:560])

# Also check around 0x1000-0x2000 area where our earlier plays were
print('\nLooking at wider range for play strings...')
# Find multiple strings in typical offset range
found = 0
for offset in range(0, 3000, 2):
    if offset + 1 < len(string_block):
        w = struct.unpack('<H', string_block[offset:offset+2])[0]
        if w != 0 and w < 0x8000:  # Valid ASCII range
            # Read a full string
            name_bytes = b''
            for j in range(offset, min(offset+60, len(string_block)), 2):
                if j+1 < len(string_block):
                    w2 = struct.unpack('<H', string_block[j:j+2])[0]
                    if w2 == 0:
                        break
                    name_bytes += struct.pack('<H', w2)
            if len(name_bytes) >= 4:
                try:
                    name = name_bytes.decode('utf-16le')
                    if name and name.isupper() and len(name) >= 5:
                        print('Offset {}: {}'.format(offset, name))
                        found += 1
                        if found > 15:
                            break
                except:
                    pass

CloseHandle(hproc)