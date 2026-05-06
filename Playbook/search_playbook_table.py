"""Search for the global playbook table using staff playbook indices."""

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
    
    # Staff playbook indices (from 0x0B8 region, first entry at 0x0B8)
    # Nick Nurse: 138 (0x8A)
    # Doc Rivers: 25 (0x19)
    # Billy Donovan: 131 (0x83)
    # Kenny Atkinson: 180 (0xB4)
    # Joe Mazzulla: 169 (0xA9)
    
    # These are playbook IDs. Let's search for a playbook table
    # by looking for known playbook names
    
    known_playbooks = [
        b'7\x006\x00e\x00r\x00s\x00',  # "76ers"
        b'B\x00u\x00c\x00k\x00s\x00',  # "Bucks"
        b'C\x00e\x00l\x00t\x00i\x00c\x00s\x00',  # "Celtics"
        b'F\x00l\x00e\x00x\x00',  # "Flex"
        b'T\x00r\x00i\x00a\x00n\x00g\x00l\x00e\x00',  # "Triangle"
        b'P\x00a\x00c\x00e\x00',  # "Pace"
        b'P\x00r\x00i\x00n\x00c\x00e\x00',  # "Prince"
        b'H\x00o\x00r\x00n\x00s\x00',  # "Horns"
        b'M\x00o\x00t\x00i\x00o\x00n\x00',  # "Motion"
        b'P\x00i\x00s\x00t\x00o\x00l\x00',  # "Pistol"
    ]
    
    print("Searching for playbook table with known playbook names...")
    print(f"{'='*80}")
    
    mbr = MBI()
    addr = 0
    regions = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                for pattern in known_playbooks[:5]:  # Search first 5 patterns
                    idx = buf.find(pattern)
                    if idx >= 0:
                        # Found a playbook name
                        text = buf[max(0,idx-20):idx+60].decode('utf-16-le', errors='ignore')
                        print(f"  Found at 0x{mbr.BaseAddress + idx:X}: ...{text}...")
                        
                        # Read more context
                        full_data = read_memory(h, mbr.BaseAddress + idx - 100, 300)
                        if full_data:
                            # Try to understand the structure
                            print(f"    Context (hex):")
                            for off in range(0, min(len(full_data), 200), 16):
                                chunk = full_data[off:off+16]
                                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                                print(f"      [{off:03X}] {hex_str}")
                        break
            
            regions += 1
            if regions % 2000 == 0:
                print(f"  Scanned {regions} regions...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print("\nDone!")

if __name__ == "__main__":
    main()
