"""Find team table by examining 76ers location."""

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
    
    # "76ers" is at 0x29B255038
    # Let's read a large block around this address
    block_start = 0x29B254000
    block_size = 0x10000
    
    block = read_memory(h, block_start, block_size)
    if not block:
        print("Could not read memory block!")
        return
    
    # Find all team names in this block
    team_names = [b'76ers', b'Bucks', b'Bulls', b'Celtics', b'Clippers', b'Grizzlies', 
                  b'Hawks', b'Heat', b'Hornets', b'Knicks', b'Lakers', b'Magic',
                  b'Nets', 'Nuggets', 'Pacers', 'Pelicans', 'Pistons', 'Raptors',
                  'Rockets', 'Spurs', 'Suns', 'Thunder', 'Timberwolves', 'Trail Blazers',
                  'Jazz', 'Warriors', 'Wizards', 'Mavericks']
    
    print("Searching for team names in block...")
    
    found_teams = []
    for name in team_names:
        if isinstance(name, str):
            name_bytes = name.encode('utf-16-le') + b'\x00\x00'
        else:
            name_bytes = name
        
        idx = block.find(name_bytes)
        while idx >= 0:
            loc = block_start + idx
            found_teams.append((loc, name if isinstance(name, str) else name.decode('utf-16-le', errors='ignore')))
            idx = block.find(name_bytes, idx + 2)
    
    # Sort by location
    found_teams.sort(key=lambda x: x[0])
    
    print(f"\nFound {len(found_teams)} team names:")
    for loc, name in found_teams:
        print(f"  0x{loc:X}: {name}")
    
    # Calculate distances between consecutive teams
    if len(found_teams) > 1:
        print(f"\nDistances between teams:")
        for i in range(1, len(found_teams)):
            diff = found_teams[i][0] - found_teams[i-1][0]
            print(f"  {found_teams[i-1][1]} -> {found_teams[i][1]}: 0x{diff:X} ({diff})")
    
    # Now let's examine the structure around the first team name
    if found_teams:
        first_loc = found_teams[0][0]
        print(f"\n{'='*80}")
        print(f"Examining structure around '{found_teams[0][1]}' at 0x{first_loc:X}")
        
        # Read 100 bytes before and 200 bytes after
        data = read_memory(h, first_loc - 100, 300)
        if data:
            for off in range(0, len(data), 16):
                chunk = data[off:off+16]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                try:
                    text = chunk.decode('utf-16-le', errors='ignore')
                    printable = ''.join(c if c.isprintable() else '.' for c in text)
                    print(f"  [{off-100:04X}] {hex_str:<48} {printable}")
                except:
                    print(f"  [{off-100:04X}] {hex_str}")

if __name__ == "__main__":
    main()
