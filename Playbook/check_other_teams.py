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

# Let's look at other teams that might have bigger playbooks loaded - let's check Bucks or another team
# The global table base is 0x2A82E17D0, stride is 5672

table_base = 0x2A82E17D0
stride = 5672

# Bucks is at +stride
bucks_addr = table_base + stride
bucks_data = mem_read(hproc, bucks_addr, 1000)

if bucks_data:
    # Bucks playbook data
    print('Bucks playbook area:')
    for offset in range(0x440, 0x500, 4):
        val = struct.unpack('<I', bucks_data[offset:offset+4])[0]
        if val != 0:
            print('  +0x{:x}: {}'.format(offset, hex(val)))

# And Celtics (index 4)
celtics_addr = table_base + stride * 4
celtics_data = mem_read(hproc, celtics_addr, 1000)

if celtics_data:
    print('\nCeltics playbook area:')
    for offset in range(0x440, 0x500, 4):
        val = struct.unpack('<I', celtics_data[offset:offset+4])[0]
        if val != 0:
            print('  +0x{:x}: {}'.format(offset, hex(val)))

# The 76ers (index 0) playbook area 
phi_data = mem_read(hproc, table_base, 1000)
print('\n76ers playbook area:')
for offset in range(0x440, 0x500, 4):
    val = struct.unpack('<I', phi_data[offset:offset+4])[0]
    if val != 0:
        print('  +0x{:x}: {}'.format(offset, hex(val)))

CloseHandle(hproc)