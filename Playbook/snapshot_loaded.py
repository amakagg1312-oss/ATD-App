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

# Let's take a wide snapshot NOW while your playbook IS loaded
snapshot_file = r'D:\project\Playbook\playbook_loaded_snapshot.bin'

# Save several regions
print('Taking snapshots of memory while playbook is loaded...')

regions = [
    (0x2D000000, 0x100000),
    (0x2E000000, 0x100000),
    (0x2F000000, 0x100000),
    (0x30000000, 0x100000),
]

all_data = b''
for start, size in regions:
    data = mem_read(hproc, start, size)
    if data:
        all_data += data
        print('Read {} bytes from {}'.format(len(data), hex(start)))
    else:
        print('Failed at {}'.format(hex(start)))

if all_data:
    with open(snapshot_file, 'wb') as f:
        f.write(all_data)
    print('\nSaved {} bytes to {}'.format(len(all_data), snapshot_file))
    print('\nNow go to game, CLEAR or change playbook to different one, then run compare script.')

CloseHandle(hproc)