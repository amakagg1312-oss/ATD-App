"""Search for play string block by looking for regions with many short play-like strings."""

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

def decode_wstring(data, max_chars=50):
    try:
        raw = data[:max_chars*2]
        return raw.decode('utf-16-le', errors='ignore').split('\x00')[0].strip()
    except:
        return ""

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
    
    # Known playbook offsets from all_play_names.txt
    # FIST DELAY 25: 0x3E5684
    # FIST STAGGER 24: need to find
    # QUICK FLARE 51: need to find
    
    # Let's search for these specific offsets as 4-byte values in memory
    # If we find a region that contains these offsets, it might be the playbook array
    
    target_offsets = [
        0x3E5684,  # FIST DELAY 25
        0x3CFCB8,  # FIST DELAY
        0x3E02CE,  # FIST DELAY 2
    ]
    
    print("Searching for regions containing playbook offsets...")
    
    # Search for regions that contain these offset values
    mbr = MBI()
    addr = 0
    regions_checked = 0
    candidates = []
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                # Check if this region contains our target offsets
                found_offsets = []
                for target in target_offsets:
                    # Search for the 4-byte little-endian value
                    target_bytes = struct.pack('<I', target)
                    if target_bytes in buf:
                        found_offsets.append(target)
                
                if found_offsets:
                    candidates.append((mbr.BaseAddress, mbr.RegionSize, found_offsets))
        
        regions_checked += 1
        if regions_checked % 3000 == 0:
            print(f"  Checked {regions_checked} regions, found {len(candidates)} candidates...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nFound {len(candidates)} candidate regions")
    
    for base, size, offsets in candidates[:20]:
        print(f"\nRegion 0x{base:X} (size: 0x{size:X}):")
        print(f"  Contains offsets: {[hex(o) for o in offsets]}")
        
        # Show context around the found offsets
        for target in offsets:
            target_bytes = struct.pack('<I', target)
            data = read_memory(h, base, min(size, 0x10000))
            if data:
                idx = data.find(target_bytes)
                while idx >= 0:
                    print(f"  Found at offset 0x{idx:X} in region")
                    # Show surrounding data
                    context_start = max(0, idx - 16)
                    context_end = min(len(data), idx + 32)
                    context = data[context_start:context_end]
                    for off in range(0, len(context), 16):
                        chunk = context[off:off+16]
                        hex_str = ' '.join(f'{b:02X}' for b in chunk)
                        print(f"    [{context_start + off:04X}] {hex_str}")
                    idx = data.find(target_bytes, idx + 4)

if __name__ == "__main__":
    main()
