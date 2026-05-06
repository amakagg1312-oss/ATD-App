"""Search for playbook data using multiple strategies."""

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
    
    print(f"PID: {pid}")
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    print("="*80)
    print("STRATEGY 1: Search for short ASCII strings (UTF-16LE)")
    print("="*80)
    
    # Try shorter patterns that are more likely to exist
    short_patterns = [
        b'F\x00I\x00S\x00T\x00',
        b'H\x00O\x00R\x00N\x00S\x00',
        b'I\x00S\x00O\x00',
        b'P\x00I\x00C\x00K\x00',
        b'Z\x00O\x00N\x00E\x00',
        b'F\x00L\x00E\x00X\x00',
    ]
    
    for pattern in short_patterns:
        display = pattern.decode('utf-16-le', errors='ignore').replace('\x00', '')
        print(f"\nSearching for '{display}'...")
        
        mbr = MBI()
        addr = 0
        hits = []
        
        while True:
            result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
            if result == 0:
                break
            
            if mbr.State == 0x1000 and mbr.RegionSize > 0:
                # Skip very large regions
                if mbr.RegionSize < 0x10000000:
                    buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
                    if buf:
                        idx = buf.find(pattern)
                        if idx >= 0:
                            loc = mbr.BaseAddress + idx
                            hits.append(loc)
            
            addr = mbr.BaseAddress + mbr.RegionSize
        
        print(f"  Found {len(hits)} hits")
        if hits:
            for loc in hits[:5]:
                print(f"    0x{loc:X}")
                # Show context
                data = read_memory(h, loc - 10, 60)
                if data:
                    for off in range(0, min(len(data), 50), 16):
                        chunk = data[off:off+16]
                        hex_str = ' '.join(f'{b:02X}' for b in chunk)
                        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                        print(f"      [{off:03X}] {hex_str:<48} {ascii_str}")
    
    print("\n" + "="*80)
    print("STRATEGY 2: Search near known team/staff addresses")
    print("="*80)
    
    # Known addresses from previous research
    known_addresses = [
        (0x2A84DD940, "Staff Table"),
        (0x2A82B17D0, "Team Table (76ers)"),
        (0x29B255038, "Team Name (76ers)"),
    ]
    
    for base_addr, label in known_addresses:
        print(f"\nSearching near {label} @ 0x{base_addr:X}...")
        
        # Search +/- 10MB
        search_start = base_addr - 0xA00000
        search_end = base_addr + 0xA00000
        
        # Look for playbook-like structures (arrays of 4-byte offsets)
        for region_start in range(search_start, search_end, 0x10000):
            data = read_memory(h, region_start, 0x10000)
            if not data:
                continue
            
            # Look for sequences of values that could be play offsets
            # Play offsets would typically be in range 0x100-0x10000
            for i in range(0, len(data) - 240, 48):  # Playbook stride is 48 bytes
                # Check if first 4 bytes look like an offset
                val = struct.unpack_from('<I', data, i)[0]
                if 0x100 < val < 0x10000:
                    # Check next few entries
                    offsets = []
                    valid = True
                    for j in range(0, 48, 48):  # Check first entry of each potential playbook
                        if i + j + 4 <= len(data):
                            v = struct.unpack_from('<I', data, i + j)[0]
                            if 0x100 < v < 0x10000:
                                offsets.append(v)
                            else:
                                valid = False
                                break
                    
                    if valid and len(offsets) >= 3:
                        print(f"  Potential playbook at 0x{region_start + i:X}: {offsets[:5]}")
    
    print("\n" + "="*80)
    print("STRATEGY 3: Search for UTF-16LE strings in all readable regions")
    print("="*80)
    
    # Extract all readable strings and look for play-like patterns
    mbr = MBI()
    addr = 0
    regions = 0
    string_regions = []
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            if mbr.Protect in (0x02, 0x04, 0x20, 0x40, 0x80):
                buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x10000))
                if buf:
                    # Check for UTF-16LE null terminators
                    null_count = buf.count(b'\x00\x00')
                    if null_count > 50:  # Region with many strings
                        string_regions.append((mbr.BaseAddress, mbr.RegionSize, null_count))
        
        regions += 1
        if regions % 5000 == 0:
            print(f"  Scanned {regions} regions, found {len(string_regions)} string-rich regions...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nFound {len(string_regions)} string-rich regions")
    
    # Analyze top string regions
    for base, size, nulls in sorted(string_regions, key=lambda x: -x[2])[:10]:
        print(f"\nRegion 0x{base:X} (size: 0x{size:X}, nulls: {nulls})")
        
        data = read_memory(h, base, min(size, 0x10000))
        if data:
            # Extract strings
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
                if len(s_bytes) >= 4:
                    try:
                        s = s_bytes.decode('utf-16-le', errors='replace').strip()
                        if s and len(s) > 2:
                            strings.append((start, s))
                    except:
                        pass
                
                i = null_pos + 2
            
            # Look for play-like strings
            play_strings = [(off, s) for off, s in strings if any(c.isupper() for c in s) and len(s) > 3]
            print(f"  Found {len(strings)} strings, {len(play_strings)} play-like")
            
            if play_strings:
                print(f"  First 10 play-like strings:")
                for off, s in play_strings[:10]:
                    print(f"    [{off:06X}] {s}")

if __name__ == "__main__":
    main()
