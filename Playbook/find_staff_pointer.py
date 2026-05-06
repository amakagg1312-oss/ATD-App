"""Find the base pointer for the staff table."""

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
    
    # Staff table base we found
    table_base = 0x2A84DD940
    
    print(f"Searching for pointer to 0x{table_base:X}...")
    
    # Known pointers from offsets file
    known_ptrs = {
        'Player': 0x7E1F878 - 0x68,  # 132244216
        'Team': 0x7E1F878 - 0x38,    # 132244248
        'Staff': 0x7E1F878,          # 132244312
        'Stadium': 0x7E1F878 - 0x40, # 132244240
    }
    
    # Search around known pointer region
    print(f"\nSearching around known pointer region...")
    for name, ptr_addr in known_ptrs.items():
        for offset in range(-200, 200, 8):
            check_addr = ptr_addr + offset
            ptr_buf = read_memory(h, check_addr, 8)
            if ptr_buf:
                ptr_val = int.from_bytes(ptr_buf, 'little')
                if ptr_val == table_base:
                    print(f"  FOUND: {name} region + {offset}: 0x{check_addr:X} -> 0x{table_base:X}")
    
    # Search the entire pointer region (0x7E1F000 - 0x7E20000)
    print(f"\nSearching full pointer region (0x7E1F000 - 0x7E20000)...")
    for addr in range(0x7E1F000, 0x7E20000, 8):
        ptr_buf = read_memory(h, addr, 8)
        if ptr_buf:
            ptr_val = int.from_bytes(ptr_buf, 'little')
            if ptr_val == table_base:
                print(f"  FOUND: 0x{addr:X} -> 0x{table_base:X}")
    
    # If not found, search in a wider range
    print(f"\nSearching wider region (0x7E00000 - 0x7F00000)...")
    found = False
    for addr in range(0x7E00000, 0x7F00000, 8):
        ptr_buf = read_memory(h, addr, 8)
        if ptr_buf:
            ptr_val = int.from_bytes(ptr_buf, 'little')
            if ptr_val == table_base:
                print(f"  FOUND: 0x{addr:X} -> 0x{table_base:X}")
                found = True
    
    if not found:
        print(f"  Not found in 0x7E00000 - 0x7F00000")
        
        # Try searching in the module base region
        print(f"\nSearching module region...")
        mbr = MBI()
        addr = 0
        while True:
            result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
            if result == 0:
                break
            
            if mbr.State == 0x1000 and mbr.RegionSize > 0:
                # Only search small regions that might contain pointers
                if mbr.RegionSize < 0x100000:
                    buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x10000))
                    if buf:
                        for i in range(0, len(buf) - 8, 8):
                            ptr_val = int.from_bytes(buf[i:i+8], 'little')
                            if ptr_val == table_base:
                                print(f"  FOUND: 0x{mbr.BaseAddress + i:X} -> 0x{table_base:X}")
            
            addr = mbr.BaseAddress + mbr.RegionSize

if __name__ == "__main__":
    main()
