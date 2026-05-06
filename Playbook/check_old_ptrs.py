"""Check old pointer addresses and find new pointer structure."""

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
    
    # Old pointer addresses from offsets file
    old_ptrs = {
        'Player': 132244216,   # 0x7E1F838
        'Stadium': 132244240,  # 0x7E1F850
        'Team': 132244248,     # 0x7E1F858
        'Staff': 132244312,    # 0x7E1F898
    }
    
    print("Checking old pointer addresses:")
    for name, addr in old_ptrs.items():
        buf = read_memory(h, addr, 8)
        if buf:
            val = struct.unpack('<Q', buf[:8])[0]
            print(f"  {name} @ 0x{addr:X} (0x{addr:X}): 0x{val:X}")
        else:
            print(f"  {name} @ 0x{addr:X}: unreadable")
    
    # Also check the base address 0x7E1F878
    print(f"\nChecking region around 0x7E1F800:")
    for offset in range(0, 0x200, 8):
        addr = 0x7E1F800 + offset
        buf = read_memory(h, addr, 8)
        if buf:
            val = struct.unpack('<Q', buf[:8])[0]
            if val > 0x1000000:  # Only show non-zero pointers
                print(f"  0x{addr:X}: 0x{val:X}")
    
    # Check if the pointer region moved
    print(f"\nSearching for pointer-like values in 0x7E00000-0x7F00000...")
    for base in range(0x7E00000, 0x7F00000, 0x1000):
        buf = read_memory(h, base, 0x100)
        if buf:
            # Check if this region contains pointers to game data
            pointer_count = 0
            for i in range(0, 0x100, 8):
                val = struct.unpack('<Q', buf[i:i+8])[0]
                if 0x10000000 < val < 0x300000000:  # Likely pointer range
                    pointer_count += 1
            
            if pointer_count > 10:  # Region with many pointers
                print(f"  0x{base:X}: {pointer_count} pointers in 0x100 bytes")

if __name__ == "__main__":
    main()
