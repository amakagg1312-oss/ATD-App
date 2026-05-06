"""Take snapshot before play change for comparison."""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import json

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
    
    # Map all readable regions and record their checksums
    print("Mapping memory regions...")
    
    regions = []
    mbr = MBI()
    addr = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0:
            if mbr.RegionSize < 0x10000000:
                regions.append({
                    'base': mbr.BaseAddress,
                    'size': mbr.RegionSize,
                    'protect': mbr.Protect,
                })
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"Found {len(regions)} regions")
    
    # Calculate checksums for each region (first 512 bytes for better accuracy)
    print("Calculating checksums...")
    checksums = {}
    for i, region in enumerate(regions):
        if region['size'] > 0:
            data = read_memory(h, region['base'], min(region['size'], 512))
            if data:
                # Use multiple checksum points for better detection
                ck1 = sum(data[:256]) & 0xFFFFFFFF
                ck2 = sum(data[256:512]) & 0xFFFFFFFF if len(data) > 256 else 0
                checksums[hex(region['base'])] = (ck1, ck2)
        
        if i % 1000 == 0:
            print(f"  Processed {i}/{len(regions)} regions...")
    
    # Save to file
    output = {
        'pid': pid,
        'region_count': len(regions),
        'checksums': {k: list(v) for k, v in checksums.items()},
    }
    
    with open('D:\\project\\Playbook\\snapshot_before_play_change.json', 'w') as f:
        json.dump(output, f)
    
    print(f"\nSaved snapshot with {len(checksums)} region checksums")
    print("Now change a play in the playbook, then run snapshot_after_play_change.py")

if __name__ == "__main__":
    main()
