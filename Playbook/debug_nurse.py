"""Debug nurse bytes."""

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
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    # Known staff table base
    known_base = 0x2A84DD940
    
    # Read last name at known location
    last_addr = known_base + 0x78
    last_buf = read_memory(h, last_addr, 40)
    
    if last_buf:
        print(f"Last name bytes at 0x{last_addr:X}:")
        print(f"  Raw: {last_buf[:20]}")
        print(f"  Hex: {last_buf[:20].hex()}")
        print(f"  Decoded: {last_buf.decode('utf-16-le', errors='ignore').split(chr(0))[0]}")
    
    # Check what "Nurse" encodes to
    nurse_bytes = b'N\x00u\x00r\x00s\x00e\x00\x00\x00'
    print(f"\nExpected 'Nurse' bytes:")
    print(f"  Raw: {nurse_bytes}")
    print(f"  Hex: {nurse_bytes.hex()}")
    
    # Check if they match
    if last_buf and last_buf[:len(nurse_bytes)] == nurse_bytes:
        print("\nBytes match!")
    else:
        print("\nBytes DON'T match!")
        print(f"  Expected: {nurse_bytes.hex()}")
        print(f"  Got:      {last_buf[:len(nurse_bytes)].hex() if last_buf else 'None'}")

if __name__ == "__main__":
    main()
