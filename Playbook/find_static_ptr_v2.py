"""Find static pointer chain for staff table."""

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import struct

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.OpenProcess.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_int]
kernel.ReadProcessMemory.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, 
    c_size_t, ctypes.POINTER(c_size_t)
]

def read_memory(h, addr, size):
    buf = create_string_buffer(size)
    if kernel.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p.pid
    return None

def main():
    pid = find_process()
    if not pid:
        print("NBA2K26.exe not running!")
        return
    
    print(f"PID: {pid}")
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    # Pointers to staff table
    candidates = [
        0x295144838,
        0x2A7AB01D8,
        0x2A82B2828,
        0x2A90DC0F8,
    ]
    
    staff_table = 0x2A84DD940
    
    # Search for pointers to these candidates in module region
    for candidate in candidates:
        print(f"\nSearching for pointer to 0x{candidate:X} in 0x7E00000-0x8000000...")
        target_bytes = candidate.to_bytes(8, 'little')
        
        found = False
        for addr in range(0x7E00000, 0x8000000, 0x10000):
            buf = read_memory(h, addr, 0x10000)
            if buf:
                idx = buf.find(target_bytes)
                while idx >= 0:
                    ptr_addr = addr + idx
                    print(f"  FOUND: 0x{ptr_addr:X} -> 0x{candidate:X} -> 0x{staff_table:X}")
                    found = True
                    idx = buf.find(target_bytes, idx + 1)
        
        if not found:
            print(f"  Not found")
    
    # Also check if any of these candidates are near each other (might be in same structure)
    print(f"\nPointer relationships:")
    for i, c1 in enumerate(candidates):
        for c2 in candidates[i+1:]:
            diff = abs(c1 - c2)
            print(f"  0x{c1:X} <-> 0x{c2:X}: diff = 0x{diff:X} ({diff})")

if __name__ == "__main__":
    main()
