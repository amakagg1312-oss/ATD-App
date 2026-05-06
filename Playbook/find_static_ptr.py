"""Find the static base pointer chain for staff table."""

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
kernel.VirtualQueryEx.restype = ctypes.c_size_t
kernel.VirtualQueryEx.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t
]

class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_uint32),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
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

def search_for_pointer(h, target, region_start, region_end):
    """Search for a pointer to target in a memory region."""
    target_bytes = target.to_bytes(8, 'little')
    found = []
    
    for addr in range(region_start, region_end, 0x10000):
        size = min(0x10000, region_end - addr)
        buf = read_memory(h, addr, size)
        if buf:
            idx = buf.find(target_bytes)
            while idx >= 0:
                found.append(addr + idx)
                idx = buf.find(target_bytes, idx + 1)
    
    return found

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
    
    # Dynamic pointer found
    dynamic_ptr = 0x2A7AB01D8
    staff_table = 0x2A84DD940
    
    print(f"Dynamic pointer: 0x{dynamic_ptr:X} -> 0x{staff_table:X}")
    
    # Search for pointer to dynamic_ptr in module region
    print(f"\nSearching for pointer to 0x{dynamic_ptr:X} in module region...")
    
    # Module region is typically 0x7E00000-0x8000000 for NBA2K
    found = search_for_pointer(h, dynamic_ptr, 0x7E00000, 0x8000000)
    
    if found:
        print(f"Found {len(found)} pointers:")
        for addr in found:
            print(f"  Static pointer: 0x{addr:X} -> 0x{dynamic_ptr:X} -> 0x{staff_table:X}")
    else:
        print("Not found in 0x7E00000-0x8000000")
        
        # Search wider
        print(f"\nSearching wider region 0x7000000-0x9000000...")
        found = search_for_pointer(h, dynamic_ptr, 0x7000000, 0x9000000)
        
        if found:
            print(f"Found {len(found)} pointers:")
            for addr in found:
                print(f"  Static pointer: 0x{addr:X} -> 0x{dynamic_ptr:X} -> 0x{staff_table:X}")
        else:
            print("Not found")
            
            # Also try searching for direct pointer to staff_table in wider region
            print(f"\nSearching for direct pointer to staff table in 0x7000000-0x9000000...")
            found = search_for_pointer(h, staff_table, 0x7000000, 0x9000000)
            
            if found:
                print(f"Found {len(found)} direct pointers:")
                for addr in found:
                    print(f"  0x{addr:X} -> 0x{staff_table:X}")
            else:
                print("No direct pointers found either")

if __name__ == "__main__":
    main()
