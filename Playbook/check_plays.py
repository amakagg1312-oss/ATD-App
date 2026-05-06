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

array_addr = 0x2E5B874

data = mem_read(hproc, array_addr, 0x100)
if data:
    print('Play array at {}'.format(hex(array_addr)))
    print('\nFirst 20 play offsets:')
    for i in range(20):
        offset = struct.unpack('<I', data[i*4:i*4+4])[0]
        print('  [{}]: {} ({})'.format(i, offset, hex(offset)))
    
    # Now look up these offsets in the string block
    string_block = mem_read(hproc, 0x2FFCD8000, 0x40000)
    if string_block:
        print('\nPlay names at these offsets:')
        for i in range(5):
            offset = struct.unpack('<I', data[i*4:i*4+4])[0]
            if offset < len(string_block):
                # Try UTF-16LE null-terminated
                name_bytes = b''
                for j in range(offset, offset + 60, 2):
                    if j+1 < len(string_block):
                        w = struct.unpack('<H', string_block[j:j+2])[0]
                        if w == 0:
                            break
                        name_bytes += struct.pack('<H', w)
                try:
                    name = name_bytes.decode('utf-16le')
                    print('  [{}] offset {}: {}'.format(i, offset, name))
                except:
                    print('  [{}] offset {}: (decode error)'.format(i, offset))
    
    # Try writing test - change first offset
    print('\nTesting write...')
    test_offset = 550  # First play we verified: FIST 21 IVERSON
    
    if mem_write(hproc, array_addr, struct.pack('<I', test_offset)):
        verify = mem_read(hproc, array_addr, 4)
        if verify and struct.unpack('<I', verify)[0] == test_offset:
            print('WRITE SUCCESS! Check game - first play should now be FIST 21 IVERSON')
        else:
            print('Write failed')

CloseHandle(hproc)