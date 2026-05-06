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

# Load before snapshot
with open(r'D:\project\Playbook\phi_team_loaded.bin', 'rb') as f:
    before = f.read()

# Get current team data
phi_addr = 0x2A82E17D0
after = mem_read(hproc, phi_addr, 5672)

if before and after:
    # Find differences
    diffs = []
    for i in range(len(before)):
        if before[i] != after[i]:
            diffs.append(i)
    
    print('Found {} differences in team'.format(len(diffs)))
    
    if diffs:
        # Group consecutive
        groups = []
        current = [diffs[0]]
        for i in range(1, len(diffs)):
            if diffs[i] == diffs[i-1] + 1:
                current.append(diffs[i])
            else:
                groups.append(current)
                current = [diffs[i]]
        groups.append(current)
        
        print('Consecutive groups: {}'.format(len(groups)))
        
        # Show first 20 groups
        for i, g in enumerate(groups[:20]):
            print('Group {}: team+0x{:x} ({} bytes)'.format(i, g[0], len(g)))
            
            # Show values
            if len(g) >= 4:
                for j in [0, 4, 8, 12]:
                    if j < len(g):
                        off = g[j]
                        before_val = struct.unpack('<I', before[off:off+4])[0]
                        after_val = struct.unpack('<I', after[off:off+4])[0]
                        print('    +0x{:x}: {} -> {}'.format(off, hex(before_val), hex(after_val)))

CloseHandle(hproc)