"""Find actual team table and playbook references."""

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
    
    # Team name locations found:
    # 76ers: 0x29B255038
    # Bucks: 0x29B2552E0 (diff: 0x2A8 = 680)
    # Bulls: 0x29B255588 (diff: 0x2A8 = 680)
    # Celtics: 0x29B255AD8 (diff: 0x550 = 1360)
    
    # These are likely string pointers or references, not the actual team structures
    # The actual team table has stride 5672 (0x1628)
    
    # Let's search for the team table by looking for a region with team-like data
    # Team name is at offset 0x2E2, so we need to find structures spaced by 5672
    
    # First, let's look at what's at the team name locations
    print("Examining team name locations...")
    
    team_name_locs = [0x29B255038, 0x29B2552E0, 0x29B255588, 0x29B255AD8]
    
    for loc in team_name_locs:
        # Read 100 bytes around the location
        data = read_memory(h, loc - 20, 120)
        if data:
            # Check if this is a pointer (8 bytes pointing to the string)
            ptr_before = struct.unpack('<Q', data[:8])[0]
            if 0x10000000 < ptr_before < 0x300000000:
                print(f"\n0x{loc:X}: pointer at -20: 0x{ptr_before:X}")
                # Read at the pointer
                ptr_data = read_memory(h, ptr_before, 64)
                if ptr_data:
                    try:
                        text = ptr_data[:40].decode('utf-16-le', errors='ignore')
                        print(f"  -> {text[:30]}")
                    except:
                        pass
            
            # Show context
            for off in range(0, min(len(data), 80), 16):
                chunk = data[off:off+16]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                try:
                    text = chunk.decode('utf-16-le', errors='ignore')
                    printable = ''.join(c if c.isprintable() else '.' for c in text)
                    print(f"  [{off-20:04X}] {hex_str:<48} {printable}")
                except:
                    print(f"  [{off-20:04X}] {hex_str}")
    
    # Now let's search for the actual team table
    # The team table should have 30 entries spaced by 5672
    # Each entry should have a name at offset 0x2E2
    
    print(f"\n{'='*80}")
    print("Searching for team table with stride 5672...")
    
    # Search around the team name region
    search_start = 0x29B250000
    search_end = 0x29B280000
    
    # Look for a pattern where team names appear at regular intervals
    team_stride = 5672
    name_offset = 0x2E2
    
    # Read a large block
    for base in range(search_start, search_end, 0x10000):
        block = read_memory(h, base, 0x10000)
        if block:
            # Look for "76ers" in this block
            idx = block.find(b'7\x006\x00e\x00r\x00s\x00')
            if idx >= 0:
                # Calculate potential team base
                potential_base = base + idx - name_offset
                
                # Verify by checking if next team is at correct offset
                next_team_addr = potential_base + team_stride
                next_name_addr = next_team_addr + name_offset
                
                next_data = read_memory(h, next_name_addr, 40)
                if next_data:
                    next_name = next_data.decode('utf-16-le', errors='ignore').split('\x00')[0]
                    if next_name and len(next_name) > 2:
                        print(f"\nFound team table!")
                        print(f"  Base: 0x{potential_base:X}")
                        print(f"  Team 0: 76ers")
                        print(f"  Team 1: {next_name}")
                        
                        # Dump first 3 teams
                        for i in range(3):
                            team_addr = potential_base + (i * team_stride)
                            name_addr = team_addr + name_offset
                            name_data = read_memory(h, name_addr, 40)
                            if name_data:
                                name = name_data.decode('utf-16-le', errors='ignore').split('\x00')[0]
                                print(f"  Team {i}: {name} @ 0x{team_addr:X}")
                                
                                # Dump team structure pointers
                                team_raw = read_memory(h, team_addr, 256)
                                if team_raw:
                                    for off in range(0, 256, 8):
                                        val = struct.unpack('<Q', team_raw[off:off+8])[0]
                                        if 0x10000000 < val < 0x300000000:
                                            # Check what this points to
                                            ptr_data = read_memory(h, val, 64)
                                            if ptr_data:
                                                # Check for playbook-like data
                                                small_ints = []
                                                for j in range(0, 32, 2):
                                                    w = struct.unpack('<H', ptr_data[j:j+2])[0]
                                                    if 0 < w < 300:
                                                        small_ints.append(w)
                                                
                                                if len(small_ints) > 5:
                                                    print(f"    [{off:03X}] 0x{val:X} -> PLAYBOOK IDS: {small_ints[:10]}")
                                                else:
                                                    try:
                                                        text = ptr_data[:30].decode('utf-16-le', errors='ignore')
                                                        printable = ''.join(c if c.isprintable() else '.' for c in text)
                                                        if len([c for c in printable if c.isalpha()]) > 3:
                                                            print(f"    [{off:03X}] 0x{val:X} -> STRING: {printable[:25]}")
                                                    except:
                                                        hex_str = ' '.join(f'{b:02X}' for b in ptr_data[:16])
                                                        print(f"    [{off:03X}] 0x{val:X} -> {hex_str}")

if __name__ == "__main__":
    main()
