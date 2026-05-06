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

pid = 58172
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

# Search for our known playbook addresses in the game memory range
# Use byte search pattern

target_bytes = b'\xd0\x19\xca\x2f'  # Little-endian of 0x2FFCA19D0

search_start = 0x2D000000
search_size = 0x2000000

print('=== Searching memory for references to playbook ===')

data = mem_read(hproc, search_start, search_size)
if data:
    pos = data.find(target_bytes)
    if pos >= 0:
        found_addr = search_start + pos
        print('Found reference at {}'.format(hex(found_addr)))
        
        # This should be THE pointer - but maybe structure offset
        # Write our test offset here
        test_offset = 550
        
        if mem_write(hproc, found_addr, struct.pack('<I', test_offset)):
            print('Wrote {} to address'.format(test_offset))
            
            # Verify
            verify = mem_read(hproc, found_addr, 4)
            if verify and struct.unpack('<I', verify)[0] == test_offset:
                print('SUCCESS - Verify it changed in-game!')
        else:
            print('Failed to write here')
    else:
        print('Not found - try another pattern')
        
        # Try alternate - 0x2FFCA1910 pattern
        alt_bytes = b'\x10\x19\xca\x2f'
        pos2 = data.find(alt_bytes)
        if pos2 >= 0:
            print('Found alternate at {}'.format(hex(search_start + pos2)))

CloseHandle(hproc)