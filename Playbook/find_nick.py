"""Find Nick Nurse staff entry - focused search"""

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import struct

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.OpenProcess.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_int]
kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

def encode_wstring(s):
    return s.encode('utf-16-le')

def read_mem(handle, addr, size):
    buf = create_string_buffer(size)
    if kernel.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
print(f"PID: {pid}")

# Nick Nurse - search for last name "Nurse" then verify first name "Nick"
last_bytes = encode_wstring("Nurse")
first_bytes = encode_wstring("Nick")

# Config from offsets file
staff_stride = 432
staff_first_offset = 0x28  # 40
staff_last_offset = 0x0    # 0
staff_name_length = 20

# Search wider range
for base in range(0x26000000, 0x2A000000, 0x100000):
    raw = read_mem(h, base, 0x100000)
    if not raw:
        continue
    
    idx = raw.find(last_bytes)
    while idx >= 0:
        # Found "Nurse" - calculate potential staff base
        addr = base + idx
        staff_base = addr - staff_last_offset
        
        # Verify "Nick" at first_name offset
        first_addr = staff_base + staff_first_offset
        first_data = read_mem(h, first_addr, len(first_bytes))
        
        if first_data and first_data.startswith(first_bytes):
            print(f"FOUND Nick Nurse!")
            print(f"  Last name at: 0x{addr:X}")
            print(f"  First name at: 0x{first_addr:X}")
            print(f"  Staff base: 0x{staff_base:X}")
            print(f"  Staff stride: {staff_stride}")
            
            # Read more staff data around this base
            staff_data = read_mem(h, staff_base, 200)
            if staff_data:
                print(f"  Staff entry: {staff_data[:100]}")
        
        idx = raw.find(last_bytes, idx + 2)

print("Done")