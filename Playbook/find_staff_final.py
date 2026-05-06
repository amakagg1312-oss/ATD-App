"""Improved staff table finder with better verification."""

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
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_uint32),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
    ]

STAFF_STRIDE = 432
STAFF_FIRST_OFFSET = 0x50
STAFF_LAST_OFFSET = 0x78
STAFF_NAME_LENGTH = 40

def read_memory(h, addr, size):
    buf = create_string_buffer(size)
    if kernel.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

def decode_wstring(data, max_chars=30):
    try:
        raw = data[:max_chars*2]
        return raw.decode('utf-16-le', errors='ignore').split('\x00')[0].strip()
    except:
        return ""

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p.pid
    return None

def find_staff_table():
    pid = find_process()
    if not pid:
        print("NBA2K26.exe not running!")
        return None
    
    print(f"PID: {pid}")
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return None
    
    # Search for "Nurse" (more unique than "Nick")
    nurse_bytes = b'N\x00u\x00r\x00s\x00e\x00\x00\x00'
    nick_bytes = b'N\x00i\x00c\x00k\x00\x00\x00'
    
    print("Searching for staff table...")
    
    mbr = MBI()
    addr = 0
    regions = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x2000000))
            if buf:
                # Search for "Nurse"
                idx = buf.find(nurse_bytes)
                while idx >= 0:
                    last_addr = mbr.BaseAddress + idx
                    # Calculate entry base from last name offset
                    entry_base = last_addr - STAFF_LAST_OFFSET
                    first_addr = entry_base + STAFF_FIRST_OFFSET
                    
                    # Verify first name is "Nick"
                    first_buf = read_memory(h, first_addr, len(nick_bytes))
                    if first_buf and first_buf == nick_bytes:
                        # Verify next entry is a valid coach
                        next_entry = entry_base + STAFF_STRIDE
                        next_first = read_memory(h, next_entry + STAFF_FIRST_OFFSET, 60)
                        next_last = read_memory(h, next_entry + STAFF_LAST_OFFSET, 60)
                        
                        if next_first and next_last:
                            nfn = decode_wstring(next_first, 20)
                            nln = decode_wstring(next_last, 20)
                            
                            # Check if it looks like a valid name
                            if nfn and nln and len(nfn) > 1 and len(nln) > 1:
                                print(f"Found staff table at 0x{entry_base:X}")
                                print(f"  Entry 0: Nick Nurse")
                                print(f"  Entry 1: {nfn} {nln}")
                                kernel.CloseHandle(h)
                                return entry_base
                    
                    idx = buf.find(nurse_bytes, idx + 2)
            
            regions += 1
            if regions % 1000 == 0:
                print(f"  Scanned {regions} regions...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    kernel.CloseHandle(h)
    return None

def list_staff(table_base, max_entries=50):
    pid = find_process()
    if not pid:
        return []
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        return []
    
    staff_list = []
    empty_count = 0
    
    for i in range(max_entries):
        addr = table_base + (i * STAFF_STRIDE)
        first_buf = read_memory(h, addr + STAFF_FIRST_OFFSET, STAFF_NAME_LENGTH * 2)
        last_buf = read_memory(h, addr + STAFF_LAST_OFFSET, STAFF_NAME_LENGTH * 2)
        
        if first_buf and last_buf:
            fn = decode_wstring(first_buf, STAFF_NAME_LENGTH)
            ln = decode_wstring(last_buf, STAFF_NAME_LENGTH)
            
            if fn and ln and len(fn) > 1:
                staff_list.append({'index': i, 'first': fn, 'last': ln, 'address': addr})
                empty_count = 0
            else:
                empty_count += 1
                if empty_count >= 5:
                    break
        else:
            empty_count += 1
            if empty_count >= 5:
                break
    
    kernel.CloseHandle(h)
    return staff_list

if __name__ == "__main__":
    table_base = find_staff_table()
    
    if table_base:
        print(f"\nStaff table base: 0x{table_base:X}")
        print(f"\nStaff members:")
        staff = list_staff(table_base)
        for s in staff:
            print(f"  [{s['index']:2d}] 0x{s['address']:X}: {s['first']} {s['last']}")
    else:
        print("\nStaff table not found!")
