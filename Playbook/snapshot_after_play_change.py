"""Take snapshot after second play change and compare."""

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
    
    # Load before snapshot
    with open('D:\\project\\Playbook\\snapshot_before_play_change.json', 'r') as f:
        before = json.load(f)
    
    before_checksums = before['checksums']
    print(f"Loaded {len(before_checksums)} checksums from before snapshot")
    
    # Calculate current checksums
    print("Calculating current checksums...")
    current_checksums = {}
    regions = []
    
    mbr = MBI()
    addr = 0
    i = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0:
            if mbr.RegionSize < 0x10000000:
                if mbr.RegionSize > 0:
                    data = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 512))
                    if data:
                        ck1 = sum(data[:256]) & 0xFFFFFFFF
                        ck2 = sum(data[256:512]) & 0xFFFFFFFF if len(data) > 256 else 0
                        current_checksums[hex(mbr.BaseAddress)] = (ck1, ck2)
                        regions.append({
                            'base': mbr.BaseAddress,
                            'size': mbr.RegionSize,
                            'protect': mbr.Protect,
                        })
        
        addr = mbr.BaseAddress + mbr.RegionSize
        i += 1
        
        if i % 1000 == 0:
            print(f"  Processed {i} regions...")
    
    print(f"Found {len(current_checksums)} current regions")
    
    # Find changed regions
    print("\nFinding changed regions...")
    changed = []
    
    for base, checksum in current_checksums.items():
        if base in before_checksums:
            if checksum != before_checksums[base]:
                changed.append(base)
    
    print(f"Changed regions: {len(changed)}")
    
    # Show changed regions
    if changed:
        print("\nChanged regions (first 40):")
        for base in changed[:40]:
            print(f"  {base}")
    
    # Examine changed regions for playbook data
    if changed:
        print("\n" + "="*80)
        print("Examining changed regions for playbook data")
        print("="*80)
        
        for base_hex in changed[:30]:
            base = int(base_hex, 16)
            
            # Find region info
            region_info = None
            for r in regions:
                if r['base'] == base:
                    region_info = r
                    break
            
            if region_info and region_info['size'] >= 48:
                print(f"\nRegion {base_hex} (size: 0x{region_info['size']:X}):")
                
                # Read and show first 256 bytes
                data = read_memory(h, base, min(region_info['size'], 256))
                if data:
                    for off in range(0, min(len(data), 128), 16):
                        chunk = data[off:off+16]
                        hex_str = ' '.join(f'{b:02X}' for b in chunk)
                        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                        print(f"  [{off:03X}] {hex_str:<48} {ascii_str}")
                    
                    # Check for UTF-16LE strings
                    try:
                        text = data.decode('utf-16-le', errors='ignore')
                        printable = ''.join(c if c.isprintable() else '.' for c in text)
                        if len([c for c in printable if c.isalpha()]) > 5:
                            print(f"  TEXT: {printable[:80]}")
                    except:
                        pass
                    
                    # Check for playbook-like arrays (60 entries, 48-byte stride)
                    if region_info['size'] >= 2880:  # 60 * 48
                        pb_data = read_memory(h, base, 2880)
                        if pb_data:
                            import struct
                            offsets = []
                            for i in range(0, 2880, 48):
                                val = struct.unpack_from('<I', pb_data, i)[0]
                                if 0x50 < val < 0x10000:
                                    offsets.append((i, val))
                            
                            if len(offsets) > 20:
                                print(f"  PLAYBOOK ARRAY: {len(offsets)} entries")
                                for off, val in offsets[:10]:
                                    print(f"    [{off:04X}] offset={val}")

if __name__ == "__main__":
    main()
