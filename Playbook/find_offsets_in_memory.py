"""Search for known play offsets (from all_play_names.txt) as 4-byte little-endian values in memory."""

import sys
import io
import struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil

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
    
    # Known offsets from all_play_names.txt (first 20 for testing)
    known_offsets = [
        0x3E02CE,  # FIST DELAY 2
        0x3E02EA,  # FIST DELAY 3
        0x3E030A,  # FIST DELAY 4
        0x3E022E,  # FIST STAGGER 1
        0x3E024A,  # FIST STAGGER 2
        0x3E0266,  # FIST STAGGER 3
        0x3E0286,  # FIST STAGGER 4
        0x3E01CE,  # QUICK FLARE 1
        0x3E01EA,  # QUICK FLARE 2
        0x3E020A,  # QUICK FLARE 3
        0x3E02DA,  # PUNCH RIP 1
        0x3E02F6,  # PUNCH RIP 2
        0x3E0316,  # PUNCH RIP 3
        0x3E018E,  # QUICK ELBOW 1
        0x3E01AA,  # QUICK ELBOW 2
        0x3E01CA,  # QUICK ELBOW 3
        0x3E016E,  # GIVE ELBOW 1
        0x3E014E,  # GIVE ELBOW 2
        0x3E010E,  # PUNCH TRI 1
        0x3E012E,  # PUNCH TRI 2
    ]
    
    # Convert to 4-byte little-endian bytes
    known_offsets_bytes = [struct.pack('<I', off) for off in known_offsets]
    
    print(f"Searching for {len(known_offsets)} known play offsets as 4-byte little-endian values...")
    
    mbr = MBI()
    addr = 0
    regions_checked = 0
    candidate_regions = []  # regions that contain at least 3 of the known offsets
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x1000000:  # limit to reasonable size
            # Read the region in chunks to avoid memory issues
            chunk_size = 0x10000  # 64KB chunks
            bytes_read = 0
            while bytes_read < mbr.RegionSize:
                to_read = min(chunk_size, mbr.RegionSize - bytes_read)
                buf = read_memory(h, mbr.BaseAddress + bytes_read, to_read)
                if not buf:
                    break
                
                # Count how many of our known offsets appear in this chunk
                found_count = 0
                for off_bytes in known_offsets_bytes:
                    if off_bytes in buf:
                        found_count += 1
                
                if found_count >= 3:  # if we find at least 3, consider it a candidate
                    candidate_regions.append({
                        'base': mbr.BaseAddress + bytes_read,
                        'size': to_read,
                        'count': found_count
                    })
                    print(f"  Found region with {found_count} offsets at 0x{mbr.BaseAddress + bytes_read:X}")
                
                bytes_read += to_read
        
        regions_checked += 1
        if regions_checked % 500 == 0:
            print(f"  Checked {regions_checked} regions...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nFinished. Checked {regions_checked} regions.")
    print(f"Found {len(candidate_regions)} candidate regions (with at least 3 known offsets):")
    for i, cand in enumerate(candidate_regions[:10]):  # show top 10
        print(f"  {i+1}. Base: 0x{cand['base']:X}, Size: 0x{cand['size']:X}, Count: {cand['count']}")
    
    if candidate_regions:
        print("\nThe region with the most matches is:")
        best = max(candidate_regions, key=lambda x: x['count'])
        print(f"  Base: 0x{best['base']:X}")
        print(f"  Size: 0x{best['size']:X}")
        print(f"  Count: {best['count']} offsets found")

if __name__ == "__main__":
    main()
