"""Find staff table with better verification.

Uses known stride and searches for consecutive coach entries to verify the table.
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

# Coaches to search for
COACHES = [
    ("Nick", "Nurse"),
    ("Doc", "Rivers"),
    ("Joe", "Mazzulla"),
    ("Tyronn", "Lue"),
    ("Taylor", "Jenkins"),
]

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p.pid
    return None

def scan_for_coach_last(h, last_name):
    """Search memory for coach last name and return all addresses where found."""
    last_bytes = encode_wstring(last_name)
    addresses = []
    
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
                idx = raw.find(last_bytes)
                while idx >= 0:
                    addresses.append(mbr.BaseAddress + idx)
                    idx = raw.find(last_bytes, idx + 2)
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    return addresses

def verify_staff_entry(h, last_addr, stride=432):
    """Verify this is a real staff entry by checking surrounding entries."""
    # Try different name offset patterns
    # Pattern 1: first name before last name (negative offset)
    # Pattern 2: first name after last name (positive offset)
    
    for first_offset in [-40, 40, -80, 80, -50, 50]:
        first_addr = last_addr + first_offset
        first_buf = read_memory(h, first_addr, 60)
        if first_buf:
            first_name = decode_wstring(first_buf, 20)
            last_buf = read_memory(h, last_addr, 60)
            last_name = decode_wstring(last_buf, 20)
            
            if first_name and last_name and len(first_name) > 1 and len(last_name) > 1:
                # Check if this looks like a real name
                if first_name.isalpha() or ' ' in first_name:
                    if last_name.isalpha() or ' ' in last_name:
                        return {
                            'last_addr': last_addr,
                            'first_addr': first_addr,
                            'first_offset': first_offset,
                            'first_name': first_name,
                            'last_name': last_name,
                            'stride': stride
                        }
    
    return None

def find_table_base(h, last_addr, first_offset, stride):
    """Try to find the table base by scanning backwards for consecutive entries."""
    # The table base should be at last_addr - first_offset - (slot * stride)
    # where slot is the entry index
    
    # Try to find the start of the table by scanning backwards
    candidate_base = last_addr + first_offset  # This is the first name address
    
    # Read several entries backwards to find where the table starts
    for slot in range(-50, 1):
        test_base = candidate_base - (slot * stride)
        # Check if this looks like a valid table start
        # Read first few entries
        valid_entries = 0
        for i in range(5):
            entry_addr = test_base + (i * stride)
            first_buf = read_memory(h, entry_addr, 60)
            last_buf = read_memory(h, entry_addr + first_offset, 60)
            
            if first_buf and last_buf:
                fn = decode_wstring(first_buf, 20)
                ln = decode_wstring(last_buf, 20)
                if fn and ln and len(fn) > 1 and len(ln) > 1:
                    valid_entries += 1
        
        if valid_entries >= 3:
            return test_base, valid_entries
    
    return None, 0

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
    
    stride = 432  # Known from previous version
    
    # Search for Nick Nurse's last name
    print("\nSearching for 'Nurse'...")
    nurse_addrs = scan_for_coach_last(h, "Nurse")
    print(f"Found 'Nurse' at {len(nurse_addrs)} locations")
    
    # Search for Doc Rivers' last name
    print("\nSearching for 'Rivers'...")
    rivers_addrs = scan_for_coach_last(h, "Rivers")
    print(f"Found 'Rivers' at {len(rivers_addrs)} locations")
    
    # Verify entries and find table
    print(f"\n{'='*60}")
    print("VERIFYING ENTRIES")
    print(f"{'='*60}")
    
    verified = []
    for addr in nurse_addrs[:5]:
        entry = verify_staff_entry(h, addr, stride)
        if entry:
            verified.append(entry)
            print(f"  Verified: {entry['first_name']} {entry['last_name']}")
            print(f"    Last@0x{entry['last_addr']:X}, First@0x{entry['first_addr']:X}")
            print(f"    First offset: {entry['first_offset']} (0x{entry['first_offset']:X})")
    
    for addr in rivers_addrs[:5]:
        entry = verify_staff_entry(h, addr, stride)
        if entry:
            verified.append(entry)
            print(f"  Verified: {entry['first_name']} {entry['last_name']}")
            print(f"    Last@0x{entry['last_addr']:X}, First@0x{entry['first_addr']:X}")
            print(f"    First offset: {entry['first_offset']} (0x{entry['first_offset']:X})")
    
    if verified:
        # Find table base from first verified entry
        entry = verified[0]
        table_base, valid = find_table_base(h, entry['last_addr'], entry['first_offset'], stride)
        
        if table_base:
            print(f"\n{'='*60}")
            print("TABLE FOUND")
            print(f"{'='*60}")
            print(f"Table base: 0x{table_base:X}")
            print(f"Stride: {stride} (0x{stride:X})")
            print(f"First name offset: {entry['first_offset']} (0x{entry['first_offset']:X})")
            print(f"Last name offset: 0")
            
            # Read first 10 entries from table
            print(f"\nFirst 10 entries:")
            for i in range(10):
                entry_addr = table_base + (i * stride)
                first_buf = read_memory(h, entry_addr, 60)
                last_buf = read_memory(h, entry_addr + entry['first_offset'], 60)
                
                if first_buf and last_buf:
                    fn = decode_wstring(first_buf, 20)
                    ln = decode_wstring(last_buf, 20)
                    if fn and ln:
                        print(f"  [{i}] {fn} {ln}")
                    else:
                        print(f"  [{i}] (empty)")
        else:
            print("\nCould not find table base")
    else:
        print("\nNo verified staff entries found!")

if __name__ == "__main__":
    main()
