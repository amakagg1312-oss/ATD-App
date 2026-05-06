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
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    if ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count)):
        return bytes(buf)
    return None

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    if WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count)):
        return write_count.value == len(data)
    return False

team_addr = 0x2A82E17D0

# Restore original count (73)
orig_count = 73
if mem_write(hproc, team_addr + 0x33c, struct.pack('<I', orig_count)):
    print('Restored original count to {}'.format(orig_count))

# Now let's try a different approach: look at the string "col" or area around team+0x458
# "col" suggests maybe the playbook name or something like that
# Let's extract actual strings from team area

team_data = mem_read(hproc, team_addr, 5672)

print('\nSearching for ASCII strings in team (might be playbook name)...')
for offset in range(0, 1000):
    if team_data[offset] >= 0x30 and team_data[offset] < 0x7F:
        # Potential ASCII start
        s = b''
        for i in range(offset, min(offset+30, 5672)):
            if team_data[i] >= 0x20 and team_data[i] < 0x7F:
                s += bytes([team_data[i]])
            else:
                break
        if len(s) >= 5:
            try:
                print('  team+0x{:x}: {}'.format(offset, s.decode('ascii')))
            except:
                pass

CloseHandle(hproc)