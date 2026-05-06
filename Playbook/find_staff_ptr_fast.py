"""Find staff pointer - optimized search."""

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

def search_region_for_pointer(h, region_base, region_size, target, chunk_size=0x10000):
    """Search a memory region for a pointer to target address."""
    found = []
    for offset in range(0, region_size, chunk_size):
        size = min(chunk_size, region_size - offset)
        buf = read_memory(h, region_base + offset, size)
        if buf:
            for i in range(0, len(buf) - 8, 8):
                ptr_val = int.from_bytes(buf[i:i+8], 'little')
                if ptr_val == target:
                    found.append(region_base + offset + i)
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
    
    table_base = 0x2A84DD940
    
    print(f"Searching for pointer to 0x{table_base:X}...")
    
    # Strategy 1: Search known pointer-like regions
    # The old pointers were around 0x7E1F000, let's search a wider range
    print(f"\n1. Searching 0x7E00000 - 0x7F00000...")
    found = search_region_for_pointer(h, 0x7E00000, 0x100000, table_base)
    for addr in found:
        print(f"  FOUND: 0x{addr:X} -> 0x{table_base:X}")
    
    # Strategy 2: Search around player/team pointers (they should be nearby)
    # First find player pointer
    print(f"\n2. Searching for player pointer first...")
    player_table = None
    
    # Search for a known player name to find player table
    player_bytes = b'V\x00i\x00c\x00t\x00o\x00r\x00\x00\x00'  # "Victor" (Wembanyama)
    mbr = MBI()
    addr = 0
    while addr < 0x100000000:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                idx = buf.find(player_bytes)
                if idx >= 0:
                    player_addr = mbr.BaseAddress + idx
                    # Player first name is at offset 0x28
                    player_entry = player_addr - 0x28
                    player_table = player_entry - (player_entry % 1176)
                    print(f"  Found Victor at 0x{player_addr:X}")
                    print(f"  Player table base: 0x{player_table:X}")
                    break
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    if player_table:
        # Search for pointer to player table
        print(f"\n3. Searching for pointer to player table 0x{player_table:X}...")
        found = search_region_for_pointer(h, 0x7E00000, 0x100000, player_table)
        for addr in found:
            print(f"  Player pointer: 0x{addr:X} -> 0x{player_table:X}")
        
        # Now search near the player pointer for staff pointer
        print(f"\n4. Searching near player pointers for staff pointer...")
        for ptr_addr in found:
            # Check +/- 500 bytes
            for offset in range(-500, 500, 8):
                check_addr = ptr_addr + offset
                ptr_buf = read_memory(h, check_addr, 8)
                if ptr_buf:
                    ptr_val = int.from_bytes(ptr_buf, 'little')
                    if ptr_val == table_base:
                        print(f"  FOUND STAFF: 0x{check_addr:X} -> 0x{table_base:X}")
                        print(f"    (offset from player ptr: {offset})")

if __name__ == "__main__":
    main()
