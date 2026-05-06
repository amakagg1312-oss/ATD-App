"""Find player table pointer to understand new pointer structure."""

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
    
    # Find player table by searching for "Victor" (Wembanyama)
    print("Finding player table...")
    victor_bytes = b'V\x00i\x00c\x00t\x00o\x00r\x00\x00\x00'
    
    player_table = None
    mbr = MBI()
    addr = 0
    
    while addr < 0x100000000:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                idx = buf.find(victor_bytes)
                if idx >= 0:
                    first_addr = mbr.BaseAddress + idx
                    player_entry = first_addr - 0x28  # Player first name offset
                    player_table = player_entry - (player_entry % 1176)
                    print(f"  Found Victor at 0x{first_addr:X}")
                    print(f"  Player table base: 0x{player_table:X}")
                    break
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    if player_table:
        # Search for pointer to player table
        print(f"\nSearching for pointer to player table 0x{player_table:X}...")
        target_bytes = player_table.to_bytes(8, 'little')
        
        found = []
        mbr = MBI()
        addr = 0
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
                            # Only show pointers outside player table
                            if ptr_addr < player_table or ptr_addr > player_table + 1000000:
                                found.append(ptr_addr)
                            idx = buf.find(target_bytes, idx + 1)
                    
                    regions += 1
                    if regions % 1000 == 0:
                        print(f"  Scanned {regions} regions, found {len(found)}...")
            
            addr = mbr.BaseAddress + mbr.RegionSize
        
        print(f"\nFound {len(found)} pointers to player table:")
        for ptr_addr in found[:20]:
            print(f"  0x{ptr_addr:X} -> 0x{player_table:X}")

if __name__ == "__main__":
    main()
