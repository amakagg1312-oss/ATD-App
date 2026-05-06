"""Find staff base - Nick Nurse focused search"""

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import struct

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.OpenProcess.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_int]
kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, c_size_t, ctypes.POINTER(c_size_t)]
kernel.VirtualQueryEx.restype = ctypes.c_size_t
kernel.VirtualQueryEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]

class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64),
        ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", ctypes.c_uint32),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
    ]

def encode_wstring(s):
    return s.encode('utf-16-le')

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

hits = []
mbr = MBI()
addr = 0

while True:
    result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
    if result == 0:
        break
    
    if mbr.State == 0x1000 and mbr.RegionSize > 0:
        buf = create_string_buffer(mbr.RegionSize)
        if kernel.ReadProcessMemory(h, ctypes.c_void_p(mbr.BaseAddress), buf, mbr.RegionSize, byref(c_size_t(0))):
            raw = buf.raw
            idx = raw.find(last_bytes)
            while idx >= 0:
                candidate = mbr.BaseAddress + idx - staff_last_offset
                first_addr = candidate + staff_first_offset
                block = create_string_buffer(len(first_bytes))
                if kernel.ReadProcessMemory(h, ctypes.c_void_p(first_addr), block, len(first_bytes), byref(c_size_t(0))):
                    if block.raw == first_bytes:
                        hits.append(candidate)
                        print(f"Found Nick Nurse at staff base 0x{candidate:X}")
                        print(f"  Last name at: 0x{mbr.BaseAddress + idx:X}")
                idx = raw.find(last_bytes, idx + 2)
    
    addr = mbr.BaseAddress + mbr.RegionSize

print(f"Total: {len(hits)}")