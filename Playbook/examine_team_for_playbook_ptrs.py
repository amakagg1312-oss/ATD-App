"""Examine team structures for playbook pointers."""

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
    
    # Known team base from previous discovery
    team_base = 0x2A82B17D0
    team_stride = 5672
    
    print(f"Team Base: 0x{team_base:X}")
    print(f"Team Stride: {team_stride}")
    
    # Known play offsets from all_play_names.txt (we'll use a few)
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
    ]
    
    # Convert to 4-byte little-endian bytes
    known_offsets_bytes = [struct.pack('<I', off) for off in known_offsets]
    
    print("\nExamining team structures for playbook pointers...")
    print(f"Checking first 30 teams")
    
    max_teams = 30
    
    for i in range(max_teams):
        team_addr = team_base + i * team_stride
        team_data = read_memory(h, team_addr, team_stride)
        if not team_data:
            print(f"  Team {i}: Failed to read memory at 0x{team_addr:X}")
            continue
        
        # Look for 8-byte pointers (64-bit) in the team data
        for j in range(0, team_stride - 7, 8):  # Step by 8 for 8-byte values
            ptr_bytes = team_data[j:j+8]
            if len(ptr_bytes) < 8:
                continue
            ptr = struct.unpack('<Q', ptr_bytes)[0]
            
            # Check if ptr looks like a valid pointer (in user space range)
            if ptr < 0x100000000 or ptr > 0x7FFFFFFFFFFF:
                continue
            
            # Now, read a small block from this pointer to see if it contains known offsets
            # We'll read 0x1000 bytes
            block = read_memory(h, ptr, 0x1000)
            if not block:
                continue
            
            # Check if any of the known offsets appear as 4-byte little-endian values in this block
            found_known = False
            for off in known_offsets_bytes:
                if off in block:
                    found_known = True
                    break
            
            if found_known:
                print(f"\n*** Found candidate at team {i} ***")
                print(f"  Team address: 0x{team_addr:X}")
                print(f"  Pointer offset in team: 0x{j:X}")
                print(f"  Pointer value: 0x{ptr:X}")
                print(f"  -> Points to memory containing known play offset")
                
                # Let's look at a bit more context around the pointer in the team
                ctx_start = max(0, j - 16)
                ctx_end = min(team_stride, j + 24)
                ctx = team_data[ctx_start:ctx_end]
                print(f"  Context around pointer: {ctx.hex()}")
                
                # Try to see if there's a pattern - maybe multiple pointers in a row
                # Check if there are more pointers nearby
                nearby_ptrs = []
                for k in range(max(0, j-32), min(team_stride-7, j+32), 8):
                    if k == j:
                        continue
                    k_ptr_bytes = team_data[k:k+8]
                    if len(k_ptr_bytes) < 8:
                        continue
                    k_ptr = struct.unpack('<Q', k_ptr_bytes)[0]
                    if 0x100000000 <= k_ptr <= 0x7FFFFFFFFFFF:
                        nearby_ptrs.append((k, k_ptr))
                
                if nearby_ptrs:
                    print(f"  Nearby pointers: {nearby_ptrs[:5]}")
                
                # Let's also check if this pointer points to one of our candidate regions
                # from previous runs: 0x2BEFF9000, 0x2D5E50000, 0x2E1850000, 0x7FFCC01F1000, 0x7FFD9ECDB000
                candidate_regions = [
                    0x2BEFF9000,
                    0x2D5E50000,
                    0x2E1850000,
                    0x7FFCC01F1000,
                    0x7FFD9ECDB000
                ]
                
                for cand in candidate_regions:
                    if ptr == cand:
                        print(f"  -> Points to known candidate region: 0x{ptr:X}")
                        break
        
        # Also, let's try to decode the team name (should be at a known offset)
        # From previous work, team name might be at offset 0x20 or similar
        if i < 5:  # Just show first few team names
            name_offset = 0x20  # guess
            if name_offset + 64 <= len(team_data):
                name_bytes = team_data[name_offset:name_offset+64]
                # Try to decode as UTF-16LE
                try:
                    name = name_bytes.decode('utf-16le').rstrip('\x00')
                    if name and all(ord(c) < 128 for c in name):  # ASCII only
                        print(f"  Team {i} name (offset 0x{name_offset:X}): {name}")
                except:
                    pass
    
    print("\nDone.")

if __name__ == "__main__":
    main()
