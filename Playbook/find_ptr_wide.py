"""Find new pointer region after update."""

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
    
    # Staff table base
    staff_table = 0x2A84DD940
    staff_ptr_dynamic = 0x2A7AB01D8
    
    # Search for pointer to staff_table in all memory
    print(f"Searching for pointer to staff table 0x{staff_table:X}...")
    target_bytes = staff_table.to_bytes(8, 'little')
    
    # Search in chunks
    regions_to_search = [
        (0x7E00000, 0x8000000),   # Module data
        (0x10000000, 0x20000000), # Game data
        (0x200000000, 0x300000000), # High memory
    ]
    
    for start, end in regions_to_search:
        print(f"\n  Searching 0x{start:X}-0x{end:X}...")
        for addr in range(start, end, 0x10000):
            size = min(0x10000, end - addr)
            buf = read_memory(h, addr, size)
            if buf:
                idx = buf.find(target_bytes)
                while idx >= 0:
                    ptr_addr = addr + idx
                    # Skip if it's in the staff table itself
                    if ptr_addr < staff_table or ptr_addr > staff_table + 50000:
                        print(f"    FOUND: 0x{ptr_addr:X} -> 0x{staff_table:X}")
                    idx = buf.find(target_bytes, idx + 1)
    
    print("\nDone!")

if __name__ == "__main__":
    main()
