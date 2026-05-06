"""Find playbook data now that plays are being displayed in roster editor."""

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
    
    team_base = 0x2A82B17D0
    
    print("="*80)
    print("STEP 1: Search for play-like strings now that plays are displayed")
    print("="*80)
    
    # Search for common play name patterns
    # Play names typically contain: team abbreviations, numbers, play types
    patterns = [
        # Team abbreviations followed by space and number
        b'P\x00H\x00I\x00',  # PHI
        b'L\x00A\x00L\x00',  # LAL
        b'B\x00O\x00S\x00',  # BOS
        b'M\x00I\x00A\x00',  # MIA
        b'S\x00A\x00S\x00',  # SAS
        b'D\x00A\x00L\x00',  # DAL
        b'C\x00L\x00E\x00',  # CLE
        b'M\x00I\x00L\x00',  # MIL
        # Play types
        b'1\x005\x00',  # 15 (common play number)
        b'2\x001\x00',  # 21
        b'3\x004\x00',  # 34
        b'4\x001\x00',  # 41
        b'5\x001\x00',  # 51
        b'5\x003\x00',  # 53
    ]
    
    for pattern in patterns:
        display = pattern.decode('utf-16-le', errors='ignore').replace('\x00', '')
        print(f"\nSearching for '{display}'...")
        
        mbr = MBI()
        addr = 0
        hits = []
        
        while True:
            result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
            if result == 0:
                break
            
            if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
                buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
                if buf:
                    idx = buf.find(pattern)
                    while idx >= 0:
                        loc = mbr.BaseAddress + idx
                        # Get context
                        context = read_memory(h, loc - 10, 50)
                        if context:
                            text = context.decode('utf-16-le', errors='ignore')
                            # Check if this looks like a play name
                            if any(c.isdigit() for c in text) and len(text) > 5:
                                hits.append((loc, text))
                        idx = buf.find(pattern, idx + 2)
            
            addr = mbr.BaseAddress + mbr.RegionSize
        
        print(f"  Found {len(hits)} hits")
        if hits:
            # Group by region
            regions = {}
            for loc, text in hits:
                region = loc & ~0xFFFF
                if region not in regions:
                    regions[region] = []
                regions[region].append((loc, text))
            
            print(f"  In {len(regions)} regions")
            
            # Show top regions
            for region, region_hits in sorted(regions.items(), key=lambda x: -len(x[1]))[:3]:
                print(f"    Region 0x{region:X} ({len(region_hits)} hits):")
                for loc, text in region_hits[:5]:
                    print(f"      0x{loc:X}: '{text[:40]}'")
    
    print("\n" + "="*80)
    print("STEP 2: Look for playbook array near team structure")
    print("="*80)
    
    # The playbook array might be referenced from the team structure
    # Let's look at offsets that might contain playbook pointers
    
    # Known playbook-related offsets from previous research
    pb_candidate_offsets = [
        0x338, 0x340, 0x348, 0x350, 0x358, 0x360,  # Playbook count fields
        0x3C0, 0x3C8, 0x3D0, 0x3D8, 0x3E0, 0x3E8,  # Potential playbook pointers
        0x400, 0x408, 0x410, 0x418, 0x420, 0x428,  # More potential pointers
        0x500, 0x508, 0x510, 0x518, 0x520, 0x528,  # Even more
        0x600, 0x608, 0x610, 0x618, 0x620, 0x628,  # And more
        0x700, 0x708, 0x710, 0x718, 0x720, 0x728,  # Keep going
        0x800, 0x808, 0x810, 0x818, 0x820, 0x828,  # More
        0x900, 0x908, 0x910, 0x918, 0x920, 0x928,  # More
        0xA00, 0xA08, 0xA10, 0xA18, 0xA20, 0xA28,  # More
        0xB00, 0xB08, 0xB10, 0xB18, 0xB20, 0xB28,  # More
        0xC00, 0xC08, 0xC10, 0xC18, 0xC20, 0xC28,  # More
        0xD00, 0xD08, 0xD10, 0xD18, 0xD20, 0xD28,  # More
        0xE00, 0xE08, 0xE10, 0xE18, 0xE20, 0xE28,  # More
    ]
    
    team_data = read_memory(h, team_base, 0xE30)
    if not team_data:
        print("Failed to read team structure!")
        return
    
    print("\nChecking potential playbook pointer offsets:")
    for off in pb_candidate_offsets:
        if off + 8 <= len(team_data):
            val = struct.unpack_from('<Q', team_data, off)[0]
            if 0x10000000 < val < 0x300000000:
                # Check if this points to an array of offsets
                ptr_data = read_memory(h, val, 100)
                if ptr_data:
                    # Check for array of 4-byte values in play offset range
                    offsets = []
                    for i in range(0, 60, 4):  # Check 15 entries
                        if i + 4 <= len(ptr_data):
                            v = struct.unpack_from('<I', ptr_data, i)[0]
                            if 0x50 < v < 0x5000:
                                offsets.append(v)
                    
                    if len(offsets) >= 5:
                        print(f"  [{off:04X}] 0x{val:X} -> OFFSETS: {offsets[:10]}")

if __name__ == "__main__":
    main()
