"""Debug: Search for Pittsburgh Steelers string in memory."""

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
    
    print("Searching for 'Pittsburgh Steelers'...")
    mbr = MBI()
    addr = 0
    found = False
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0:
            # Limit read to avoid huge regions, but we can read up to 0x100000
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf and b'Pittsburgh Steelers' in buf:
                offset = buf.find(b'Pittsburgh Steelers')
                print(f"Found 'Pittsburgh Steelers' at 0x{mbr.BaseAddress + offset:X} in region 0x{mbr.BaseAddress:X}-0x{mbr.BaseAddress + mbr.RegionSize:X}")
                found = True
                # Let's see a bit of context
                context_start = max(0, offset - 10)
                context_end = min(len(buf), offset + 40)
                context = buf[context_start:context_end]
                print(f"Context: {context}")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    if not found:
        print("String not found!")

if __name__ == "__main__":
    main()
