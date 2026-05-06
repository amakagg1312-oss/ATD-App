"""Fast staff table finder - searches for Nick Nurse with staff offsets."""

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil

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
    
    stride = 432
    
    # Test pattern 1: Staff offsets (first@0x50, last@0x78)
    print("\nSearching for Nick Nurse with staff offsets (first@0x50, last@0x78)...")
    
    first_bytes = encode_wstring("Nick")
    last_bytes = encode_wstring("Nurse")
    
    first_off = 0x50
    last_off = 0x78
    name_len = 40
    
    hits = []
    mbr = MBI()
    addr = 0
    regions_scanned = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = create_string_buffer(mbr.RegionSize)
            if kernel.ReadProcessMemory(h, ctypes.c_void_p(mbr.BaseAddress), buf, mbr.RegionSize, byref(c_size_t(0))):
                raw = buf.raw
                
                # Search for "Nick"
                idx = raw.find(first_bytes)
                while idx >= 0:
                    entry_base = mbr.BaseAddress + idx - first_off
                    last_addr = entry_base + last_off
                    
                    # Check last name
                    last_buf = read_memory(h, last_addr, len(last_bytes) + 10)
                    if last_buf and last_buf[:len(last_bytes)] == last_bytes:
                        hits.append(entry_base)
                    
                    idx = raw.find(first_bytes, idx + 2)
            
            regions_scanned += 1
            if regions_scanned % 1000 == 0:
                print(f"  Scanned {regions_scanned} regions, found {len(hits)} hits...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"Found {len(hits)} hits")
    
    if hits:
        # Verify and show results
        for hit in hits[:5]:
            # Read entry
            first_buf = read_memory(h, hit + first_off, name_len * 2)
            last_buf = read_memory(h, hit + last_off, name_len * 2)
            
            if first_buf and last_buf:
                fn = decode_wstring(first_buf, name_len)
                ln = decode_wstring(last_buf, name_len)
                print(f"\n  Entry at 0x{hit:X}: {fn} {ln}")
                
                # Check next 4 entries
                for i in range(1, 5):
                    next_addr = hit + (i * stride)
                    nfirst = read_memory(h, next_addr + first_off, name_len * 2)
                    nlast = read_memory(h, next_addr + last_off, name_len * 2)
                    if nfirst and nlast:
                        nfn = decode_wstring(nfirst, name_len)
                        nln = decode_wstring(nlast, name_len)
                        if nfn and nln and len(nfn) > 1:
                            print(f"    +{i}: {nfn} {nln}")

if __name__ == "__main__":
    main()
