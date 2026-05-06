"""Dump team structure to find playbook references."""

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
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    # Team structure starts at roster array address
    # Team stride: 5672
    # Team name offset: 0x2E2
    
    team_base = 0x2A82B17D0  # 76ers
    team_stride = 5672
    name_offset = 0x2E2
    
    print(f"Team table base: 0x{team_base:X}")
    print(f"Team stride: {team_stride} (0x{team_stride:X})")
    print(f"Team name offset: 0x{name_offset:X}")
    
    # Dump first 5 teams
    print(f"\n{'='*80}")
    print("TEAM STRUCTURE ANALYSIS")
    print(f"{'='*80}")
    
    for i in range(5):
        team_addr = team_base + (i * team_stride)
        
        # Read team name
        name_data = read_memory(h, team_addr + name_offset, 40)
        if name_data:
            team_name = name_data.decode('utf-16-le', errors='ignore').split('\x00')[0]
        else:
            team_name = "(unreadable)"
        
        print(f"\nTeam {i}: {team_name} @ 0x{team_addr:X}")
        print(f"{'-'*80}")
        
        # Read full team structure
        team_raw = read_memory(h, team_addr, team_stride)
        if team_raw:
            # Show all pointers and interesting data
            for off in range(0, team_stride, 8):
                val = struct.unpack('<Q', team_raw[off:off+8])[0]
                
                # Check for pointers
                if 0x10000000 < val < 0x300000000:
                    # Check what this points to
                    ptr_data = read_memory(h, val, 64)
                    if ptr_data:
                        # Check for playbook indices (small integers)
                        pb_ids = []
                        for j in range(0, 40, 2):
                            w = struct.unpack('<H', ptr_data[j:j+2])[0]
                            if 0 < w < 300:
                                pb_ids.append(w)
                        
                        if len(pb_ids) > 5:
                            print(f"  [{off:03X}] 0x{val:X} -> PLAYBOOK IDS: {pb_ids[:15]}")
                        else:
                            # Check for string
                            try:
                                text = ptr_data[:30].decode('utf-16-le', errors='ignore')
                                printable = ''.join(c if c.isprintable() else '.' for c in text)
                                if len([c for c in printable if c.isalpha()]) > 3:
                                    print(f"  [{off:03X}] 0x{val:X} -> STRING: {printable[:25]}")
                            except:
                                pass
                
                # Check for non-zero values that aren't pointers
                elif val > 0 and val < 0x10000000:
                    # Could be an ID or count
                    if val < 1000:
                        print(f"  [{off:03X}] = {val} (0x{val:X})")

if __name__ == "__main__":
    main()
