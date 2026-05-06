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

# Take snapshot NOW with current playbook (1 play)
snapshot_file = r'D:\project\Playbook\pb_1play.bin'

# Save wide memory regions
print('Taking snapshot with 1 play...')
regions = [
    (0x2D000000, 0x100000),
    (0x2E000000, 0x100000),
    (0x2F000000, 0x100000),
]

all_data = b''
for start, size in regions:
    data = mem_read(hproc, start, size)
    if data:
        all_data += data

if all_data:
    with open(snapshot_file, 'wb') as f:
        f.write(all_data)
    print('Saved {} bytes'.format(len(all_data)))
    print('\nNOW LOAD THE PLAYBOOK in the game (add some plays), then run:')
    print('python compare_pb.py')

CloseHandle(hproc)