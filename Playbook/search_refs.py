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

# Our known playbook: 0x2FFCA19D0
# Let's directly search in ALL of memory for reference to it using memory from large region and check what references we can find

target_bytes = b'\xd0\x19\xca\x2f'

# Search large memory
import itertools

search_regions = [(0x10000000, 0x20000000), (0x2D000000, 0x4000000)]

for start, end in search_regions:
    print('Searching {} to {}'.format(hex(start), hex(end)))
    
    count = 0
    for current in range(start, end, 0x500000):
        try:
            size = min(0x500000, end - current)
            data = mem_read(hproc, current, size)
            if data:
                pos = data.find(target_bytes)
                while pos >= 0:
                    found_addr = current + pos
                    print('Ref at {}'.format(hex(found_addr)))
                    
                    # Try writing here
                    test_offset = 550
                    if mem_write(hproc, found_addr, struct.pack('<I', test_offset)):
                        write_verify = mem_read(hproc, found_addr, 4)
                        if write_verify and struct.unpack('<I', write_verify)[0] == test_offset:
                            print('SUCCESS! Wrote to {}'.format(hex(found_addr)))
                            exit()
                    
                    count += 1
                    if count > 5:
                        break
                    
                    pos = data.find(target_bytes, pos + 1)
        except Exception as e:
            pass
        
        if count > 5:
            break

CloseHandle(hproc)