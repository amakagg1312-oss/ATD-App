"""Examine what the pointers in team structure point to."""

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
    
    # Extract the first few pointers
    print("\nExamining first 10 pointers from team structure:")
    pointers = []
    for i in range(0, min(80, len(team_data)), 8):  # First 10 pointers
        ptr_val = struct.unpack('<Q', team_data[i:i+8])[0]
        if 0x100000000 <= ptr_val <= 0x7FFFFFFFFFFF:
            pointers.append((i, ptr_val))
            print(f"  Offset 0x{i:04X}: 0x{ptr_val:016X}")
    
    # Now examine what each pointer points to
    print("\nExamining what these pointers point to:")
    for offset, ptr_val in pointers[:5]:  # Check first 5 pointers
        print(f"\nPointer at team offset 0x{offset:04X} points to 0x{ptr_val:016X}:")
        
        # Read a block of memory at this pointer
        block_size = 0x200  # 512 bytes
        block = read_memory(h, ptr_val, block_size)
        if not block:
            print("  Failed to read memory at pointer address")
            continue
        
        # Look for known play offsets in this block
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
        
        found_offsets = []
        for i in range(0, len(block) - 3, 4):
            val = struct.unpack('<I', block[i:i+4])[0]
            if val in known_offsets:
                found_offsets.append((i, val))
        
        if found_offsets:
            print(f"  Found {len(found_offsets)} known play offsets in this block:")
            for block_offset, val in found_offsets[:10]:  # Show first 10
                abs_addr = ptr_val + block_offset
                print(f"    Block offset 0x{block_offset:04X} (0x{abs_addr:016X}): 0x{val:08X}")
        else:
            print("  No known play offsets found in this block")
            
        # Also look for strings or patterns
        # Try to see if there's any readable text
        ascii_text = []
        current = []
        for i, b in enumerate(block[:100]):  # First 100 bytes
            if 32 <= b <= 126:  # Printable ASCII
                current.append(chr(b))
            else:
                if len(current) >= 4:
                    ascii_text.append(''.join(current))
                current = []
        if len(current) >= 4:
            ascii_text.append(''.join(current))
        
        if ascii_text:
            print(f"  ASCII strings found: {ascii_text[:5]}")
        
        # Look for the pattern of consecutive 4-byte values that might be offsets
        # Let's see if there are sequential values that increase by small amounts
        dword_vals = []
        for i in range(0, min(len(block), 0x100), 4):  # First 64 dwords
            val = struct.unpack('<I', block[i:i+4])[0]
            dword_vals.append(val)
        
        # Look for sequences
        sequences = []
        for i in range(len(dword_vals)-1):
            if dword_vals[i+1] > dword_vals[i]:  # Increasing
                seq_start = i
                while i+1 < len(dword_vals) and dword_vals[i+1] > dword_vals[i]:
                    i += 1
                if i - seq_start >= 3:  # At least 3 increasing values
                    sequences.append((seq_start, i, dword_vals[seq_start:i+1]))
        
        if sequences:
            print(f"  Found {len(sequences)} increasing sequences in dword values:")
            for start, end, vals in sequences[:3]:  # Show first 3
                print(f"    Offsets 0x{start*4:02X}-0x{end*4:02X}: {vals[:5]}{'...' if len(vals) > 5 else ''}")

if __name__ == "__main__":
    main()
