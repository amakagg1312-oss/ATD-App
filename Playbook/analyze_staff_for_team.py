"""Search for team table near staff roster arrays."""

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
    
    # Staff roster arrays are at 0x2A82B17D0, 0x2A82B2DF8, etc.
    # These are pointed to by staff entry at offset 0x018
    
    # The staff entry itself is at 0x2A84DD940 (Nick Nurse)
    # Staff entry has roster pointer at 0x018
    
    # Let's look at the staff entry structure more carefully
    # and see if there's a team reference
    
    staff_base = 0x2A84DD940
    stride = 432
    
    print("Examining staff entries for team references...")
    
    for i in range(5):
        entry_addr = staff_base + (i * stride)
        raw = read_memory(h, entry_addr, stride)
        
        if raw:
            fn = raw[0x50:0x50+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            ln = raw[0x78:0x78+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            
            print(f"\n{fn} {ln} @ 0x{entry_addr:X}:")
            
            # Show all pointers
            for off in range(0, stride, 8):
                val = struct.unpack('<Q', raw[off:off+8])[0]
                if 0x10000000 < val < 0x300000000:
                    # Check what this points to
                    ptr_data = read_memory(h, val, 64)
                    if ptr_data:
                        # Check if it's a roster array (array of pointers to names)
                        ptr_count = 0
                        for j in range(0, 40, 8):
                            inner = struct.unpack('<Q', ptr_data[j:j+8])[0]
                            if 0x10000000 < inner < 0x300000000:
                                inner_data = read_memory(h, inner, 40)
                                if inner_data:
                                    inner_name = inner_data.decode('utf-16-le', errors='ignore').split('\x00')[0]
                                    if inner_name and 2 < len(inner_name) < 20:
                                        ptr_count += 1
                        
                        if ptr_count > 5:
                            print(f"  [{off:03X}] 0x{val:X} -> ROSTER ARRAY ({ptr_count} players)")
                        else:
                            # Check for other patterns
                            floats = []
                            for j in range(0, 32, 4):
                                f = struct.unpack('<f', ptr_data[j:j+4])[0]
                                if 0.0 < f < 100.0:
                                    floats.append(f)
                            
                            if len(floats) > 5:
                                print(f"  [{off:03X}] 0x{val:X} -> FLOATS: {floats[:6]}")
                            else:
                                # Check for team ID or other data
                                dwords = []
                                for j in range(0, 32, 4):
                                    d = struct.unpack('<I', ptr_data[j:j+4])[0]
                                    if 0 < d < 1000:
                                        dwords.append(d)
                                
                                if len(dwords) > 3:
                                    print(f"  [{off:03X}] 0x{val:X} -> DWORDS: {dwords[:8]}")

if __name__ == "__main__":
    main()
