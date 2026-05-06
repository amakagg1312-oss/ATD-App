"""Search for playbook catalog using ASCII strings."""

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
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    # Search for ASCII playbook names
    playbook_names = [
        b'Flex',
        b'Triangle',
        b'Princeton',
        b'Horns',
        b'Motion',
        b'Pistol',
        b'Pace and Space',
        b'Grit and Grind',
        b'Seven Seconds',
        b'Post Up',
        b'Isolation',
        b'Pick and Roll',
    ]
    
    print("Searching for playbook names in memory...")
    print(f"{'='*80}")
    
    mbr = MBI()
    addr = 0
    regions = 0
    found = []
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                for name in playbook_names:
                    idx = buf.find(name)
                    if idx >= 0:
                        loc = mbr.BaseAddress + idx
                        found.append((loc, name.decode()))
            
            regions += 1
            if regions % 2000 == 0:
                print(f"  Scanned {regions} regions, found {len(found)}...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nFound {len(found)} playbook name references:")
    for loc, name in found[:20]:
        print(f"  0x{loc:X}: {name}")
        
        # Show context
        data = read_memory(h, loc - 30, 100)
        if data:
            for off in range(0, min(len(data), 80), 16):
                chunk = data[off:off+16]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                print(f"    [{off:03X}] {hex_str:<48} {ascii_str}")

if __name__ == "__main__":
    main()
