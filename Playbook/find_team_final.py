"""Find actual team table by searching for team names with correct structure."""

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
    
    # We know team names are stored as length-prefixed UTF-16 strings
    # "76ers" is at 0x29B255038
    # The format is: 4-byte length, then UTF-16 string
    
    # Let's search for the team table by looking for consecutive team names
    # with the team stride of 5672
    
    print("Searching for team table...")
    
    # Search for "76ers" and then check if there's a team structure
    team_name_bytes = b'7\x006\x00e\x00r\x00s\x00'
    
    mbr = MBI()
    addr = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                idx = buf.find(team_name_bytes)
                if idx >= 0:
                    name_addr = mbr.BaseAddress + idx
                    print(f"Found '76ers' at 0x{name_addr:X}")
                    
                    # Read 4 bytes before the name (length prefix)
                    len_data = read_memory(h, name_addr - 4, 4)
                    if len_data:
                        name_len = struct.unpack('<I', len_data)[0]
                        print(f"  Length prefix: {name_len}")
                    
                    # Now search for the team table by looking for a region
                    # where team names appear at offset 0x2E2 from team base
                    # with stride 5672
                    
                    # Try different offsets from the name to find the team base
                    for name_offset in [0x2E2, 0x2E0, 0x2D8, 0x2F0, 0x300]:
                        team_base = name_addr - name_offset
                        
                        # Check if next team is at correct offset
                        next_team = team_base + 5672
                        next_name = next_team + name_offset
                        
                        next_data = read_memory(h, next_name, 40)
                        if next_data:
                            next_name_str = next_data.decode('utf-16-le', errors='ignore').split('\x00')[0]
                            if next_name_str and 2 < len(next_name_str) < 20:
                                print(f"\n  Potential team table found!")
                                print(f"  Base: 0x{team_base:X}")
                                print(f"  Name offset: 0x{name_offset:X}")
                                print(f"  Team 0: 76ers")
                                print(f"  Team 1: {next_name_str}")
                                
                                # Verify with team 2
                                team2 = team_base + 2 * 5672
                                team2_name = team2 + name_offset
                                team2_data = read_memory(h, team2_name, 40)
                                if team2_data:
                                    team2_str = team2_data.decode('utf-16-le', errors='ignore').split('\x00')[0]
                                    print(f"  Team 2: {team2_str}")
                                
                                # Dump team structure
                                print(f"\n  Team structure pointers:")
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
                                                    # Check for string
                                                    try:
                                                        text = ptr_data[:30].decode('utf-16-le', errors='ignore')
                                                        printable = ''.join(c if c.isprintable() else '.' for c in text)
                                                        if len([c for c in printable if c.isalpha()]) > 3:
                                                            print(f"    [{off:03X}] 0x{val:X} -> {printable[:25]}")
                                                    except:
                                                        pass
                                return
            break
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print("Team table not found!")

if __name__ == "__main__":
    main()
