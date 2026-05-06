"""Dump memory around roster arrays to find team structure."""

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
    
    # Roster arrays
    roster_addrs = [0x2A82B17D0, 0x2A82B2DF8, 0x2A82B4420]
    team_names_expected = ["76ers", "Bucks", "Cavaliers"]
    
    print("Dumping memory around roster arrays...")
    
    for i, roster_addr in enumerate(roster_addrs):
        print(f"\n{'='*80}")
        print(f"Roster array {i} ({team_names_expected[i]}): 0x{roster_addr:X}")
        print(f"{'='*80}")
        
        # Read 0x1000 bytes before the roster array
        block_start = roster_addr - 0x1000
        block = read_memory(h, block_start, 0x2000)
        
        if block:
            # Show hex dump of first 512 bytes
            print(f"\nFirst 512 bytes (from 0x{block_start:X}):")
            for off in range(0, 512, 16):
                chunk = block[off:off+16]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                
                # Check for strings
                try:
                    text = chunk.decode('utf-16-le', errors='ignore')
                    printable = ''.join(c if c.isprintable() else '.' for c in text)
                    has_text = sum(1 for c in printable if c.isalpha()) > 3
                except:
                    printable = ""
                    has_text = False
                
                if has_text:
                    print(f"  [{off:04X}] {hex_str:<48} {printable}")
                else:
                    # Check for pointers
                    if len(chunk) >= 8:
                        qword = struct.unpack('<Q', chunk[:8])[0]
                        marker = " <-- PTR" if 0x10000000 < qword < 0x300000000 else ""
                        print(f"  [{off:04X}] {hex_str}{marker}")
            
            # Search for team name in this block
            team_name = team_names_expected[i].encode('utf-16-le') + b'\x00\x00'
            idx = block.find(team_name)
            if idx >= 0:
                print(f"\n  Found '{team_names_expected[i]}' at offset 0x{idx:X}")
                print(f"  Absolute address: 0x{block_start + idx:X}")
                
                # Calculate potential team base
                for name_off in [0x2E2, 0x2E0, 0x2D8, 0x2F0, 0x300, 0x2C0, 0x2A0]:
                    team_base = block_start + idx - name_off
                    print(f"\n  If name offset = 0x{name_off:X}:")
                    print(f"    Team base: 0x{team_base:X}")
                    
                    # Check if roster pointer is at 0x018
                    roster_ptr_addr = team_base + 0x018
                    roster_ptr = read_memory(h, roster_ptr_addr, 8)
                    if roster_ptr:
                        ptr_val = struct.unpack('<Q', roster_ptr)[0]
                        if ptr_val == roster_addr:
                            print(f"    *** MATCH! Roster pointer at 0x018 points to 0x{ptr_val:X}")
                        else:
                            print(f"    Roster pointer at 0x018: 0x{ptr_val:X} (expected 0x{roster_addr:X})")

if __name__ == "__main__":
    main()
