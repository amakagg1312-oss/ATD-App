"""Search for exact play names from user's current playbook."""

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
    
    # Distinctive play name fragments to search for
    search_terms = [
        "FIST DELAY",
        "FIST STAGGER",
        "QUICK FLARE",
        "PUNCH RIP",
        "QUICK ELBOW",
        "GIVE ELBOW",
        "PUNCH TRI",
    ]
    
    print("="*80)
    print("Searching for exact play names in memory")
    print("="*80)
    
    all_hits = {}
    
    for term in search_terms:
        print(f"\nSearching for '{term}'...")
        term_bytes = encode_wstring(term)
        
        mbr = MBI()
        addr = 0
        hits = []
        regions_checked = 0
        
        while True:
            result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
            if result == 0:
                break
            
            if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
                buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
                if buf:
                    idx = buf.find(term_bytes)
                    while idx >= 0:
                        loc = mbr.BaseAddress + idx
                        # Get full string context
                        context = read_memory(h, loc - 20, 80)
                        if context:
                            full_text = decode_wstring(context, 40)
                            hits.append((loc, full_text))
                        idx = buf.find(term_bytes, idx + 2)
            
            regions_checked += 1
            if regions_checked % 3000 == 0:
                print(f"  Checked {regions_checked} regions...")
            
            addr = mbr.BaseAddress + mbr.RegionSize
        
        print(f"  Found {len(hits)} hits")
        if hits:
            for loc, text in hits[:5]:
                print(f"    0x{loc:X}: '{text}'")
                all_hits[loc] = text
    
    # Analyze hits to find string block
    if all_hits:
        print("\n" + "="*80)
        print("Analyzing hit locations")
        print("="*80)
        
        # Group by region
        regions = {}
        for loc, text in all_hits.items():
            region = loc & ~0xFFFF
            if region not in regions:
                regions[region] = []
            regions[region].append((loc, text))
        
        print(f"\nHits found in {len(regions)} regions:")
        for region, hits in sorted(regions.items(), key=lambda x: -len(x[1])):
            print(f"\n  Region 0x{region:X} ({len(hits)} hits):")
            for loc, text in hits[:10]:
                print(f"    0x{loc:X}: '{text}'")
            
            # If this region has multiple hits, it might be the string block
            if len(hits) >= 3:
                print(f"\n  *** POTENTIAL STRING BLOCK! Extracting nearby strings... ***")
                
                # Read large chunk and extract all strings
                data = read_memory(h, region, 0x10000)
                if data:
                    strings = []
                    i = 0
                    while i < len(data) - 2:
                        null_pos = data.find(b'\x00\x00', i)
                        if null_pos == -1:
                            break
                        
                        start = null_pos + 2
                        if start % 2 != 0:
                            start += 1
                        
                        next_null = data.find(b'\x00\x00', start)
                        if next_null == -1:
                            next_null = len(data)
                        
                        s_bytes = data[start:next_null]
                        if len(s_bytes) >= 6:
                            try:
                                s = s_bytes.decode('utf-16-le', errors='replace').strip()
                                if s and len(s) > 3:
                                    has_upper = any(c.isupper() for c in s)
                                    has_digit = any(c.isdigit() for c in s)
                                    if has_upper and has_digit:
                                        strings.append((start, s))
                            except:
                                pass
                        
                        i = null_pos + 2
                    
                    print(f"  Found {len(strings)} play-like strings in region")
                    for off, s in strings[:30]:
                        print(f"    [{off:06X}] {s}")

if __name__ == "__main__":
    main()
