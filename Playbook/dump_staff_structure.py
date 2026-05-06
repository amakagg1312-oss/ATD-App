"""Dump full staff entry structure to find playbook references."""

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

def main():
    pid = find_process()
    if not pid:
        print("NBA2K26.exe not running!")
        return
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    # Staff table config
    table_base = 0x2A84DD940
    stride = 432
    
    # Dump first 3 staff entries as raw hex
    print(f"Dumping staff entry structure (stride={stride})")
    print(f"{'='*80}")
    
    for i in range(3):
        entry_addr = table_base + (i * stride)
        raw = read_memory(h, entry_addr, stride)
        
        if raw:
            # Read names
            first_name = raw[0x50:0x50+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            last_name = raw[0x78:0x78+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            
            print(f"\nEntry {i}: {first_name} {last_name} @ 0x{entry_addr:X}")
            print(f"{'-'*80}")
            
            # Dump as 16-byte rows with offsets
            for offset in range(0, stride, 16):
                chunk = raw[offset:offset+16]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                
                # Try to interpret as different types
                if len(chunk) >= 8:
                    qword = struct.unpack('<Q', chunk[:8])[0]
                    dword = struct.unpack('<I', chunk[:4])[0]
                    word = struct.unpack('<H', chunk[:2])[0]
                    byte = chunk[0]
                    
                    # Mark potential pointers (values in pointer range)
                    marker = ""
                    if 0x10000000 < qword < 0x300000000:
                        marker = " <-- POINTER?"
                    elif 0x10000000 < dword < 0x300000000:
                        marker = " <-- DWORD PTR?"
                    
                    print(f"  [{offset:03X}] {hex_str:<48} Q:0x{qword:016X} D:0x{dword:08X} W:0x{word:04X} B:0x{byte:02X}{marker}")
    
    print(f"\n{'='*80}")
    print("Looking for playbook-related patterns...")
    
    # Compare entries to find differences that might be playbook IDs
    print(f"\nComparing first 5 entries for playbook indices:")
    
    entries_data = []
    for i in range(5):
        entry_addr = table_base + (i * stride)
        raw = read_memory(h, entry_addr, stride)
        if raw:
            entries_data.append(raw)
    
    # Find offsets where values differ between entries
    print(f"\nOffsets with different values between entries:")
    for offset in range(0, stride, 4):
        values = []
        for raw in entries_data:
            val = struct.unpack('<I', raw[offset:offset+4])[0]
            values.append(val)
        
        # Check if values differ
        if len(set(values)) > 1:
            # Show all values
            names = []
            for raw in entries_data:
                fn = raw[0x50:0x50+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
                ln = raw[0x78:0x78+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
                names.append(f"{fn} {ln}")
            
            print(f"  Offset 0x{offset:03X}: {', '.join(f'{names[j]}=0x{values[j]:X}' for j in range(len(values)))}")

if __name__ == "__main__":
    main()
