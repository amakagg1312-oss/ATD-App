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

# Bucks team
bucks_addr = 0x2A82E2DF8
bucks_data = mem_read(hproc, bucks_addr, 5672)

play_ref = struct.unpack('<I', bucks_data[0x464:0x468])[0]
print('Bucks playbook ref at team+0x464:', hex(play_ref))

# This appears to be a string pointer - read what's at that address as ASCII
ref_data = mem_read(hproc, play_ref, 50)
if ref_data:
    print('String at that address:', ref_data[:30])

# Now 76ers team - what's at team+0x464?
phi_addr = 0x2A82E17D0
phi_data = mem_read(hproc, phi_addr, 5672)

phi_ref = struct.unpack('<I', phi_data[0x464:0x468])[0]
print('\n76ers at team+0x464:', hex(phi_ref))

if phi_ref > 0x10000000:
    ref_data2 = mem_read(hproc, phi_ref, 50)
    if ref_data2:
        print('String at that address:', ref_data2[:30])

# Let's also look at what's at team+0x33c for both (the count)
print('\n76ers count at +0x33c:', struct.unpack('<I', phi_data[0x33c:0x340])[0])
print('Bucks count at +0x33c:', struct.unpack('<I', bucks_data[0x33c:0x340])[0])

# Now check team+0x348 for both (other count)
print('\n76ers count at +0x348:', struct.unpack('<I', phi_data[0x348:0x34c])[0])
print('Bucks count at +0x348:', struct.unpack('<I', bucks_data[0x348:0x34c])[0])

CloseHandle(hproc)