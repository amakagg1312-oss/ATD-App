"""Examine regions containing team abbreviations for playbook data."""

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
    
    # Regions that contain team abbreviations
    candidate_regions = [
        0xC6F230000,  # PHI
        0xC6F290000,  # PHI
        0xC6F2F0000,  # PHI
        0xC8D3F0000,  # LAL
        0xC8D450000,  # LAL
        0x259A0000,   # BOS, MIA
        0x2EA000000,  # MIA
    ]
    
    print("="*80)
    print("Examining candidate regions for playbook data")
    print("="*80)
    
    for region in candidate_regions:
        print(f"\n{'='*60}")
        print(f"Region 0x{region:X}")
        print(f"{'='*60}")
        
        # Read 64KB of data
        data = read_memory(h, region, 0x10000)
        if not data:
            print("  Not readable")
            continue
        
        # Look for team abbreviations and show context
        for team in [b'P\x00H\x00I\x00', b'L\x00A\x00L\x00', b'B\x00O\x00S\x00', b'M\x00I\x00A\x00']:
            team_name = team.decode('utf-16-le', errors='ignore').replace('\x00', '')
            idx = data.find(team)
            while idx >= 0:
                loc = region + idx
                # Show 100 bytes of context
                context = read_memory(h, loc - 30, 120)
                if context:
                    print(f"\n  Found '{team_name}' at 0x{loc:X}:")
                    
                    # Show as hex
                    for off in range(0, min(len(context), 100), 16):
                        chunk = context[off:off+16]
                        hex_str = ' '.join(f'{b:02X}' for b in chunk)
                        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                        print(f"    [{off:03X}] {hex_str:<48} {ascii_str}")
                
                idx = data.find(team, idx + 2)
        
        # Also look for arrays of 4-byte values that could be play offsets
        print(f"\n  Looking for offset arrays...")
        for i in range(0, len(data) - 240, 48):
            val = struct.unpack_from('<I', data, i)[0]
            if 0x50 < val < 0x5000:
                # Check next few entries
                offsets = []
                valid = True
                for j in range(0, 96, 48):
                    if i + j + 4 <= len(data):
                        v = struct.unpack_from('<I', data, i + j)[0]
                        if 0x50 < v < 0x5000:
                            offsets.append(v)
                        else:
                            valid = False
                            break
                
                if valid and len(offsets) >= 3:
                    print(f"    Offset array at 0x{region + i:X}: {offsets[:8]}")

if __name__ == "__main__":
    main()
