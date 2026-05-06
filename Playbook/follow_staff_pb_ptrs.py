"""Follow the playbook pointer array at staff offset 0x018."""

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
    
    table_base = 0x2A84DD940
    stride = 432
    
    # For each coach, follow the pointer array at 0x018
    print("Following playbook pointer arrays at staff offset 0x018")
    print(f"{'='*80}")
    
    for i in range(5):
        entry_addr = table_base + (i * stride)
        raw = read_memory(h, entry_addr, stride)
        
        if raw:
            first_name = raw[0x50:0x50+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            last_name = raw[0x78:0x78+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            
            # Get pointer array address
            ptr_array_addr = struct.unpack('<Q', raw[0x18:0x20])[0]
            
            print(f"\n{first_name} {last_name}:")
            print(f"  Pointer array at: 0x{ptr_array_addr:X}")
            
            # Read the pointer array (each entry is 8 bytes)
            # Read first 20 pointers
            array_data = read_memory(h, ptr_array_addr, 20 * 8)
            if array_data:
                for j in range(20):
                    ptr = struct.unpack('<Q', array_data[j*8:j*8+8])[0]
                    if ptr == 0:
                        print(f"    [{j}] 0x0 (end of array)")
                        break
                    
                    if 0x10000000 < ptr < 0x300000000:
                        # Read data at this pointer
                        pb_data = read_memory(h, ptr, 64)
                        if pb_data:
                            # Check if it looks like playbook data
                            # Look for strings or known patterns
                            first_dword = struct.unpack('<I', pb_data[:4])[0]
                            second_dword = struct.unpack('<I', pb_data[4:8])[0]
                            
                            # Try to find a string
                            try:
                                text = pb_data[:40].decode('utf-16-le', errors='ignore')
                                printable = ''.join(c for c in text if c.isprintable() or c == '\x00')
                                if len(printable) > 5:
                                    print(f"    [{j}] 0x{ptr:X} -> text: {printable[:30]}")
                                else:
                                    print(f"    [{j}] 0x{ptr:X} -> D0:0x{first_dword:X} D1:0x{second_dword:X}")
                            except:
                                print(f"    [{j}] 0x{ptr:X} -> D0:0x{first_dword:X} D1:0x{second_dword:X}")
                        else:
                            print(f"    [{j}] 0x{ptr:X} (unreadable)")
                    else:
                        print(f"    [{j}] 0x{ptr:X} (invalid)")

if __name__ == "__main__":
    main()
