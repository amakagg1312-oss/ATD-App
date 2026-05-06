"""Examine new regions that appeared after team switch."""

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
    
    # New regions that appeared after team switch
    new_regions = [
        0x1b20000,
        0x1fa0000,
        0xc694d0000,
        0xcbd290000,
        0xcc79d0000,
    ]
    
    print("="*80)
    print("Examining new regions after team switch")
    print("="*80)
    
    for region in new_regions:
        print(f"\n{'='*60}")
        print(f"Region 0x{region:X}")
        print(f"{'='*60}")
        
        # Read 64KB of data
        data = read_memory(h, region, 0x10000)
        if not data:
            print("  Not readable")
            continue
        
        # Show first 256 bytes as hex
        print("\n  First 256 bytes:")
        for off in range(0, min(len(data), 256), 16):
            chunk = data[off:off+16]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print(f"    [{off:03X}] {hex_str:<48} {ascii_str}")
        
        # Look for UTF-16LE strings
        print("\n  UTF-16LE strings:")
        i = 0
        string_count = 0
        while i < len(data) - 2 and string_count < 30:
            null_pos = data.find(b'\x00\x00', i)
            if null_pos == -1:
                break
            
            start = null_pos + 2
            if start % 2 != 0:
                start += 1
            
            next_null = data.find(b'\x00\x00', start)
            if next_null == -1:
                next_null = len(data)
            
            s_bytes = data[start:next_null]
            if len(s_bytes) >= 4:
                try:
                    s = s_bytes.decode('utf-16-le', errors='replace').strip()
                    if s and len(s) > 2:
                        print(f"    [{start:06X}] {s}")
                        string_count += 1
                except:
                    pass
            
            i = null_pos + 2
        
        # Look for arrays of 4-byte offsets (playbook structure)
        print("\n  Looking for playbook-like arrays...")
        for i in range(0, len(data) - 240, 48):
            val = struct.unpack_from('<I', data, i)[0]
            if 0x50 < val < 0x5000:
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
                    print(f"    Array at 0x{region + i:X}: {offsets[:8]}")

if __name__ == "__main__":
    main()
