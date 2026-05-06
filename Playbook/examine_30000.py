"""Examine region 0x30000 which has playbook-like array."""

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
    
    # Region 0x30000 has playbook-like array
    region = 0x30000
    region_size = 0x2A000
    
    print(f"Examining region 0x{region:X} (size: 0x{region_size:X})")
    
    # Read the entire region
    data = read_memory(h, region, region_size)
    if not data:
        print("Failed to read region!")
        return
    
    # Look for arrays of 4-byte offsets at 48-byte intervals (playbook stride)
    print("\nSearching for playbook arrays (48-byte stride)...")
    
    for base_offset in range(0, len(data) - 2880, 48):
        # Check if this looks like a playbook array (60 entries)
        offsets = []
        valid = True
        for i in range(0, 60 * 48, 48):
            if base_offset + i + 4 <= len(data):
                val = struct.unpack_from('<I', data, base_offset + i)[0]
                if 0x50 < val < 0x10000:
                    offsets.append((i, val))
                else:
                    valid = False
                    break
        
        if valid and len(offsets) >= 40:  # At least 40 valid entries
            print(f"\n*** PLAYBOOK ARRAY at 0x{region + base_offset:X} ({len(offsets)} entries) ***")
            
            # Try to resolve play names
            # The offsets might point to a string block
            # Let's check if they point to valid UTF-16LE strings
            
            # First, check if offsets point within this region
            for entry_off, val in offsets[:10]:
                if val < region_size:
                    # Points within this region
                    str_addr = region + val
                    str_data = read_memory(h, str_addr, 40)
                    if str_data:
                        play_name = decode_wstring(str_data, 20)
                        print(f"  [{entry_off//48:2d}] offset={val:5d} (0x{val:04X}) -> '{play_name}'")
                else:
                    # Points elsewhere - try to read
                    str_data = read_memory(h, val, 40)
                    if str_data:
                        play_name = decode_wstring(str_data, 20)
                        if play_name and len(play_name) > 2:
                            print(f"  [{entry_off//48:2d}] offset={val:5d} (0x{val:04X}) -> '{play_name}'")
                        else:
                            print(f"  [{entry_off//48:2d}] offset={val:5d} (0x{val:04X}) -> (not a string)")
                    else:
                        print(f"  [{entry_off//48:2d}] offset={val:5d} (0x{val:04X}) -> (unreadable)")
            
            # Only show first match
            break

if __name__ == "__main__":
    main()
