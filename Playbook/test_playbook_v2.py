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

playbook_addr = 0x2e031790

print('Playbook at {}'.format(hex(playbook_addr)))

data = mem_read(hproc, playbook_addr, 300)
if data:
    count = struct.unpack('<I', data[0:4])[0]
    print('Count: {}'.format(count))
    
    print('\nFirst 20 play offsets:')
    for i in range(min(20, count)):
        offset = struct.unpack('<I', data[4+i*4:4+i*4+4])[0]
        print('  [{}]: {}'.format(i, hex(offset)))
    
    # Try writing - change first play offset to a different valid one
    # Use offset like 0x370029 (one of the valid ones)
    test_offset = 0x370029
    
    print('\nWriting test offset {} to first play...'.format(hex(test_offset)))
    if mem_write(hproc, playbook_addr + 4, struct.pack('<I', test_offset)):
        verify = mem_read(hproc, playbook_addr + 4, 4)
        if verify and struct.unpack('<I', verify)[0] == test_offset:
            print('WRITE SUCCESS! Check if first play changed in game!')

CloseHandle(hproc)