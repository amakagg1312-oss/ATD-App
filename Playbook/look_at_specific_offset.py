"""Look at a specific offset in the team structure."""

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
    
    # Look at offset 0x338 specifically
    offset = 0x338
    if offset + 8 <= len(team_data):
        ptr_bytes = team_data[offset:offset+8]
        print(f"Bytes at offset 0x{offset:X}: {ptr_bytes.hex()}")
        ptr_val = struct.unpack('<Q', ptr_bytes)[0]
        print(f"Pointer value: 0x{ptr_val:016X} ({ptr_val})")
        
        # Check if this looks like a valid pointer
        if ptr_val < 0x100000:
            print("This pointer value is too small - likely not a pointer")
        elif ptr_val > 0x7FFFFFFFFFFF:
            print("This pointer value is too large - likely not a user-space pointer")
        else:
            print("This looks like a valid user-space pointer")
            
            # Let's see what's at this address
            block = read_memory(h, ptr_val, 0x200)
            if block:
                print(f"\nFirst 64 bytes at 0x{ptr_val:016X}:")
                for i in range(0, min(64, len(block)), 16):
                    addr = ptr_val + i
                    hex_part = ' '.join(f'{b:02X}' for b in block[i:i+16])
                    ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in block[i:i+16])
                    print(f"0x{addr:08X}: {hex_part:<48} {ascii_part}")
    
    # Let's also look at the surrounding area to see if there's a pattern
    print(f"\nLooking at offsets 0x{offset-0x20:X} to 0x{offset+0x20:X}:")
    start = max(0, offset - 0x20)
    end = min(len(team_data), offset + 0x20 + 8)
    for i in range(start, end, 8):
        if i + 8 <= len(team_data):
            val = struct.unpack('<Q', team_data[i:i+8])[0]
            print(f"  Offset 0x{i:04X}: 0x{val:016X}")

if __name__ == "__main__":
    main()
