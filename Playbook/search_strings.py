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

# Try searching for playbook string directly - find a play name we know should be in the currently loaded playbook
# Load the string block and find a play name, then search for it in memory

# First get the string block
string_block = mem_read(hproc, 0x2FFCD8000, 0x40000)
if not string_block:
    print('Failed to read string block')
    CloseHandle(hproc)
    exit()

# Search for a play name in current memory - find some non-empty location
# Try searching for UTF-16LE patterns that look like play names

# Let's try searching for team "PHI" - this should exist whether playbook loaded or not
print('Searching for PHI in string block area...')

# Try several regions in the 0x2FFCDxxx area
search_areas = [0x2FFD0000, 0x2FFE0000, 0x2FFF0000, 0x30000000]

for area in search_areas:
    data = mem_read(hproc, area, 0x10000)
    if data:
        pos = data.find(b'PHI\x00')
        if pos >= 0:
            print('Found PHI at {} + {}'.format(hex(area), pos))
            break
        else:
            print('No PHI at {}'.format(hex(area)))

# Also check around our original playbook area
print('\nChecking original playbook area 0x2ffca0000:')
data = mem_read(hproc, 0x2ffca0000, 0x100)
if data:
    non_zero = sum(1 for i in range(0, 100, 4) if struct.unpack('<I', data[i:i+4])[0] != 0)
    print('Non-zero entries: {}'.format(non_zero))

CloseHandle(hproc)