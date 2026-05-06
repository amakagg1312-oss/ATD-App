"""Find playbook data while roster editor is open."""

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
    
    # Known team addresses from previous research
    team_name_addr = 0x29B255038  # "76ers"
    team_base_addr = 0x2A82B17D0  # 76ers team base
    team_stride = 5672
    name_offset = 0x2E2
    
    print("="*80)
    print("STEP 1: Verify team addresses")
    print("="*80)
    
    # Check if team name is still at known address
    name_data = read_memory(h, team_name_addr, 40)
    if name_data:
        team_name = decode_wstring(name_data, 20)
        print(f"Team name @ 0x{team_name_addr:X}: '{team_name}'")
    else:
        print(f"Team name @ 0x{team_name_addr:X} not readable")
    
    # Check team base
    team_data = read_memory(h, team_base_addr, 64)
    if team_data:
        print(f"Team base @ 0x{team_base_addr:X} is readable")
        # Show first few values
        for i in range(0, 64, 8):
            val = struct.unpack_from('<Q', team_data, i)[0]
            print(f"  [{i:03X}] = 0x{val:X}")
    else:
        print(f"Team base @ 0x{team_base_addr:X} not readable")
    
    print("\n" + "="*80)
    print("STEP 2: Search for playbook near team structure")
    print("="*80)
    
    # Search +/- 50MB from team base for playbook-like structures
    search_start = team_base_addr - 0x3200000
    search_end = team_base_addr + 0x3200000
    
    print(f"Searching region 0x{search_start:X} to 0x{search_end:X}...")
    
    # Look for arrays of 4-byte values that could be play offsets
    # Play offsets from known data range from ~88 to ~3267
    # But after update, they might be different
    
    # First, let's look for the play string block by searching for UTF-16LE strings
    # that look like play names (uppercase letters, numbers, spaces)
    
    print("\nSearching for play-like strings...")
    
    mbr = MBI()
    addr = search_start
    string_regions = []
    
    while addr < search_end:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0:
            if mbr.Protect in (0x02, 0x04, 0x20, 0x40, 0x80):
                # Read region in chunks
                for chunk_start in range(0, min(mbr.RegionSize, 0x1000000), 0x10000):
                    chunk_size = min(0x10000, mbr.RegionSize - chunk_start)
                    buf = read_memory(h, mbr.BaseAddress + chunk_start, chunk_size)
                    if buf:
                        # Count UTF-16LE null terminators
                        null_count = buf.count(b'\x00\x00')
                        if null_count > 100:
                            string_regions.append((mbr.BaseAddress + chunk_start, chunk_size, null_count))
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"Found {len(string_regions)} string-rich regions")
    
    # Analyze top string regions for play-like strings
    for base, size, nulls in sorted(string_regions, key=lambda x: -x[2])[:20]:
        print(f"\nAnalyzing region 0x{base:X} (nulls: {nulls})...")
        
        data = read_memory(h, base, min(size, 0x10000))
        if not data:
            continue
        
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
            if len(s_bytes) >= 6:
                try:
                    s = s_bytes.decode('utf-16-le', errors='replace').strip()
                    # Check if string looks like a play name
                    if s and len(s) > 3:
                        # Play names typically have uppercase letters and numbers
                        has_upper = any(c.isupper() for c in s)
                        has_digit = any(c.isdigit() for c in s)
                        if has_upper and len(s) < 40:
                            strings.append((start, s, has_digit))
                except:
                    pass
            
            i = null_pos + 2
        
        # Show play-like strings
        play_strings = [(off, s, has_digit) for off, s, has_digit in strings if has_digit]
        print(f"  Found {len(strings)} strings, {len(play_strings)} play-like (with digits)")
        
        if play_strings:
            print(f"  First 15 play-like strings:")
            for off, s, has_digit in play_strings[:15]:
                print(f"    [{off:06X}] {s}")
            
            # Check if this region has enough play-like strings to be the string block
            if len(play_strings) > 50:
                print(f"  *** POTENTIAL PLAY STRING BLOCK! ***")
                
                # Try to find playbook arrays that point to this region
                print(f"\n  Searching for playbook arrays pointing to this region...")
                
                # Look for arrays of 4-byte offsets in the range of this string block
                for region_base, region_size, _ in string_regions[:50]:
                    region_data = read_memory(h, region_base, min(region_size, 0x100000))
                    if not region_data:
                        continue
                    
                    for i in range(0, len(region_data) - 240, 48):
                        # Check if first 4 bytes look like an offset into string block
                        val = struct.unpack_from('<I', region_data, i)[0]
                        if base <= base + val < base + size:
                            # Check next few entries
                            offsets = []
                            valid = True
                            for j in range(0, 96, 48):
                                if i + j + 4 <= len(region_data):
                                    v = struct.unpack_from('<I', region_data, i + j)[0]
                                    if base <= base + v < base + size:
                                        offsets.append(v)
                                    else:
                                        valid = False
                                        break
                            
                            if valid and len(offsets) >= 2:
                                print(f"    Playbook candidate at 0x{region_base + i:X}")
                                # Read play names
                                for k, off in enumerate(offsets[:5]):
                                    play_addr = base + off
                                    play_data = read_memory(h, play_addr, 40)
                                    if play_data:
                                        play_name = decode_wstring(play_data, 20)
                                        print(f"      [{k}] offset {off}: '{play_name}'")

if __name__ == "__main__":
    main()
