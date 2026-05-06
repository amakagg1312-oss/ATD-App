"""Direct search for Nurse in known region."""

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
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    nurse_bytes = b'N\x00u\x00r\x00s\x00e\x00\x00\x00'
    
    # Search all regions and print info
    print("Scanning all regions...")
    mbr = MBI()
    addr = 0
    regions = 0
    total_size = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0:
            regions += 1
            total_size += mbr.RegionSize
            
            # Check if this region contains the known staff table
            if mbr.BaseAddress <= 0x2A84DD940 < mbr.BaseAddress + mbr.RegionSize:
                print(f"\n  Region containing staff table:")
                print(f"    Base: 0x{mbr.BaseAddress:X}")
                print(f"    Size: 0x{mbr.RegionSize:X} ({mbr.RegionSize})")
                print(f"    Protect: 0x{mbr.Protect:X}")
                
                # Try to read and search
                chunk_size = min(mbr.RegionSize, 0x1000000)
                buf = read_memory(h, mbr.BaseAddress, chunk_size)
                if buf:
                    idx = buf.find(nurse_bytes)
                    if idx >= 0:
                        print(f"    Found 'Nurse' at offset 0x{idx:X}")
                    else:
                        print(f"    'Nurse' NOT found in first 0x{chunk_size:X} bytes")
                else:
                    print(f"    Could not read region")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nTotal regions: {regions}")
    print(f"Total size: 0x{total_size:X} ({total_size / 1024 / 1024 / 1024:.2f} GB)")

if __name__ == "__main__":
    main()
