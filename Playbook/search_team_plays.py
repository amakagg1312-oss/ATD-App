import struct
import ctypes
from ctypes import wintypes
import subprocess

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE
CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL
ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
ReadProcessMemory.restype = wintypes.BOOL

result = subprocess.run(['powershell', '-Command', '(Get-Process NBA2K26).Id'], capture_output=True, text=True)
pid = int(result.stdout.strip())
hproc = OpenProcess(0x1F0FFF, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    if ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count)):
        return bytes(buf)
    return None

# Search team region for count(30-80) + entries pattern
print('Searching team region...')

team_base = 0x2A82E0000

for offset in range(0, 0x50000, 8):
    data = mem_read(hproc, team_base + offset, 100)
    if not data:
        continue
    
    count = struct.unpack('<I', data[0:4])[0]
    if 30 <= count <= 80:
        # Check next entries
        valid = 0
        for i in range(5):
            val = struct.unpack('<I', data[4+i*4:8+i*4])[0]
            if 0 <= val <= 1700:
                valid += 1
        
        if valid >= 5:
            print('Found at', hex(team_base+offset), '- count:', count)
            print('Entries:', struct.unpack('<I', data[4:8])[0], struct.unpack('<I', data[8:12])[0], struct.unpack('<I', data[12:16])[0])
            break

CloseHandle(hproc)