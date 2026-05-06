"""Find all table pointers using known table bases."""

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil

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
    
    # Known table bases
    staff_table = 0x2A84DD940
    
    # Search in the pointer region 0x7E00000-0x7E30000
    print(f"Scanning pointer region for staff table pointer...")
    
    ptr_region_start = 0x7E00000
    ptr_region_end = 0x7E30000
    region_size = ptr_region_end - ptr_region_start
    
    # Read entire region in chunks
    chunk_size = 0x10000
    target_bytes = staff_table.to_bytes(8, 'little')
    
    for offset in range(0, region_size, chunk_size):
        size = min(chunk_size, region_size - offset)
        buf = read_memory(h, ptr_region_start + offset, size)
        if buf:
            idx = buf.find(target_bytes)
            while idx >= 0:
                ptr_addr = ptr_region_start + offset + idx
                print(f"  FOUND: 0x{ptr_addr:X} -> 0x{staff_table:X}")
                idx = buf.find(target_bytes, idx + 1)
    
    print("\nDone!")

if __name__ == "__main__":
    main()
