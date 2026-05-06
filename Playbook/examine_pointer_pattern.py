"""Examine the memory that team pointers point to."""

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
    
    # Let's look at the first pointer more closely
    ptr1 = struct.unpack('<Q', team_data[0:8])[0]
    print(f"\nFirst pointer at offset 0x0000: 0x{ptr1:016X}")
    
    # Read a larger block at this pointer
    block = read_memory(h, ptr1, 0x1000)  # 4KB
    if block:
        print(f"Read 0x{len(block):X} bytes from 0x{ptr1:016X}")
        
        # Look for patterns
        # Let's see if there are repeated patterns or structures
        
        # Check if this looks like an array of pointers
        ptr_count = 0
        for i in range(0, min(len(block), 0x1000), 8):
            if i + 8 <= len(block):
                val = struct.unpack('<Q', block[i:i+8])[0]
                if 0x100000000 <= val <= 0x7FFFFFFFFFFF:
                    ptr_count += 1
        
        print(f"Found {ptr_count} potential pointers in this block")
        
        # Let's look at the first 64 bytes as hex
        print("\nFirst 64 bytes as hex:")
        for i in range(0, min(64, len(block)), 16):
            addr = ptr1 + i
            hex_part = ' '.join(f'{b:02X}' for b in block[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in block[i:i+16])
            print(f"0x{addr:08X}: {hex_part:<48} {ascii_part}")
    
    # Let's also check if these pointers form a pattern
    print("\nChecking if pointers form a pattern:")
    ptrs = []
    for i in range(0, min(80, len(team_data)), 8):
        ptr_val = struct.unpack('<Q', team_data[i:i+8])[0]
        if 0x100000000 <= ptr_val <= 0x7FFFFFFFFFFF:
            ptrs.append(ptr_val)
    
    if len(ptrs) >= 3:
        print("Pointer values:")
        for i, ptr in enumerate(ptrs[:10]):
            print(f"  [{i:2d}] 0x{ptr:016X}")
        
        # Check if they're sequential or have a pattern
        diffs = []
        for i in range(1, len(ptrs)):
            diff = ptrs[i] - ptrs[i-1]
            diffs.append(diff)
        
        if diffs:
            print(f"\nDifferences between consecutive pointers: {diffs[:10]}")
            # Check if all diffs are the same
            if len(set(diffs)) == 1:
                print(f"All pointers are spaced by 0x{diffs[0]:X} bytes")
            else:
                print("Pointers are not uniformly spaced")

if __name__ == "__main__":
    main()
