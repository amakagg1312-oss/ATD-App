"""Search for playbook catalog in memory."""

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import struct
import sys

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

def safe_print(s):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', errors='replace').decode('ascii'))

def main():
    pid = find_process()
    if not pid:
        safe_print("NBA2K26.exe not running!")
        return
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        safe_print("Failed to open process!")
        return
    
    # Search for "Flex" playbook name (common playbook)
    flex_bytes = b'F\x00l\x00e\x00x\x00\x00\x00'
    
    safe_print("Searching for 'Flex' playbook...")
    
    mbr = MBI()
    addr = 0
    regions = 0
    found_locations = []
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                idx = buf.find(flex_bytes)
                while idx >= 0:
                    found_locations.append(mbr.BaseAddress + idx)
                    idx = buf.find(flex_bytes, idx + 2)
            
            regions += 1
            if regions % 2000 == 0:
                safe_print(f"  Scanned {regions} regions, found {len(found_locations)}...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    safe_print(f"\nFound 'Flex' at {len(found_locations)} locations:")
    
    # Show first 10 locations with context
    for loc in found_locations[:10]:
        safe_print(f"\n  Location: 0x{loc:X}")
        data = read_memory(h, loc - 50, 200)
        if data:
            # Show hex dump
            for off in range(0, min(len(data), 150), 16):
                chunk = data[off:off+16]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                try:
                    text = chunk.decode('utf-16-le', errors='ignore')
                    printable = ''.join(c if c.isprintable() else '.' for c in text)
                    safe_print(f"    [{off:03X}] {hex_str:<48} {printable}")
                except:
                    safe_print(f"    [{off:03X}] {hex_str}")

if __name__ == "__main__":
    main()
