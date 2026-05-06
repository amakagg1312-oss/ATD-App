"""Search for Pittsburgh Steelers in both ASCII and UTF-16LE."""

import sys
import io
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
    
    ascii_bytes = b'Pittsburgh Steelers'
    utf16_bytes = 'Pittsburgh Steelers'.encode('utf-16le')
    
    print(f"Searching for ASCII: {ascii_bytes}")
    print(f"Searching for UTF-16LE: {utf16_bytes.hex()}")
    
    mbr = MBI()
    addr = 0
    found_ascii = []
    found_utf16 = []
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0:
            # Limit the read to avoid reading huge regions, but we can read up to 0x100000
            max_read = min(mbr.RegionSize, 0x100000)
            buf = read_memory(h, mbr.BaseAddress, max_read)
            if buf:
                # Search for ASCII
                offset = buf.find(ascii_bytes)
                while offset != -1:
                    found_ascii.append((mbr.BaseAddress + offset, offset))
                    offset = buf.find(ascii_bytes, offset + 1)
                
                # Search for UTF-16LE
                offset = buf.find(utf16_bytes)
                while offset != -1:
                    found_utf16.append((mbr.BaseAddress + offset, offset))
                    offset = buf.find(utf16_bytes, offset + 1)
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nFound {len(found_ascii)} ASCII matches:")
    for base_addr, offset in found_ascii[:10]:  # Limit output
        print(f"  0x{base_addr + offset:X} (region base 0x{base_addr:X})")
    
    print(f"\nFound {len(found_utf16)} UTF-16LE matches:")
    for base_addr, offset in found_utf16[:10]:
        print(f"  0x{base_addr + offset:X} (region base 0x{base_addr:X})")
    
    if not found_ascii and not found_utf16:
        print("String not found in either encoding!")

if __name__ == "__main__":
    main()
