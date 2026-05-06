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
print('NBA2K26 PID: {}'.format(pid))

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# Search in team structure area where playbook might load
# Our team base is around 0x2D000000 - let me search that entire team area

search_regions = [
    (0x2D000000, 0x200000),      # Team region
    (0x2E000000, 0x200000),      # Next region
    (0x2F000000, 0x1000000),    # Large playbook area
]

before_file = r'D:\project\Playbook\playbook_snapshot.bin'
with open(before_file, 'rb') as f:
    before_data = f.read()

# Check what's currently loaded in the old playbook addresses - maybe it's being read, not stored

print('Reading playbook array bases to see current state...')

playbook_bases = [0x2FFCA1910, 0x2FFCA19D0, 0x2FFCA1A00, 0x2FFCA1A90, 0x2FFCA1B20]

for base in playbook_bases:
    data = mem_read(hproc, base, 0x30)
    if data:
        print('\nBase: {}'.format(hex(base)))
        for i in range(0, 6):
            offset = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            print('  [{}] offset: {} ({})'.format(i, offset, hex(offset)))

CloseHandle(hproc)