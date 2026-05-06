"""Extract strings from region 0x259A0000 to see if it contains play names."""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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
    
    print(f"PID: {pid}")
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    # Region that contains team abbreviations and strings
    region = 0x259A0000
    region_size = 0x100000  # 1MB
    
    print(f"Reading region 0x{region:X} (size: 0x{region_size:X})...")
    
    data = read_memory(h, region, region_size)
    if not data:
        print("Failed to read region!")
        return
    
    print(f"Read {len(data)} bytes")
    
    # Extract all UTF-16LE strings
    strings = []
    i = 0
    while i < len(data) - 2:
        # Find null terminator
        null_pos = data.find(b'\x00\x00', i)
        if null_pos == -1:
            break
        
        # Find start of string
        start = null_pos + 2
        if start % 2 != 0:
            start += 1
        
        # Find next null
        next_null = data.find(b'\x00\x00', start)
        if next_null == -1:
            next_null = len(data)
        
        s_bytes = data[start:next_null]
        if len(s_bytes) >= 2:
            try:
                s = s_bytes.decode('utf-16-le', errors='replace').strip()
                if s and len(s) > 1:
                    strings.append((start, s))
            except:
                pass
        
        i = null_pos + 2
    
    print(f"Found {len(strings)} strings")
    
    # Show all strings
    print("\nAll strings in region:")
    for off, s in strings[:200]:
        print(f"  [{off:06X}] {s}")
    
    # Look for play-like strings (containing team abbreviations and numbers)
    print("\n\nPlay-like strings (with team abbreviations and numbers):")
    team_abbrs = ['PHI', 'LAL', 'BOS', 'MIA', 'SAS', 'DAL', 'CLE', 'MIL', 'GSW', 'DEN', 'PHX', 'LAC', 'MEM', 'MIN', 'NOP', 'OKC', 'POR', 'SAC', 'UTA', 'HOU', 'SAN', 'TOR', 'CHI', 'DET', 'IND', 'ATL', 'CHA', 'ORL', 'WAS', 'NYK', 'BRK', 'BKN']
    
    for off, s in strings:
        has_team = any(t in s for t in team_abbrs)
        has_digit = any(c.isdigit() for c in s)
        if has_team and has_digit and len(s) > 3:
            print(f"  [{off:06X}] {s}")

if __name__ == "__main__":
    main()
