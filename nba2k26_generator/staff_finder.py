"""Dynamic staff table finder for NBA 2K26.

Finds the staff table base address at runtime by searching for known coach names.
Returns the table base address which can be used with the known offsets:
- Stride: 432
- First Name Offset: 0x50 (80)
- Last Name Offset: 0x78 (120)
- Name Length: 40
"""

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

# Staff table configuration
STAFF_STRIDE = 432
STAFF_FIRST_OFFSET = 0x50
STAFF_LAST_OFFSET = 0x78
STAFF_NAME_LENGTH = 40

# Known head coaches (2025-26 season)
HEAD_COACHES = [
    ("Nick", "Nurse"),
    ("Doc", "Rivers"),
    ("Joe", "Mazzulla"),
    ("Tyronn", "Lue"),
    ("Billy", "Donovan"),
    ("Kenny", "Atkinson"),
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

def find_process(exe_name='NBA2K26.exe'):
    for p in psutil.process_iter():
        if exe_name.lower() in p.name().lower():
            return p.pid
    return None

def find_staff_table(h=None, pid=None):
    """Find the staff table base address.
    
    Args:
        h: Process handle (optional, will open if not provided)
        pid: Process ID (optional, will find if not provided)
    
    Returns:
        tuple: (table_base_address, process_handle) or (None, None) if not found
    """
    close_handle = False
    
    if pid is None:
        pid = find_process()
        if pid is None:
            print("NBA2K26.exe not running!")
            return None, None
    
    if h is None:
        h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
        if not h:
            print("Failed to open process!")
            return None, None
        close_handle = True
    
    # Search for Nick Nurse
    first_bytes = encode_wstring("Nick")
    last_bytes = encode_wstring("Nurse")
    
    mbr = MBI()
    addr = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x2000000))
            if buf:
                idx = buf.find(first_bytes)
                while idx >= 0:
                    entry_base = mbr.BaseAddress + idx - STAFF_FIRST_OFFSET
                    last_addr = entry_base + STAFF_LAST_OFFSET
                    
                    # Verify last name
                    last_buf = read_memory(h, last_addr, len(last_bytes) + 10)
                    if last_buf and last_buf[:len(last_bytes)] == last_bytes:
                        # Verify next entry is also a coach
                        next_entry = entry_base + STAFF_STRIDE
                        next_first = read_memory(h, next_entry + STAFF_FIRST_OFFSET, 60)
                        next_last = read_memory(h, next_entry + STAFF_LAST_OFFSET, 60)
                        
                        if next_first and next_last:
                            nfn = decode_wstring(next_first, 20)
                            nln = decode_wstring(next_last, 20)
                            
                            # Check if next entry is a known coach
                            for first, last in HEAD_COACHES[1:]:
                                if first.lower() in nfn.lower() and last.lower() in nln.lower():
                                    return entry_base, h
                    
                    idx = buf.find(first_bytes, idx + 2)
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    if close_handle and h:
        kernel.CloseHandle(h)
    return None, None

def list_staff(h=None, pid=None, table_base=None, max_entries=50):
    """List all staff members.
    
    Args:
        h: Process handle
        pid: Process ID
        table_base: Staff table base address (will find if not provided)
        max_entries: Maximum entries to read
    
    Returns:
        list: List of dicts with 'first', 'last', 'address' keys
    """
    close_handle = False
    
    if table_base is None:
        table_base, h = find_staff_table(h, pid)
        if table_base is None:
            return []
    
    if h is None:
        if pid is None:
            pid = find_process()
        if pid:
            h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
            close_handle = True
    
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
                staff_list.append({
                    'index': i,
                    'first': fn,
                    'last': ln,
                    'address': addr
                })
                empty_count = 0
            else:
                empty_count += 1
                if empty_count >= 5:
                    break
        else:
            empty_count += 1
            if empty_count >= 5:
                break
    
    if close_handle and h:
        kernel.CloseHandle(h)
    
    return staff_list

if __name__ == "__main__":
    print("Finding staff table...")
    table_base, h = find_staff_table()
    
    if table_base:
        print(f"Staff table base: 0x{table_base:X}")
        print(f"\nStaff members:")
        staff = list_staff(h=h, table_base=table_base)
        for s in staff:
            print(f"  [{s['index']:2d}] 0x{s['address']:X}: {s['first']} {s['last']}")
        kernel.CloseHandle(h)
    else:
        print("Staff table not found!")
