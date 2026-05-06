"""Look for playbook pointers in staff structures."""

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

def find_staff_base(h):
    """Find the Steelers string and calculate staff base."""
    mbr = MBI()
    addr = 0
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf and b'Pittsburgh Steelers' in buf:
                offset = buf.find(b'Pittsburgh Steelers')
                # Based on prior discovery: staff base = address - 0x50
                return mbr.BaseAddress + offset - 0x50
        
        addr = mbr.BaseAddress + mbr.RegionSize
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
    
    # Find staff base
    staff_base = find_staff_base(h)
    if not staff_base:
        print("Could not find staff base!")
        return
    
    print(f"Staff Base: 0x{staff_base:X}")
    
    # Known play offsets from all_play_names.txt (we'll use a few)
    known_offsets = [
        0x3E02CE,  # FIST DELAY 2
        0x3E02EA,  # FIST DELAY 3
        0x3E030A,  # FIST DELAY 4
        0x3E022E,  # FIST STAGGER 1
        0x3E024A,  # FIST STAGGER 2
        0x3E0266,  # FIST STAGGER 3
    ]
    
    # Also, we know from earlier search that some memory regions contain these offsets
    # We'll also check for the candidate regions we found: 0x2BEFF9000, 0x2D5E50000, 0x2E1850000, 0x7FFCC01F1000, 0x7FFD9ECDB000
    candidate_regions = [
        0x2BEFF9000,
        0x2D5E50000,
        0x2E1850000,
        0x7FFCC01F1000,
        0x7FFD9ECDB000
    ]
    
    print("\nSearching staff structures for playbook pointers...")
    print(f"Checking {min(50, 200)} staff members (stride=432)")
    
    stride = 432
    max_staff = 50  # Check first 50 staff members
    
    for i in range(max_staff):
        staff_addr = staff_base + i * stride
        staff_data = read_memory(h, staff_addr, stride)
        if not staff_data:
            continue
        
        # Look for 8-byte pointers (64-bit) in the staff data
        for j in range(0, stride - 7, 8):  # Step by 8 for 8-byte values
            ptr_bytes = staff_data[j:j+8]
            if len(ptr_bytes) < 8:
                continue
            ptr = struct.unpack('<Q', ptr_bytes)[0]
            
            # Check if ptr looks like a valid pointer (in user space range)
            if ptr < 0x100000000 or ptr > 0x7FFFFFFFFFFF:
                continue
            
            # Now, read a small block from this pointer to see if it contains known offsets
            # We'll read 0x1000 bytes
            block = read_memory(h, ptr, 0x1000)
            if not block:
                continue
            
            # Check if any of the known offsets appear as 4-byte little-endian values in this block
            found_known = False
            for off in known_offsets:
                off_bytes = struct.pack('<I', off)  # 4-byte little-endian
                if off_bytes in block:
                    found_known = True
                    break
            
            # Also check if the pointer itself points to one of our candidate regions
            points_to_candidate = False
            for cand in candidate_regions:
                if ptr == cand:
                    points_to_candidate = True
                    break
            
            if found_known or points_to_candidate:
                print(f"\n*** Found candidate at staff member {i} ***")
                print(f"  Staff address: 0x{staff_addr:X}")
                print(f"  Pointer offset in staff: 0x{j:X}")
                print(f"  Pointer value: 0x{ptr:X}")
                if found_known:
                    print(f"  -> Points to memory containing known play offset")
                if points_to_candidate:
                    print(f"  -> Points to known candidate region: 0x{ptr:X}")
                
                # Let's look at a bit more context around the pointer in the staff
                ctx_start = max(0, j - 16)
                ctx_end = min(stride, j + 24)
                ctx = staff_data[ctx_start:ctx_end]
                print(f"  Context around pointer: {ctx.hex()}")
                
                # Try to read a string from the pointer (if it's a string block)
                # We'll try to read 0x100 bytes and see if we can find any ASCII
                str_block = read_memory(h, ptr, 0x100)
                if str_block:
                    # Look for any ASCII strings of length >= 4
                    ascii_parts = []
                    current = []
                    for b in str_block:
                        if 32 <= b <= 126:  # Printable ASCII
                            current.append(chr(b))
                        else:
                            if len(current) >= 4:
                                ascii_parts.append(''.join(current))
                            current = []
                    if len(current) >= 4:
                        ascii_parts.append(''.join(current))
                    if ascii_parts:
                        print(f"  ASCII strings found: {ascii_parts[:5]}")
    
    print("\nDone.")

if __name__ == "__main__":
    main()
