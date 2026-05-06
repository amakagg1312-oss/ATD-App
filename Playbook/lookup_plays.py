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
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# This address seems to have the playbook. Let me read the structure differently
array_addr = 0x2E05B864  # Start from index 2 where we saw 4096

data = mem_read(hproc, array_addr, 0x100)
if data:
    print('Reading as playbook array from {}'.format(hex(array_addr)))
    
    # It seems like the playbook has a header, then play list starts at some offset
    # The entries at [6], [7], [8] = 4096 might be the first few plays
    
    # Try offsetting into this structure
    plays_start = 0x2E05B870  # Try index 6 * 4 = 24 bytes in
    
    print('\nTrying plays at {}:'.format(hex(plays_start)))
    
    for i in range(10):
        offset = i * 4
        val = struct.unpack('<I', data[offset:offset+4])[0]
        if 0x1000 <= val <= 0x30000:
            print('  [{}] offset {} -> {}'.format(i, hex(val), hex(array_addr + offset)))
            
            # Look up name
            string_block = mem_read(hproc, 0x2FFCD8000, 0x40000)
            if string_block and val < len(string_block):
                name_bytes = b''
                for j in range(val, val + 60, 2):
                    if j+1 < len(string_block):
                        w = struct.unpack('<H', string_block[j:j+2])[0]
                        if w == 0:
                            break
                        name_bytes += struct.pack('<H', w)
                try:
                    name = name_bytes.decode('utf-16le')
                    print('       name: {}'.format(name))
                except:
                    pass

CloseHandle(hproc)