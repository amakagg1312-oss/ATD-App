"""Find staff table with correct offsets.

The staff table has different name offsets than the player table:
- Player: first@0x28, last@0x0
- Staff: first@0x50, last@0x78 (from old offsets)

This script searches for the staff-specific pattern.
"""

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
        ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", ctypes.c_uint32),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
    ]

def encode_wstring(s):
    return (s + "\x00").encode('utf-16-le')

def decode_wstring(data, max_chars=30):
    try:
        raw = data[:max_chars*2]
        return raw.decode('utf-16-le', errors='ignore').split('\x00')[0].strip()
    except:
        return ""

def read_memory(h, addr, size):
    buf = create_string_buffer(size)
    if kernel.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

# Known coaches
COACHES = [
    ("Nick", "Nurse"),
    ("Doc", "Rivers"),
    ("Joe", "Mazzulla"),
    ("Tyronn", "Lue"),
]

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p.pid
    return None

def scan_for_staff_entry(h, first_name, last_name, first_offset=0x50, last_offset=0x78, name_len=40):
    """Search for staff entry using staff-specific offsets."""
    first_bytes = encode_wstring(first_name)
    last_bytes = encode_wstring(last_name)
    
    hits = []
    mbr = MBI()
    addr = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = create_string_buffer(mbr.RegionSize)
            if kernel.ReadProcessMemory(h, ctypes.c_void_p(mbr.BaseAddress), buf, mbr.RegionSize, byref(c_size_t(0))):
                raw = buf.raw
                
                # Search for first name
                idx = raw.find(first_bytes)
                while idx >= 0:
                    # Calculate entry base from first name position
                    entry_base = mbr.BaseAddress + idx - first_offset
                    
                    # Verify last name at expected offset
                    last_addr = entry_base + last_offset
                    last_buf = read_memory(h, last_addr, len(last_bytes) + 10)
                    
                    if last_buf and last_buf[:len(last_bytes)] == last_bytes:
                        # Found both names at correct offsets
                        hits.append({
                            'entry_base': entry_base,
                            'first_addr': mbr.BaseAddress + idx,
                            'last_addr': last_addr,
                            'first_name': first_name,
                            'last_name': last_name,
                        })
                    
                    idx = raw.find(first_bytes, idx + 2)
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    return hits

def verify_staff_table(h, entry_base, stride=432, first_offset=0x50, last_offset=0x78, name_len=40):
    """Verify this is a real staff table by checking consecutive entries."""
    # Read 5 entries starting from this base
    entries = []
    for i in range(5):
        addr = entry_base + (i * stride)
        first_buf = read_memory(h, addr + first_offset, name_len * 2)
        last_buf = read_memory(h, addr + last_offset, name_len * 2)
        
        if first_buf and last_buf:
            fn = decode_wstring(first_buf, name_len)
            ln = decode_wstring(last_buf, name_len)
            entries.append((fn, ln))
        else:
            entries.append(("", ""))
    
    # Count valid entries (entries with readable names)
    valid = sum(1 for fn, ln in entries if fn and ln and len(fn) > 1 and len(ln) > 1)
    return valid, entries

def main():
    pid = find_process()
    if not pid:
        print("NBA2K26.exe not running!")
        return
    
    print(f"Found NBA2K26.exe PID: {pid}")
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    stride = 432
    
    # Try different offset combinations
    offset_patterns = [
        (0x50, 0x78, 40),  # Old staff offsets
        (0x28, 0x0, 20),   # Player offsets (for comparison)
        (0x40, 0x60, 32),  # Alternative
        (0x50, 0x70, 32),  # Alternative
    ]
    
    for first_off, last_off, name_len in offset_patterns:
        print(f"\n{'='*60}")
        print(f"Testing offsets: first=0x{first_off:X}, last=0x{last_off:X}, len={name_len}")
        print(f"{'='*60}")
        
        hits = scan_for_staff_entry(h, "Nick", "Nurse", first_off, last_off, name_len)
        print(f"Found {len(hits)} hits for Nick Nurse")
        
        if hits:
            # Verify the table
            for hit in hits[:3]:
                valid, entries = verify_staff_table(h, hit['entry_base'], stride, first_off, last_off, name_len)
                print(f"\n  Entry at 0x{hit['entry_base']:X} - {valid}/5 valid entries")
                for i, (fn, ln) in enumerate(entries):
                    print(f"    [{i}] {fn} {ln}")
                
                if valid >= 3:
                    print(f"\n  *** VALID TABLE FOUND ***")
                    print(f"  Table base: 0x{hit['entry_base']:X}")
                    print(f"  Stride: {stride}")
                    print(f"  First name offset: 0x{first_off:X}")
                    print(f"  Last name offset: 0x{last_off:X}")
                    print(f"  Name length: {name_len}")
                    
                    # Read more entries
                    print(f"\n  First 15 entries:")
                    for i in range(15):
                        addr = hit['entry_base'] + (i * stride)
                        first_buf = read_memory(h, addr + first_off, name_len * 2)
                        last_buf = read_memory(h, addr + last_off, name_len * 2)
                        
                        if first_buf and last_buf:
                            fn = decode_wstring(first_buf, name_len)
                            ln = decode_wstring(last_buf, name_len)
                            if fn and ln:
                                print(f"    [{i}] {fn} {ln}")

if __name__ == "__main__":
    main()
