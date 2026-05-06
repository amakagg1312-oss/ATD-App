"""Search all memory for static pointer to staff table."""

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
    
    # Search for pointer to 0x295144838 in all memory
    target = 0x295144838
    target_bytes = target.to_bytes(8, 'little')
    
    print(f"Searching all memory for pointer to 0x{target:X}...")
    
    mbr = MBI()
    addr = 0
    found = []
    regions = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.Protect in [0x02, 0x04, 0x08, 0x20, 0x40, 0x80]:
            if mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
                buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
                if buf:
                    idx = buf.find(target_bytes)
                    while idx >= 0:
                        ptr_addr = mbr.BaseAddress + idx
                        # Skip if in game data region
                        if ptr_addr < 0x10000000 or ptr_addr > 0x300000000:
                            found.append(ptr_addr)
                        idx = buf.find(target_bytes, idx + 1)
                
                regions += 1
                if regions % 1000 == 0:
                    print(f"  Scanned {regions} regions, found {len(found)}...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nFound {len(found)} pointers:")
    for ptr_addr in found[:20]:
        print(f"  0x{ptr_addr:X} -> 0x{target:X}")

if __name__ == "__main__":
    main()
