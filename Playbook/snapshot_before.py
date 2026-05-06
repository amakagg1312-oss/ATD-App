import struct
import ctypes
from ctypes import wintypes
import sys
import io
import os

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

# Get current PID
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

snapshot_file = r'D:\project\Playbook\playbook_snapshot.bin'

print('Taking snapshot of playbook memory region...')

snapshot_data = mem_read(hproc, 0x2FFCA0000, 0x20000)

if snapshot_data:
    with open(snapshot_file, 'wb') as f:
        f.write(snapshot_data)
    print('Snapshot saved! Size: {} bytes'.format(len(snapshot_data)))
    print('\nNow LOAD YOUR PLAYBOOK in the game, then run:')
    print('python compare_after.py')
else:
    print('Failed to read memory')

CloseHandle(hproc)