"""Find team table using consecutive team name search."""

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

def decode_wstring(data, max_chars=30):
    try:
        raw = data[:max_chars*2]
        return raw.decode('utf-16-le', errors='ignore').split('\x00')[0].strip()
    except:
        return ""

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
    
    # Team name offset and stride
    team_stride = 5672
    
    # Search for "76ers" and then verify team table structure
    print("Searching for team table...")
    
    # We know "76ers" is at 0x29B255038
    # Let's search for a region where team names appear at regular intervals
    
    # Search in the region around known team names
    search_start = 0x29B250000
    search_end = 0x29B260000
    
    # Read the entire region
    for base in range(search_start, search_end, 0x1000):
        buf = read_memory(h, base, 0x1000)
        if buf:
            # Look for "76ers"
            idx = buf.find(b'7\x006\x00e\x00r\x00s\x00')
            if idx >= 0:
                name_addr = base + idx
                print(f"Found '76ers' at 0x{name_addr:X}")
                
                # Try different name offsets
                for name_off in range(0, 0x1000, 8):
                    team_base = name_addr - name_off
                    
                    # Check if this could be a team table
                    # Read first 8 bytes of team structure
                    team_header = read_memory(h, team_base, 16)
                    if team_header:
                        # Check for pointers or valid data
                        qword0 = struct.unpack('<Q', team_header[:8])[0]
                        qword1 = struct.unpack('<Q', team_header[8:16])[0]
                        
                        # If both look like pointers, this might be the team base
                        if 0x10000000 < qword0 < 0x300000000 or 0x10000000 < qword1 < 0x300000000:
                            # Check next team
                            next_team = team_base + team_stride
                            next_name = next_team + name_off
                            next_data = read_memory(h, next_name, 40)
                            if next_data:
                                next_name_str = decode_wstring(next_data, 20)
                                if next_name_str and 2 < len(next_name_str) < 20:
                                    print(f"\n  Potential team table!")
                                    print(f"  Base: 0x{team_base:X}")
                                    print(f"  Name offset: 0x{name_off:X}")
                                    print(f"  Team 0: 76ers")
                                    print(f"  Team 1: {next_name_str}")
                                    
                                    # Check team 2
                                    team2 = team_base + 2 * team_stride
                                    team2_name = team2 + name_off
                                    team2_data = read_memory(h, team2_name, 40)
                                    if team2_data:
                                        team2_str = decode_wstring(team2_data, 20)
                                        print(f"  Team 2: {team2_str}")
                                    
                                    # Dump team structure
                                    print(f"\n  Team structure:")
                                    team_raw = read_memory(h, team_base, 512)
                                    if team_raw:
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
                                                        print(f"    [{off:03X}] 0x{val:X} -> PLAYBOOK: {pb_ids[:10]}")
                                                    else:
                                                        try:
                                                            text = ptr_data[:30].decode('utf-16-le', errors='ignore')
                                                            printable = ''.join(c if c.isprintable() else '.' for c in text)
                                                            if len([c for c in printable if c.isalpha()]) > 3:
                                                                print(f"    [{off:03X}] 0x{val:X} -> {printable[:25]}")
                                                        except:
                                                            pass
                                    return
    
    print("Team table not found!")

if __name__ == "__main__":
    main()
