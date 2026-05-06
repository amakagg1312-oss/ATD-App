"""Find team table by searching for pointers to team names."""

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
    
    # Team name locations
    team_name_locs = [
        0x29B255038,  # 76ers
        0x29B2552E0,  # Bucks
        0x29B255588,  # Bulls
        0x29B255AD8,  # Celtics
        0x29B256AC8,  # Jazz
        0x29B257D60,  # Nuggets
    ]
    
    # Search for pointers to these team names
    print("Searching for pointers to team names...")
    
    team_stride = 5672
    
    mbr = MBI()
    addr = 0
    regions = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                # Look for pointers to team names
                for name_loc in team_name_locs[:3]:  # Check first 3
                    name_bytes = name_loc.to_bytes(8, 'little')
                    idx = buf.find(name_bytes)
                    while idx >= 0:
                        ptr_addr = mbr.BaseAddress + idx
                        print(f"  Found pointer to 0x{name_loc:X} at 0x{ptr_addr:X}")
                        
                        # Check if this could be part of a team table
                        # Team name should be at offset 0x2E2 from team base
                        # So team base = ptr_addr - 0x2E2
                        team_base = ptr_addr - 0x2E2
                        
                        # Check if next team is at correct offset
                        next_team = team_base + team_stride
                        next_name_ptr_addr = next_team + 0x2E2
                        
                        # Read the pointer at next_name_ptr_addr
                        next_ptr = read_memory(h, next_name_ptr_addr, 8)
                        if next_ptr:
                            next_name_loc = struct.unpack('<Q', next_ptr)[0]
                            if next_name_loc in team_name_locs:
                                print(f"    -> Team table found!")
                                print(f"    Base: 0x{team_base:X}")
                                print(f"    Team 0 name ptr: 0x{ptr_addr:X} -> 0x{name_loc:X}")
                                print(f"    Team 1 name ptr: 0x{next_name_ptr_addr:X} -> 0x{next_name_loc:X}")
                                
                                # Dump team structure
                                team_raw = read_memory(h, team_base, 512)
                                if team_raw:
                                    print(f"\n    Team structure pointers:")
                                    for off in range(0, 512, 8):
                                        val = struct.unpack('<Q', team_raw[off:off+8])[0]
                                        if 0x10000000 < val < 0x300000000:
                                            ptr_data = read_memory(h, val, 64)
                                            if ptr_data:
                                                # Check for playbook indices
                                                pb_ids = []
                                                for j in range(0, 40, 2):
                                                    w = struct.unpack('<H', ptr_data[j:j+2])[0]
                                                    if 0 < w < 300:
                                                        pb_ids.append(w)
                                                
                                                if len(pb_ids) > 5:
                                                    print(f"      [{off:03X}] 0x{val:X} -> PLAYBOOK: {pb_ids[:10]}")
                                                else:
                                                    # Check for string
                                                    try:
                                                        text = ptr_data[:30].decode('utf-16-le', errors='ignore')
                                                        printable = ''.join(c if c.isprintable() else '.' for c in text)
                                                        if len([c for c in printable if c.isalpha()]) > 3:
                                                            print(f"      [{off:03X}] 0x{val:X} -> {printable[:25]}")
                                                    except:
                                                        pass
                                return
                        idx = buf.find(name_bytes, idx + 1)
            
            regions += 1
            if regions % 2000 == 0:
                print(f"  Scanned {regions} regions...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print("Team table not found!")

if __name__ == "__main__":
    main()
