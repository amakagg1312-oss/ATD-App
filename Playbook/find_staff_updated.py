"""Find staff table base and offsets after game update.

Searches NBA2K26.exe memory for known coach names to locate the staff table,
then analyzes the structure to determine stride and name offsets.
"""

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import struct
import sys

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

def decode_wstring(data):
    try:
        return data.decode('utf-16-le', errors='ignore').split('\x00')[0].strip()
    except:
        return ""

def read_memory(h, addr, size):
    buf = create_string_buffer(size)
    if kernel.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

# Known NBA coaches (2025-26 season) - update if needed
COACHES = [
    ("Nick", "Nurse"),
    ("Doc", "Rivers"),
    ("Joe", "Mazzulla"),
    ("Tyronn", "Lue"),
    ("Taylor", "Jenkins"),
    ("Jamahl", "Mosley"),
    ("Chris", "Finch"),
    ("Mark", "Daigneault"),
    ("Ime", "Udoka"),
    ("J.B.", "Bickerstaff"),
    ("Kenny", "Atkinson"),
    ("Mike", "Brown"),
    ("Darvin", "Ham"),
    ("Will", "Hardy"),
    ("Steve", "Clifford"),
]

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p.pid
    return None

def scan_for_coach(h, first_name, last_name):
    """Search memory for a coach name pair and return candidate addresses."""
    last_bytes = encode_wstring(last_name)
    first_bytes = encode_wstring(first_name)
    
    candidates = []
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
                    # Found last name, now search nearby for first name
                    # Try different offsets around the last name
                    for offset_delta in range(-200, 200, 2):
                        test_addr = mbr.BaseAddress + idx + offset_delta
                        test_buf = create_string_buffer(len(first_bytes))
                        if kernel.ReadProcessMemory(h, ctypes.c_void_p(test_addr), test_buf, len(first_bytes), byref(c_size_t(0))):
                            if test_buf.raw == first_bytes:
                                candidates.append({
                                    'last_addr': mbr.BaseAddress + idx,
                                    'first_addr': test_addr,
                                    'offset_delta': offset_delta,
                                    'coach': f"{first_name} {last_name}"
                                })
                                break  # Found this coach, move to next occurrence
                    
                    idx = raw.find(last_bytes, idx + 2)
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    return candidates

def analyze_structure(h, candidates):
    """Analyze found candidates to determine stride and offsets."""
    if not candidates:
        return None
    
    # Group by offset pattern
    patterns = {}
    for c in candidates:
        delta = c['offset_delta']
        if delta not in patterns:
            patterns[delta] = []
        patterns[delta].append(c)
    
    # Find the most common pattern (likely the correct one)
    best_delta = max(patterns.keys(), key=lambda d: len(patterns[d]))
    best_candidates = patterns[best_delta]
    
    print(f"\nMost common offset delta: {best_delta} ({len(best_candidates)} matches)")
    
    # Calculate stride by looking at distances between consecutive entries
    addresses = sorted([c['last_addr'] for c in best_candidates])
    distances = [addresses[i+1] - addresses[i] for i in range(len(addresses)-1)]
    
    print(f"\nDistances between entries:")
    for d in distances[:10]:
        print(f"  0x{d:X} ({d})")
    
    # Find the most common distance (stride)
    if distances:
        from collections import Counter
        stride_counts = Counter(distances)
        most_common_stride = stride_counts.most_common(5)
        print(f"\nMost common distances (potential strides):")
        for stride, count in most_common_stride:
            print(f"  0x{stride:X} ({stride}) - {count} occurrences")
    
    # Show sample entries
    print(f"\nSample entries found:")
    for c in best_candidates[:5]:
        last_addr = c['last_addr']
        first_addr = c['first_addr']
        
        # Read surrounding context
        context = read_memory(h, last_addr - 50, 150)
        if context:
            # Try to decode as UTF-16
            text = decode_wstring(context)
            print(f"  {c['coach']}: last@0x{last_addr:X}, first@0x{first_addr:X}")
            print(f"    Context: ...{text}...")
    
    return {
        'first_offset': best_candidates[0]['first_addr'] - best_candidates[0]['last_addr'],
        'candidates': best_candidates,
        'distances': distances
    }

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
    
    all_candidates = []
    
    # Search for first 3 coaches to find the pattern
    for first, last in COACHES[:3]:
        print(f"\nSearching for {first} {last}...")
        candidates = scan_for_coach(h, first, last)
        print(f"  Found {len(candidates)} candidates")
        all_candidates.extend(candidates)
    
    if not all_candidates:
        print("\nNo staff entries found! Coaches may have changed or table structure is different.")
        return
    
    print(f"\n{'='*60}")
    print(f"ANALYSIS")
    print(f"{'='*60}")
    
    result = analyze_structure(h, all_candidates)
    
    if result:
        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}")
        print(f"First name offset from last name: {result['first_offset']} (0x{result['first_offset']:X})")
        print(f"Total candidates found: {len(all_candidates)}")
        
        # Try to find stride
        if result['distances']:
            from collections import Counter
            stride = Counter(result['distances']).most_common(1)[0][0]
            print(f"Estimated stride: {stride} (0x{stride:X})")

if __name__ == "__main__":
    main()
