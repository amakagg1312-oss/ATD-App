"""Examine the memory that team pointers point to, looking for playbook data."""

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
    
    # Read first team structure
    team_data = read_memory(h, team_base, team_stride)
    if not team_data:
        print("Failed to read team data!")
        return
    
    # We saw that pointers are spaced by 0x498 bytes and point to player data
    # Let's look at a different offset in the team structure - maybe playbook pointer is elsewhere
    
    print("\nExamining team structure for potential playbook pointers at different offsets:")
    
    # Look at offsets that are multiples of 8 (potential 64-bit pointers)
    # but let's skip the first bunch that we know are player pointers
    # Let's check offsets 0x200-0x400 for example
    
    start_offset = 0x200
    end_offset = 0x400
    
    print(f"Checking offsets 0x{start_offset:X} to 0x{end_offset:X}")
    
    potential_ptrs = []
    for offset in range(start_offset, end_offset, 8):
        if offset + 8 <= len(team_data):
            ptr_val = struct.unpack('<Q', team_data[offset:offset+8])[0]
            # Check if it's a valid user-mode pointer
            if 0x100000000 <= ptr_val <= 0x7FFFFFFFFFFF:
                potential_ptrs.append((offset, ptr_val))
    
    print(f"Found {len(potential_ptrs)} potential pointers in this range")
    
    # Examine the first few
    for offset, ptr_val in potential_ptrs[:10]:
        print(f"\nPointer at team offset 0x{offset:04X}: 0x{ptr_val:016X}")
        
        # Read a block at this pointer
        block = read_memory(h, ptr_val, 0x2000)  # 8KB
        if block:
            # Look for known play offsets
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
                0x3E018E,  # QUICK ELBOW 1
                0x3E01AA,  # QUICK ELBOW 2
                0x3E01CA,  # QUICK ELBOW 3
                0x3E016E,  # GIVE ELBOW 1
                0x3E014E,  # GIVE ELBOW 2
            ]
            
            found_offsets = []
            for i in range(0, len(block) - 3, 4):
                val = struct.unpack('<I', block[i:i+4])[0]
                if val in known_offsets:
                    found_offsets.append((i, val))
            
            if found_offsets:
                print(f"  *** FOUND {len(found_offsets)} KNOWN PLAY OFFSETS ***")
                for block_offset, val in found_offsets[:5]:
                    abs_addr = ptr_val + block_offset
                    print(f"    Block offset 0x{block_offset:04X} (0x{abs_addr:016X}): 0x{val:08X}")
                
                # This looks promising! Let's examine this region more
                print(f"\n  Examining the region around 0x{ptr_val:016X}:")
                
                # Let's see if there's a pattern or structure
                # Look for arrays or sequences
                
                # Check if this looks like an array of offsets
                offset_array = []
                for i in range(0, min(len(block), 0x1000), 4):  # First 1KB as dwords
                    val = struct.unpack('<I', block[i:i+4])[0]
                    if val < 0x100000:  # Reasonable offset size
                        offset_array.append(val)
                
                if len(offset_array) >= 10:
                    print(f"    Found {len(offset_array)} potential offset values in first 1KB")
                    # Show first 20
                    print(f"    First 20 offsets: {offset_array[:20]}")
                    
                    # Check if they're sequential or have a pattern
                    if len(offset_array) >= 5:
                        # Check if they're increasing
                        increasing = all(offset_array[i] <= offset_array[i+1] for i in range(len(offset_array)-1))
                        if increasing:
                            print(f"    Offsets are monotonically increasing")
                            
                            # Check gaps
                            gaps = [offset_array[i+1] - offset_array[i] for i in range(len(offset_array)-1)]
                            if gaps:
                                avg_gap = sum(gaps) / len(gaps)
                                print(f"    Average gap between offsets: {avg_gap:.1f} bytes")
                                
                                # If gaps are consistent, this might be an array
                                if len(set(gaps)) <= 5:  # Not too many different gap sizes
                                    print(f"    Gap values: {sorted(set(gaps))[:10]}")
            else:
                # No known offsets found, but let's see if there's any interesting data
                # Look for strings
                ascii_strings = []
                current = []
                for i, b in enumerate(block[:500]):  # First 500 bytes
                    if 32 <= b <= 126:  # Printable ASCII
                        current.append(chr(b))
                    else:
                        if len(current) >= 4:
                            ascii_strings.append(''.join(current))
                        current = []
                if len(current) >= 4:
                    ascii_strings.append(''.join(current))
                
                if ascii_strings:
                    # Filter for interesting strings
                    interesting = [s for s in ascii_strings if any(keyword in s.upper() for keyword in 
                                                                  ['PLAY', 'FIST', 'STAG', 'FLARE', 'RIP', 'ELBOW', 'TRI', 'QUICK'])]
                    if interesting:
                        print(f"  Interesting strings found: {interesting[:5]}")
    
    # Also, let's check if there's a specific offset in the team structure that we haven't looked at
    # Based on the pattern we saw earlier, maybe the playbook pointer is at a specific offset
    
    print("\n" + "="*60)
    print("Checking specific offsets in team structure that might contain playbook pointers:")
    
    # Let's check offsets that are round numbers or based on the stride
    # Team stride is 5672 = 0x1628
    # Maybe playbook pointer is at offset 0x1500 or 0x1600 or something
    
    check_offsets = [0x1500, 0x1550, 0x1600, 0x1620, 0x1628, 0x1650, 0x1700]
    
    for offset in check_offsets:
        if offset + 8 <= len(team_data):
            ptr_val = struct.unpack('<Q', team_data[offset:offset+8])[0]
            if 0x100000000 <= ptr_val <= 0x7FFFFFFFFFFF:
                print(f"Team offset 0x{offset:04X}: 0x{ptr_val:016X}")
                
                # Quick check for known offsets in what this points to
                block = read_memory(h, ptr_val, 0x1000)
                if block:
                    known_offsets = [0x3E02CE, 0x3E02EA, 0x3E030A, 0x3E022E, 0x3E024A, 0x3E0266]
                    found = False
                    for i in range(0, min(len(block), 0x1000)-3, 4):
                        val = struct.unpack('<I', block[i:i+4])[0]
                        if val in known_offsets:
                            found = True
                            break
                    if found:
                        print(f"  *** CONTAINS KNOWN PLAY OFFSETS! ***")

if __name__ == "__main__":
    main()
