"""Examine playbook array at 0x300C0 and try to resolve play names."""

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
    
    playbook_base = 0x300C0
    
    print(f"Reading playbook array at 0x{playbook_base:X}")
    
    # Read all 60 entries (60 * 48 = 2880 bytes)
    pb_data = read_memory(h, playbook_base, 2880)
    if not pb_data:
        print("Failed to read playbook!")
        return
    
    # Extract all 60 offsets
    offsets = []
    for i in range(0, 2880, 48):
        val = struct.unpack_from('<I', pb_data, i)[0]
        offsets.append(val)
    
    print(f"Found {len(offsets)} entries")
    print(f"Offset range: {min(offsets)} - {max(offsets)}")
    
    # Show first 20 offsets
    print("\nFirst 20 offsets:")
    for i, val in enumerate(offsets[:20]):
        print(f"  [{i:2d}] {val:6d} (0x{val:04X})")
    
    # Try to resolve play names by reading at the offset as absolute address
    print("\n\nTrying to resolve play names (absolute addresses):")
    for i, val in enumerate(offsets[:20]):
        if val > 0x10000:  # Only try if it looks like a valid address
            str_data = read_memory(h, val, 40)
            if str_data:
                play_name = decode_wstring(str_data, 20)
                if play_name and len(play_name) > 2:
                    print(f"  [{i:2d}] 0x{val:X} -> '{play_name}'")
    
    # Try to find string block by looking at where offsets might point
    # The offsets are around 23740-24100, which is 0x5CBC-0x5E24
    # These are small values, so they might be relative to some base
    
    # Let's check if there's a string block at a known location
    # Try adding offsets to various base addresses
    
    print("\n\nTrying to find string block base...")
    
    # Try some common base addresses
    test_bases = [
        0x30000,  # Same region
        0x2FFCD8000,  # Old string block base
        0x2FFCA1000,  # Near old playbook base
        0x2A8000000,  # Near team/staff base
        0x2A7000000,  # Another candidate
    ]
    
    for base in test_bases:
        print(f"\nTesting base 0x{base:X}:")
        for i, val in enumerate(offsets[:5]):
            addr = base + val
            str_data = read_memory(h, addr, 40)
            if str_data:
                play_name = decode_wstring(str_data, 20)
                if play_name and len(play_name) > 2 and any(c.isalpha() for c in play_name):
                    print(f"  [{i}] 0x{addr:X} -> '{play_name}'")
                else:
                    print(f"  [{i}] 0x{addr:X} -> (not a play name: '{play_name[:20]}')")
            else:
                print(f"  [{i}] 0x{addr:X} -> (unreadable)")

if __name__ == "__main__":
    main()
