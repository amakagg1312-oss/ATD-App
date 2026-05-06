"""Search for play names as ASCII strings in memory."""

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
    
    # Search for play names as ASCII strings
    search_terms = [
        b"FIST DELAY",
        b"FIST STAGGER",
        b"QUICK FLARE",
        b"PUNCH RIP",
        b"QUICK ELBOW",
        b"GIVE ELBOW",
        b"PUNCH TRI",
        b"DBL TRI",
        b"SWING BACK",
    ]
    
    print("="*80)
    print("Searching for play names as ASCII strings")
    print("="*80)
    
    for term in search_terms:
        print(f"\nSearching for '{term.decode()}'...")
        
        mbr = MBI()
        addr = 0
        hits = []
        regions_checked = 0
        
        while True:
            result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
            if result == 0:
                break
            
            if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
                buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
                if buf:
                    idx = buf.find(term)
                    while idx >= 0:
                        loc = mbr.BaseAddress + idx
                        # Get context
                        context_start = max(0, idx - 20)
                        context_end = min(len(buf), idx + 40)
                        context = buf[context_start:context_end]
                        try:
                            text = context.decode('ascii', errors='replace')
                            hits.append((loc, text))
                        except:
                            hits.append((loc, "(binary)"))
                        idx = buf.find(term, idx + 1)
            
            regions_checked += 1
            if regions_checked % 3000 == 0:
                print(f"  Checked {regions_checked} regions...")
            
            addr = mbr.BaseAddress + mbr.RegionSize
        
        print(f"  Found {len(hits)} hits")
        if hits:
            for loc, text in hits[:5]:
                print(f"    0x{loc:X}: '{text}'")

if __name__ == "__main__":
    main()
