"""Find playbook string block and team playbook arrays dynamically."""

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

def encode_wstring(s):
    return (s + "\x00").encode('utf-16-le')

def decode_wstring(data, max_chars=50):
    try:
        raw = data[:max_chars*2]
        return raw.decode('utf-16-le', errors='ignore').split('\x00')[0].strip()
    except:
        return ""

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
    
    # Known play names from previous research
    known_plays = [
        "FIST 64 STS",
        "CLE FIST 15 DRA",
        "FIST 21 IVERSON",
        "FIST CHEST FLAR",
        "SAS FIST 15 FLAT OU",
        "MIL FIST 34 DOWN SLI",
        "PUNCH 5 WEA",
        "PUNCH 3 DOW",
        "HORNS 12",
        "HORNS 21",
        "FLEX 45",
        "TRIANGLE",
        "PRINCETON",
        "MOTION 4 OUT",
        "ISO",
        "PICK AND ROLL",
    ]
    
    print("="*80)
    print("STEP 1: Finding play string block")
    print("="*80)
    
    # Search for known play names to locate the string block
    string_block_candidates = {}
    
    for play_name in known_plays[:6]:  # Start with first 6
        play_bytes = encode_wstring(play_name)
        print(f"\nSearching for '{play_name}'...")
        
        mbr = MBI()
        addr = 0
        regions = 0
        
        while True:
            result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
            if result == 0:
                break
            
            if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
                # Only search regions that could contain strings (readable, not executable)
                if mbr.Protect in (0x02, 0x04, 0x20, 0x40, 0x80):  # PAGE_READONLY, PAGE_READWRITE, etc.
                    buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
                    if buf:
                        idx = buf.find(play_bytes)
                        if idx >= 0:
                            loc = mbr.BaseAddress + idx
                            # Round down to find start of string block region
                            region_start = loc & ~0xFFFF
                            string_block_candidates[region_start] = string_block_candidates.get(region_start, 0) + 1
            
            regions += 1
            if regions % 5000 == 0:
                print(f"  Scanned {regions} regions...")
            
            addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nFound {len(string_block_candidates)} candidate regions for string block:")
    for region, count in sorted(string_block_candidates.items(), key=lambda x: -x[1])[:10]:
        print(f"  0x{region:X} (matched {count} play names)")
    
    if not string_block_candidates:
        print("\nNo string block found! Trying broader search...")
        # Try searching for just "FIST" which should be common
        fist_bytes = encode_wstring("FIST")
        fist_hits = []
        
        mbr = MBI()
        addr = 0
        regions = 0
        
        while True:
            result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
            if result == 0:
                break
            
            if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
                if mbr.Protect in (0x02, 0x04, 0x20, 0x40, 0x80):
                    buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
                    if buf:
                        idx = buf.find(fist_bytes)
                        while idx >= 0:
                            loc = mbr.BaseAddress + idx
                            fist_hits.append(loc)
                            idx = buf.find(fist_bytes, idx + 2)
            
            regions += 1
            if regions % 5000 == 0:
                print(f"  Scanned {regions} regions, found {len(fist_hits)} hits...")
            
            addr = mbr.BaseAddress + mbr.RegionSize
        
        print(f"\nFound {len(fist_hits)} 'FIST' occurrences")
        if fist_hits:
            # Group by region
            regions_dict = {}
            for loc in fist_hits[:100]:
                region = loc & ~0xFFFF
                regions_dict[region] = regions_dict.get(region, 0) + 1
            
            print("Top regions with 'FIST':")
            for region, count in sorted(regions_dict.items(), key=lambda x: -x[1])[:10]:
                print(f"  0x{region:X} ({count} hits)")
    
    print("\n" + "="*80)
    print("STEP 2: Analyzing string block candidates")
    print("="*80)
    
    # For each candidate, try to extract play names
    for candidate in sorted(string_block_candidates.keys(), key=lambda x: -string_block_candidates[x])[:5]:
        print(f"\nAnalyzing region 0x{candidate:X}...")
        
        # Read a large chunk
        data = read_memory(h, candidate, 0x10000)
        if not data:
            continue
        
        # Extract UTF-16LE strings
        plays_found = []
        i = 0
        while i < len(data) - 2:
            # Find null terminator
            null_pos = data.find(b'\x00\x00', i)
            if null_pos == -1:
                break
            
            # Find start of string (previous null + 2, aligned)
            start = null_pos + 2
            if start % 2 != 0:
                start += 1
            
            # Find next null
            next_null = data.find(b'\x00\x00', start)
            if next_null == -1:
                next_null = len(data)
            
            play_bytes = data[start:next_null]
            if len(play_bytes) >= 6:  # At least 3 characters
                try:
                    play_name = play_bytes.decode('utf-16-le', errors='replace').strip()
                    if play_name and len(play_name) > 2 and any(c.isalpha() for c in play_name):
                        plays_found.append((start, play_name))
                except:
                    pass
            
            i = null_pos + 2
        
        print(f"  Found {len(plays_found)} play-like strings")
        if plays_found:
            print(f"  First 10 plays:")
            for offset, name in plays_found[:10]:
                print(f"    [{offset:06X}] {name}")
            
            # Check if known plays are in this list
            known_in_region = []
            for _, name in plays_found:
                for known in known_plays:
                    if known in name or name in known:
                        known_in_region.append(name)
                        break
            
            if known_in_region:
                print(f"  MATCH: Found {len(known_in_region)} known play names!")
                print(f"  Examples: {known_in_region[:5]}")

if __name__ == "__main__":
    main()
