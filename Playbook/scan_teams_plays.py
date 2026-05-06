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

team_table = 0x2A82E17D0
stride = 5672

print('Scanning teams for playbook...')

for team_idx in range(30):
    team_addr = team_table + team_idx * stride
    team_data = mem_read(hproc, team_addr, 1000)
    if not team_data:
        continue
    
    for off in [0x300, 0x33c, 0x340, 0x348, 0x350]:
        try:
            count = struct.unpack('<I', team_data[off:off+4])[0]
            if 60 <= count <= 70:
                first_ref = struct.unpack('<I', team_data[off+4:off+8])[0]
                if first_ref > 0x1000000:
                    print('Team {} at {}: count={} at +0x{:x}'.format(team_idx, hex(team_addr), count, off))
                    print('  First ref: {}'.format(hex(first_ref)))
        except:
            pass

CloseHandle(hproc)