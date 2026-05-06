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

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    ok = WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count))
    return ok and write_count.value == len(data)

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

# Find "PHI" in memory to find 76ers team
phi_pattern = b'PHI\x00'
search_start = 0x2D000000
search_size = 0x1000000

print('Searching for PHI team...')
data = mem_read(hproc, search_start, search_size)
if data:
    pos = data.find(phi_pattern)
    if pos >= 0:
        team_base = search_start + pos - 0x30
        print('Found PHI at offset {}, team base likely {}'.format(hex(pos), hex(team_base)))
        
        # Read team data
        team_data = mem_read(hproc, team_base, 5672)
        if team_data:
            print('\nSearching for pointers to playbook region...')
            
            for offset in range(0, 5672, 4):
                val = struct.unpack('<I', team_data[offset:offset+4])[0]
                if 0x2FFCA000 <= val <= 0x2FFD0000:
                    print('  team+0x{:x}: {}'.format(offset, hex(val)))
                    
                    # Try writing here
                    test_val = 550
                    if mem_write(hproc, team_base + offset, struct.pack('<I', test_val)):
                        verify = mem_read(hproc, team_base + offset, 4)
                        if verify and struct.unpack('<I', verify)[0] == test_val:
                            print('WRITE SUCCESS at team+0x{:x}! Check game!'.format(offset))

CloseHandle(hproc)