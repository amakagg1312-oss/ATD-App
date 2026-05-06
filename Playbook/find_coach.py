"""Quick find staff base - Nick Nurse"""

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import struct

kernel = WinDLL('kernel32')
OpenProcess = kernel.OpenProcess
OpenProcess.restype = ctypes.c_void_p
OpenProcess.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_int]
CloseHandle = kernel.CloseHandle
ReadProcessMemory = kernel.ReadProcessMemory
ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p.pid
    return None

def read_mem(handle, addr, size):
    buf = create_string_buffer(size)
    if ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

# Config - adjust these for 2K26
staff_stride = 432
staff_first_offset = 0x28

pid = find_process()
if not pid:
    print("Game not running")
    exit(1)

handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
print(f"PID: {pid}")

# Search for Nick Nurse at staff slot 0 (HEAD COACH usually slot 0)
# Nick Nurse = first name at offset 0x28, last name at offset 0x28+20 = 0x3C
search = b'N\x00i\x00c\x00k\x00 \x00N\x00u\x00r\x00s\x00e\x00'

# Search memory
found = []
for base in range(0x27000000, 0x28000000, 0x100000):
    raw = read_mem(handle, base, 0x100000)
    if not raw:
        continue
    idx = raw.find(search)
    if idx >= 0:
        found.append(base + idx)
        print(f"Found Nick Nurse at 0x{base+idx:X}")

for addr in found:
    # Try calculate staff base
    staff_base = addr - staff_first_offset - 20  # Back up to start of staff entry
    if staff_base > 0:
        print(f"Staff base likely: 0x{staff_base:X}")

print(f"Done. Found {len(found)} matches")
CloseHandle(handle)