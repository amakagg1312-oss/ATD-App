"""Dump and examine team structure memory."""

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
    
    # Let's dump the first team structure
    print("\nDumping first team structure (0x{:X} - 0x{:X}):".format(team_base, team_base + team_stride))
    team_data = read_memory(h, team_base, team_stride)
    if not team_data:
        print("Failed to read team data!")
        return
    
    # Print as hex
    print("Hex dump:")
    for i in range(0, min(256, len(team_data)), 16):
        addr = team_base + i
        hex_part = ' '.join(f'{b:02X}' for b in team_data[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in team_data[i:i+16])
        print(f"0x{addr:08X}: {hex_part:<48} {ascii_part}")
    
    # Look for potential pointers (8-byte values that point to reasonable memory ranges)
    print("\nLooking for potential 64-bit pointers in team structure:")
    pointers = []
    for i in range(0, len(team_data) - 7, 8):
        ptr_val = struct.unpack('<Q', team_data[i:i+8])[0]
        # Check if it's in a reasonable range for a pointer (not too small, not in kernel space)
        if 0x100000000 <= ptr_val <= 0x7FFFFFFFFFFF:
            pointers.append((i, ptr_val))
    
    if pointers:
        print(f"Found {len(pointers)} potential pointers:")
        for offset, ptr_val in pointers[:20]:  # Show first 20
            print(f"  Offset 0x{offset:04X}: 0x{ptr_val:016X}")
    else:
        print("No potential pointers found in the expected range.")
    
    # Look for the known play offsets as 4-byte values
    print("\nLooking for known play offsets as 4-byte little-endian values:")
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
    for i in range(0, len(team_data) - 3, 4):
        val = struct.unpack('<I', team_data[i:i+4])[0]
        if val in known_offsets:
            found_offsets.append((i, val))
    
    if found_offsets:
        print(f"Found {len(found_offsets)} known play offsets:")
        for offset, val in found_offsets:
            print(f"  Offset 0x{offset:04X}: 0x{val:08X} ({val})")
    else:
        print("No known play offsets found as 4-byte values.")
    
    # Also check the second team
    print("\n" + "="*60)
    print("Dumping second team structure for comparison:")
    team2_base = team_base + team_stride
    team2_data = read_memory(h, team2_base, team_stride)
    if team2_data:
        print("Hex dump (first 128 bytes):")
        for i in range(0, min(128, len(team2_data)), 16):
            addr = team2_base + i
            hex_part = ' '.join(f'{b:02X}' for b in team2_data[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in team2_data[i:i+16])
            print(f"0x{addr:08X}: {hex_part:<48} {ascii_part}")

if __name__ == "__main__":
    main()
