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
WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL
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

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    ok = WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count))
    return ok and write_count.value == len(data)

# Current playbook is loaded somewhere - let's search for non-zero offsets in the 0x2FFCAxxx region now
# After loading new playbook, let's find where the valid plays are

print('Searching for valid playbook arrays...')

for base_addr in range(0x2FFCA0000, 0x2FFCC0000, 0x10000):
    data = mem_read(hproc, base_addr, 0x100)
    if data:
        # Check for non-zero pointers
        non_zero = 0
        for i in range(0, 0x100, 4):
            val = struct.unpack('<I', data[i:i+4])[0]
            if val != 0:
                non_zero += 1
        
        if non_zero > 3:
            print('Found active region at {}'.format(hex(base_addr)))
            # Show first few entries
            for i in range(0, 10):
                val = struct.unpack('<I', data[i*4:i*4+4])[0]
                if val != 0:
                    print('  [{}] offset: {} ({})'.format(i, val, hex(val)))

CloseHandle(hproc)