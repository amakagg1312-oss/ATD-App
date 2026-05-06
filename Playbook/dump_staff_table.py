"""Dump full staff table and find base pointer."""

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
        ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", ctypes.c_uint32),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
    ]

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
    
    # Known staff table base
    table_base = 0x2A84DD940
    stride = 432
    first_off = 0x50
    last_off = 0x78
    name_len = 40
    
    # Dump all staff entries
    print(f"\n{'='*60}")
    print(f"STAFF TABLE DUMP (base=0x{table_base:X}, stride={stride})")
    print(f"{'='*60}")
    
    staff_entries = []
    empty_count = 0
    
    for i in range(50):  # NBA has 30 teams + assistants
        addr = table_base + (i * stride)
        first_buf = read_memory(h, addr + first_off, name_len * 2)
        last_buf = read_memory(h, addr + last_off, name_len * 2)
        
        if first_buf and last_buf:
            fn = decode_wstring(first_buf, name_len)
            ln = decode_wstring(last_buf, name_len)
            
            if fn and ln and len(fn) > 1:
                print(f"  [{i:2d}] 0x{addr:X}: {fn} {ln}")
                staff_entries.append({'index': i, 'first': fn, 'last': ln, 'address': addr})
                empty_count = 0
            else:
                empty_count += 1
                if empty_count >= 5:
                    print(f"  ... (empty entries, stopping)")
                    break
        else:
            empty_count += 1
            if empty_count >= 5:
                print(f"  ... (unreadable, stopping)")
                break
    
    # Try to find the base pointer
    print(f"\n{'='*60}")
    print(f"SEARCHING FOR BASE POINTER")
    print(f"{'='*60}")
    
    # The base pointer should point to table_base
    # Search in the known pointer region (around 0x7E1F878 from old offsets)
    old_ptr = 0x7E1F878  # 132244312
    
    # Read around the old pointer location
    for offset in range(-100, 100, 8):
        ptr_addr = old_ptr + offset
        ptr_buf = read_memory(h, ptr_addr, 8)
        if ptr_buf:
            ptr_val = int.from_bytes(ptr_buf, 'little')
            if ptr_val == table_base:
                print(f"  Found pointer at 0x{ptr_addr:X} -> 0x{table_base:X}")
    
    # Also search in the known pointer region for any pointer to our table
    print(f"\nSearching pointer region (0x7E1F000 - 0x7E20000)...")
    for addr in range(0x7E1F000, 0x7E20000, 8):
        ptr_buf = read_memory(h, addr, 8)
        if ptr_buf:
            ptr_val = int.from_bytes(ptr_buf, 'little')
            if ptr_val == table_base:
                print(f"  Found pointer at 0x{addr:X} -> 0x{table_base:X}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Staff table base: 0x{table_base:X}")
    print(f"Stride: {stride} (0x{stride:X})")
    print(f"First name offset: 0x{first_off:X} ({first_off})")
    print(f"Last name offset: 0x{last_off:X} ({last_off})")
    print(f"Name length: {name_len}")
    print(f"Total staff entries: {len(staff_entries)}")

if __name__ == "__main__":
    main()
