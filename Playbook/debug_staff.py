"""Debug staff table finder."""

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
    
    # Known staff table base from earlier
    known_base = 0x2A84DD940
    
    # Verify we can read it
    first_buf = read_memory(h, known_base + 0x50, 80)
    last_buf = read_memory(h, known_base + 0x78, 80)
    
    if first_buf and last_buf:
        fn = first_buf.decode('utf-16-le', errors='ignore').split('\x00')[0]
        ln = last_buf.decode('utf-16-le', errors='ignore').split('\x00')[0]
        print(f"Known base 0x{known_base:X}: {fn} {ln}")
    
    # Search for "Nick"
    nick_bytes = b'N\x00i\x00c\x00k\x00\x00\x00'
    print(f"\nSearching for 'Nick'...")
    
    mbr = MBI()
    addr = 0
    found = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                idx = buf.find(nick_bytes)
                if idx >= 0:
                    found += 1
                    entry_base = mbr.BaseAddress + idx - 0x50
                    print(f"  Found 'Nick' at 0x{mbr.BaseAddress + idx:X}, entry_base=0x{entry_base:X}")
                    
                    # Verify
                    last_addr = entry_base + 0x78
                    last_buf = read_memory(h, last_addr, 20)
                    if last_buf:
                        ln = last_buf.decode('utf-16-le', errors='ignore').split('\x00')[0]
                        print(f"    Last name at 0x{last_addr:X}: {ln}")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nTotal 'Nick' found: {found}")

if __name__ == "__main__":
    main()
