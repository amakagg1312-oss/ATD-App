"""Search for team table using roster pointer pattern."""

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
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    # Staff entry roster pointer array at 0x018 points to player names
    # Let's search for similar roster arrays that could be team-based
    
    # First, let's look at the staff roster array structure
    staff_roster_ptr = 0x2A82B17D0  # Nick Nurse's roster array
    roster_data = read_memory(h, staff_roster_ptr, 16 * 8)
    
    if roster_data:
        print("Staff roster array (Nick Nurse):")
        for i in range(16):
            ptr = struct.unpack('<Q', roster_data[i*8:i*8+8])[0]
            if ptr == 0:
                print(f"  [{i}] 0x0 (end)")
                break
            if 0x10000000 < ptr < 0x300000000:
                name_data = read_memory(h, ptr, 40)
                if name_data:
                    name = name_data.decode('utf-16-le', errors='ignore').split('\x00')[0]
                    print(f"  [{i}] 0x{ptr:X} -> {name}")
    
    # Now let's search for other roster arrays (one per team)
    # These should be in a similar memory region
    
    print(f"\n{'='*80}")
    print("Searching for team roster arrays...")
    
    # Search in the region 0x2A7AB0000 - 0x2A8000000
    search_start = 0x2A7AB0000
    search_end = 0x2A8000000
    
    # Look for arrays of pointers to player names
    mbr = MBI()
    addr = search_start
    
    found_arrays = []
    
    while addr < search_end:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0:
            if mbr.RegionSize >= 16 * 8:  # At least 16 pointers
                buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x10000))
                if buf:
                    # Look for sequences of valid pointers
                    for i in range(0, min(len(buf), 0x10000) - 8, 8):
                        ptr = struct.unpack('<Q', buf[i:i+8])[0]
                        if 0x10000000 < ptr < 0x300000000:
                            # Check if this points to a player name
                            name_data = read_memory(h, ptr, 40)
                            if name_data:
                                try:
                                    name = name_data.decode('utf-16-le', errors='ignore').split('\x00')[0]
                                    if name and 2 < len(name) < 20 and name.isalpha():
                                        # Found a potential roster array start
                                        # Count consecutive pointers
                                        count = 0
                                        for j in range(i, min(len(buf), i + 20 * 8), 8):
                                            inner_ptr = struct.unpack('<Q', buf[j:j+8])[0]
                                            if 0x10000000 < inner_ptr < 0x300000000:
                                                inner_name = read_memory(h, inner_ptr, 40)
                                                if inner_name:
                                                    inner_text = inner_name.decode('utf-16-le', errors='ignore').split('\x00')[0]
                                                    if inner_text and 2 < len(inner_text) < 20:
                                                        count += 1
                                                    else:
                                                        break
                                                else:
                                                    break
                                            else:
                                                break
                                        
                                        if count >= 10:  # At least 10 players
                                            array_addr = mbr.BaseAddress + i
                                            if array_addr not in [a[0] for a in found_arrays]:
                                                found_arrays.append((array_addr, count))
                                                print(f"  Found roster array at 0x{array_addr:X} ({count} players)")
                                                # Show first 5 names
                                                for k in range(min(5, count)):
                                                    p = struct.unpack('<Q', buf[i + k*8:i + k*8 + 8])[0]
                                                    nd = read_memory(h, p, 40)
                                                    if nd:
                                                        n = nd.decode('utf-16-le', errors='ignore').split('\x00')[0]
                                                        print(f"    [{k}] {n}")
                                                break
                break
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nFound {len(found_arrays)} roster arrays")

if __name__ == "__main__":
    main()
