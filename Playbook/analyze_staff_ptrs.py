"""Analyze all pointers in staff entry to find playbook reference."""

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
    
    # Read first staff entry
    raw = read_memory(h, table_base, stride)
    
    print("All 64-bit values in staff entry that look like pointers:")
    print(f"{'='*80}")
    
    for off in range(0, stride, 8):
        val = struct.unpack('<Q', raw[off:off+8])[0]
        if 0x10000000 < val < 0x300000000:
            # Read data at this pointer
            data = read_memory(h, val, 128)
            if data:
                # Try to identify what this pointer points to
                # Check for strings
                try:
                    text = data[:60].decode('utf-16-le', errors='ignore')
                    printable = ''.join(c if c.isprintable() else '.' for c in text)
                    if len([c for c in printable if c.isalpha()]) > 5:
                        print(f"  [{off:03X}] 0x{val:X} -> STRING: {printable[:40]}")
                        continue
                except:
                    pass
                
                # Check for array of pointers
                ptr_count = 0
                for i in range(0, 64, 8):
                    inner = struct.unpack('<Q', data[i:i+8])[0]
                    if 0x10000000 < inner < 0x300000000:
                        ptr_count += 1
                
                if ptr_count > 3:
                    print(f"  [{off:03X}] 0x{val:X} -> POINTER ARRAY ({ptr_count} pointers)")
                    # Show first few pointers
                    for i in range(min(ptr_count, 5)):
                        inner = struct.unpack('<Q', data[i*8:i*8+8])[0]
                        inner_data = read_memory(h, inner, 40)
                        if inner_data:
                            try:
                                inner_text = inner_data[:30].decode('utf-16-le', errors='ignore')
                                inner_printable = ''.join(c if c.isprintable() else '.' for c in inner_text)
                                print(f"    [{i}] 0x{inner:X} -> {inner_printable[:25]}")
                            except:
                                print(f"    [{i}] 0x{inner:X}")
                    continue
                
                # Check for float data
                floats = []
                for i in range(0, 32, 4):
                    f = struct.unpack('<f', data[i:i+4])[0]
                    if 0.0 < f < 100.0:
                        floats.append(f)
                
                if len(floats) > 5:
                    print(f"  [{off:03X}] 0x{val:X} -> FLOATS: {floats[:8]}")
                    continue
                
                # Check for integer array
                ints = []
                for i in range(0, 32, 4):
                    d = struct.unpack('<I', data[i:i+4])[0]
                    if 0 < d < 1000:
                        ints.append(d)
                
                if len(ints) > 5:
                    print(f"  [{off:03X}] 0x{val:X} -> INTS: {ints[:10]}")
                    continue
                
                # Default: show hex
                hex_str = ' '.join(f'{b:02X}' for b in data[:32])
                print(f"  [{off:03X}] 0x{val:X} -> DATA: {hex_str}")

if __name__ == "__main__":
    main()
