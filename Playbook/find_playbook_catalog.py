"""Search for global playbook catalog using staff playbook indices."""

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

def main():
    pid = find_process()
    if not pid:
        print("NBA2K26.exe not running!")
        return
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    # Staff playbook indices (at 0x0B8, 0x0BA, 0x0BC, etc.)
    # Nick Nurse: 138, 137, 136, 135, 134, 133, 132
    # Doc Rivers: 25, 24, 23, ... 0
    # Billy Donovan: 131, 130, ... 122
    # Kenny Atkinson: 180, 179, 178, 177, 176
    # Joe Mazzulla: 169, 168, 167
    
    # Strategy: Search for a table where entry size * index + base = valid pointer
    # Try different entry sizes
    
    print("Searching for playbook catalog table...")
    print(f"{'='*80}")
    
    # Read all staff playbook indices
    table_base = 0x2A84DD940
    stride = 432
    
    staff_playbooks = {}
    for i in range(5):
        entry_addr = table_base + (i * stride)
        raw = read_memory(h, entry_addr, stride)
        if raw:
            fn = raw[0x50:0x50+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            ln = raw[0x78:0x78+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            
            indices = []
            for off in range(0x0B8, 0x0F0, 2):
                val = struct.unpack('<H', raw[off:off+2])[0]
                if val != 0xFFFF:
                    indices.append(val)
            
            staff_playbooks[f"{fn} {ln}"] = indices
    
    print("Staff playbook indices:")
    for name, indices in staff_playbooks.items():
        print(f"  {name}: {indices[:5]}{'...' if len(indices) > 5 else ''}")
    
    # Now search for a catalog table
    # The catalog should have entries for IDs 0-180+
    # Try to find a table by searching for pointers that could be playbook entries
    
    # First, let's look at what's at the pointer in staff entry at 0x008
    # This might be related to playbook assignments
    
    print(f"\nAnalyzing staff entry pointer at 0x008...")
    for i in range(5):
        entry_addr = table_base + (i * stride)
        raw = read_memory(h, entry_addr, stride)
        if raw:
            fn = raw[0x50:0x50+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            ln = raw[0x78:0x78+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            
            ptr = struct.unpack('<Q', raw[0x08:0x10])[0]
            print(f"\n{fn} {ln}: ptr@0x08 = 0x{ptr:X}")
            
            # Read data at this pointer
            data = read_memory(h, ptr, 512)
            if data:
                # This looks like a byte array with 0x7F values
                # Could be playbook assignments or permissions
                # Let's look for patterns
                non_7f = []
                for off in range(min(len(data), 300)):
                    if data[off] != 0x7F:
                        non_7f.append((off, data[off]))
                
                if non_7f:
                    print(f"  Non-0x7F values ({len(non_7f)}):")
                    for off, val in non_7f[:20]:
                        print(f"    [{off}] = 0x{val:X} ({val})")
    
    # Search for playbook catalog by looking for a table with ~200 entries
    # Each entry might be 8-64 bytes
    
    print(f"\n{'='*80}")
    print("Searching for playbook catalog in memory...")
    
    # Look for a region with many pointers (potential catalog)
    mbr = MBI()
    addr = 0
    regions = 0
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                # Count pointers in this region
                ptr_count = 0
                for i in range(0, min(len(buf), 0x10000) - 8, 8):
                    val = struct.unpack('<Q', buf[i:i+8])[0]
                    if 0x10000000 < val < 0x300000000:
                        ptr_count += 1
                
                # If many pointers, this could be a catalog
                if ptr_count > 50:
                    # Check if it has ~200 consecutive pointers
                    consecutive = 0
                    max_consecutive = 0
                    start_offset = 0
                    
                    for i in range(0, min(len(buf), 0x10000) - 8, 8):
                        val = struct.unpack('<Q', buf[i:i+8])[0]
                        if 0x10000000 < val < 0x300000000:
                            if consecutive == 0:
                                start_offset = i
                            consecutive += 1
                            max_consecutive = max(max_consecutive, consecutive)
                        else:
                            consecutive = 0
                    
                    if max_consecutive > 100:
                        print(f"\n  Potential catalog at 0x{mbr.BaseAddress + start_offset:X}")
                        print(f"    {max_consecutive} consecutive pointers")
                        
                        # Show first 10 pointers
                        for j in range(min(10, max_consecutive)):
                            ptr = struct.unpack('<Q', buf[start_offset + j*8:start_offset + j*8 + 8])[0]
                            # Read data at pointer
                            pb_data = read_memory(h, ptr, 64)
                            if pb_data:
                                # Try to find string
                                try:
                                    text = pb_data[:40].decode('utf-16-le', errors='ignore')
                                    printable = ''.join(c if c.isprintable() else '.' for c in text)
                                    if len([c for c in printable if c.isalpha()]) > 3:
                                        print(f"    [{j}] 0x{ptr:X} -> {printable[:30]}")
                                    else:
                                        hex_str = ' '.join(f'{b:02X}' for b in pb_data[:16])
                                        print(f"    [{j}] 0x{ptr:X} -> {hex_str}")
                                except:
                                    hex_str = ' '.join(f'{b:02X}' for b in pb_data[:16])
                                    print(f"    [{j}] 0x{ptr:X} -> {hex_str}")
            
            regions += 1
            if regions % 2000 == 0:
                print(f"  Scanned {regions} regions...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print("\nDone!")

if __name__ == "__main__":
    main()
