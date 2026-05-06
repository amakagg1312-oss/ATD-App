"""Examine team structure pointers to find playbook references."""

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
    
    team_base = 0x2A82B17D0
    team_stride = 5672
    name_offset = 0x2E2
    
    print("="*80)
    print("STEP 1: Dump full team structure")
    print("="*80)
    
    # Read full team structure
    team_data = read_memory(h, team_base, team_stride)
    if not team_data:
        print("Failed to read team structure!")
        return
    
    # Show all 8-byte values
    print(f"\nTeam structure @ 0x{team_base:X} (size: {team_stride}):")
    for i in range(0, team_stride, 8):
        val = struct.unpack_from('<Q', team_data, i)[0]
        if val > 0:
            print(f"  [{i:04X}] = 0x{val:X}")
    
    print("\n" + "="*80)
    print("STEP 2: Examine pointers in team structure")
    print("="*80)
    
    # Examine each pointer
    for i in range(0, team_stride, 8):
        val = struct.unpack_from('<Q', team_data, i)[0]
        
        # Check if it's a valid pointer
        if 0x10000000 < val < 0x300000000:
            print(f"\n[{i:04X}] 0x{val:X}:")
            
            # Read data at pointer
            ptr_data = read_memory(h, val, 256)
            if ptr_data:
                # Check for strings
                try:
                    text = ptr_data[:60].decode('utf-16-le', errors='ignore')
                    printable = ''.join(c if c.isprintable() else '.' for c in text)
                    if len([c for c in printable if c.isalpha()]) > 3:
                        print(f"  STRING: {printable[:50]}")
                except:
                    pass
                
                # Check for arrays of small integers (play IDs)
                uint16_vals = []
                for j in range(0, 40, 2):
                    w = struct.unpack_from('<H', ptr_data, j)[0]
                    if 0 < w < 500:
                        uint16_vals.append(w)
                
                if len(uint16_vals) > 5:
                    print(f"  UINT16 ARRAY: {uint16_vals[:15]}")
                
                # Check for arrays of 4-byte offsets (play offsets)
                uint32_vals = []
                for j in range(0, 40, 4):
                    dw = struct.unpack_from('<I', ptr_data, j)[0]
                    if 0x50 < dw < 0x2000:
                        uint32_vals.append(dw)
                
                if len(uint32_vals) > 3:
                    print(f"  UINT32 OFFSETS: {uint32_vals[:10]}")
                
                # Show first 32 bytes as hex
                hex_str = ' '.join(f'{b:02X}' for b in ptr_data[:32])
                print(f"  HEX: {hex_str}")
    
    print("\n" + "="*80)
    print("STEP 3: Search for play strings in entire memory")
    print("="*80)
    
    # Search for known play name patterns
    known_fragments = [
        b'F\x00I\x00S\x00T\x00',
        b'P\x00U\x00N\x00C\x00H\x00',
        b'H\x00O\x00R\x00N\x00S\x00',
        b'I\x00S\x00O\x00',
        b'Q\x00U\x00I\x00C\x00K\x00',
        b'G\x00I\x00V\x00E\x00',
        b'C\x00U\x00T\x00',
    ]
    
    for fragment in known_fragments:
        display = fragment.decode('utf-16-le', errors='ignore').replace('\x00', '')
        print(f"\nSearching for '{display}'...")
        
        mbr = MBI()
        addr = 0
        hits = []
        
        while True:
            result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
            if result == 0:
                break
            
            if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
                buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
                if buf:
                    idx = buf.find(fragment)
                    while idx >= 0:
                        loc = mbr.BaseAddress + idx
                        # Check if this is part of a longer play-like string
                        context = read_memory(h, loc - 10, 40)
                        if context:
                            text = context.decode('utf-16-le', errors='ignore')
                            # Check if string has digits (play names usually have numbers)
                            if any(c.isdigit() for c in text):
                                hits.append((loc, text))
                        idx = buf.find(fragment, idx + 2)
            
            addr = mbr.BaseAddress + mbr.RegionSize
        
        print(f"  Found {len(hits)} hits with digits")
        if hits:
            for loc, text in hits[:5]:
                print(f"    0x{loc:X}: '{text[:30]}'")

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

if __name__ == "__main__":
    main()
