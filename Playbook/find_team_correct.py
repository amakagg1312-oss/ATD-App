"""Find correct team structure and playbook references."""

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
    
    # We know "76ers" is at 0x29B255038
    # Let's read around that address to understand the structure
    team_name_addr = 0x29B255038
    
    # Read 200 bytes around the team name
    data = read_memory(h, team_name_addr - 200, 500)
    if data:
        print("Data around '76ers' string:")
        for off in range(0, len(data), 16):
            chunk = data[off:off+16]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            try:
                text = chunk.decode('utf-16-le', errors='ignore')
                printable = ''.join(c if c.isprintable() else '.' for c in text)
                print(f"  [{off-200:04X}] {hex_str:<48} {printable}")
            except:
                print(f"  [{off-200:04X}] {hex_str}")
    
    # The team name is at offset 0x2E2 from team base
    # So team base = 0x29B255038 - 0x2E2 = 0x29B254D56
    # But that doesn't seem right. Let's search for the actual team base
    
    # Search backwards from team name for the start of the structure
    print(f"\nSearching for team base...")
    
    # Read a large block and look for structure patterns
    block = read_memory(h, 0x29B254000, 0x5000)
    if block:
        # Look for 76ers
        idx = block.find(b'7\x006\x00e\x00r\x00s\x00')
        if idx >= 0:
            print(f"'76ers' found at offset 0x{idx:X} in block")
            
            # The team name offset should be 0x2E2 (738)
            # So team base in block = idx - 0x2E2
            team_base_in_block = idx - 0x2E2
            print(f"Team base in block: 0x{team_base_in_block:X}")
            
            # Read the team structure
            team_start = 0x29B254000 + team_base_in_block
            print(f"Team base address: 0x{team_start:X}")
            
            # Dump the team structure
            team_raw = read_memory(h, team_start, 512)
            if team_raw:
                print(f"\nTeam structure (first 512 bytes):")
                for off in range(0, 512, 16):
                    chunk = team_raw[off:off+16]
                    hex_str = ' '.join(f'{b:02X}' for b in chunk)
                    if len(chunk) >= 8:
                        qword = struct.unpack('<Q', chunk[:8])[0]
                        marker = " <-- PTR" if 0x10000000 < qword < 0x300000000 else ""
                        print(f"  [{off:03X}] {hex_str}{marker}")
    
    # Now let's find the actual team table by looking for consecutive team names
    print(f"\n{'='*80}")
    print("Finding team table by searching for multiple team names...")
    
    team_names = [b'B\x00u\x00c\x00k\x00s\x00', b'C\x00e\x00l\x00t\x00i\x00c\x00s\x00', b'B\x00u\x00l\x00l\x00s\x00']
    
    for name_bytes in team_names:
        # Search in a limited range
        for base in range(0x29B250000, 0x29B270000, 0x1000):
            buf = read_memory(h, base, 0x1000)
            if buf:
                idx = buf.find(name_bytes)
                if idx >= 0:
                    loc = base + idx
                    print(f"Found '{name_bytes.decode('utf-16-le', errors='ignore')}' at 0x{loc:X}")

if __name__ == "__main__":
    main()
