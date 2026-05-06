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

snapshot_file = r'D:\project\Playbook\pb_1play.bin'
with open(snapshot_file, 'rb') as f:
    before = f.read()

regions = [(0x2D000000, 0x100000), (0x2E000000, 0x100000), (0x2F000000, 0x100000)]

after_data = b''
for start, size in regions:
    data = mem_read(hproc, start, size)
    if data:
        after_data += data

diffs = []
for i in range(min(len(before), len(after_data))):
    if before[i] != after_data[i]:
        diffs.append(i)

print('Found {} differences'.format(len(diffs)))

if diffs:
    groups = []
    current = [diffs[0]]
    for i in range(1, len(diffs)):
        if diffs[i] == diffs[i-1] + 1:
            current.append(diffs[i])
        else:
            groups.append(current)
            current = [diffs[i]]
    groups.append(current)
    
    print('Groups: {}'.format(len(groups)))
    
    for i, g in enumerate(groups[:20]):
        size = len(g)
        base = g[0]
        
        if base < 0x100000:
            addr = 0x2D000000 + base
        elif base < 0x200000:
            addr = 0x2E000000 + base - 0x100000
        else:
            addr = 0x2F000000 + base - 0x200000
        
        chunk = after_data[base:base+20]
        print('Group {}: {} bytes at {}'.format(i, size, hex(addr)))
        
        if size >= 4:
            count = struct.unpack('<I', chunk[0:4])[0]
            print('  Count: {}'.format(count))

CloseHandle(hproc)