"""Search for string block that contains valid play names at offsets 0x5CBC-0x6644."""

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
    
    # Playbook offsets from 0x300C0
    pb_offsets = [23740, 23780, 23800, 23860, 23900, 23940, 23980, 24020, 24060, 24100]
    
    print("Searching for string block that contains valid play names at playbook offsets...")
    print(f"Testing offsets: {pb_offsets[:5]}...")
    
    # Search all readable regions
    mbr = MBI()
    addr = 0
    regions_checked = 0
    candidates = []
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            # Check if region is large enough to contain the offsets
            if mbr.RegionSize > 27000:  # Max offset is ~26180
                # Read data at first few offsets
                valid_count = 0
                for off in pb_offsets[:5]:
                    if off < mbr.RegionSize:
                        str_data = read_memory(h, mbr.BaseAddress + off, 40)
                        if str_data:
                            play_name = decode_wstring(str_data, 20)
                            # Check if it looks like a play name
                            if play_name and len(play_name) > 3:
                                has_upper = any(c.isupper() for c in play_name)
                                has_digit = any(c.isdigit() for c in play_name)
                                if has_upper and has_digit:
                                    valid_count += 1
                
                if valid_count >= 3:
                    candidates.append((mbr.BaseAddress, mbr.RegionSize, valid_count))
        
        regions_checked += 1
        if regions_checked % 2000 == 0:
            print(f"  Checked {regions_checked} regions, found {len(candidates)} candidates...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nFound {len(candidates)} candidate string blocks")
    
    # Show candidates
    for base, size, count in candidates[:10]:
        print(f"\nCandidate: 0x{base:X} (size: 0x{size:X}, matches: {count})")
        
        # Show play names at all offsets
        for i, off in enumerate(pb_offsets[:10]):
            if off < size:
                str_data = read_memory(h, base + off, 40)
                if str_data:
                    play_name = decode_wstring(str_data, 20)
                    print(f"  [{i}] offset {off}: '{play_name}'")

if __name__ == "__main__":
    main()
