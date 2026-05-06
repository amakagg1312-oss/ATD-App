"""Follow staff entry pointers to find playbook data."""

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
    
    # Read first 5 staff entries
    print("Following pointers in staff entries...")
    print(f"{'='*80}")
    
    for i in range(5):
        entry_addr = table_base + (i * stride)
        raw = read_memory(h, entry_addr, stride)
        
        if raw:
            first_name = raw[0x50:0x50+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            last_name = raw[0x78:0x78+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            
            print(f"\n{first_name} {last_name}:")
            
            # Key pointers to follow
            pointer_offsets = [0x000, 0x008, 0x018, 0x028, 0x108, 0x110]
            
            for off in pointer_offsets:
                ptr = struct.unpack('<Q', raw[off:off+8])[0]
                if 0x10000000 < ptr < 0x300000000:
                    print(f"  Pointer at 0x{off:03X}: 0x{ptr:X}")
                    
                    # Read data at pointer
                    data = read_memory(h, ptr, 256)
                    if data:
                        # Try to interpret as string
                        try:
                            text = data[:100].decode('utf-16-le', errors='ignore').split('\x00')[0]
                            if text and len(text) > 2 and all(c.isprintable() for c in text[:20]):
                                print(f"    String: {text[:50]}")
                        except:
                            pass
                        
                        # Show first 64 bytes as hex
                        hex_lines = []
                        for j in range(0, 64, 16):
                            chunk = data[j:j+16]
                            hex_str = ' '.join(f'{b:02X}' for b in chunk)
                            hex_lines.append(f"    [{j:03X}] {hex_str}")
                        print(f"    Data:\n" + '\n'.join(hex_lines))
    
    # Now look at the playbook index region (0x0B8-0x0EC)
    print(f"\n{'='*80}")
    print("Playbook index region (0x0B8-0x0EC):")
    print(f"{'='*80}")
    
    for i in range(5):
        entry_addr = table_base + (i * stride)
        raw = read_memory(h, entry_addr, stride)
        
        if raw:
            first_name = raw[0x50:0x50+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            last_name = raw[0x78:0x78+80].decode('utf-16-le', errors='ignore').split('\x00')[0]
            
            print(f"\n{first_name} {last_name}:")
            
            # Read playbook indices as 16-bit values
            for off in range(0x0B8, 0x0F0, 2):
                val = struct.unpack('<H', raw[off:off+2])[0]
                if val != 0xFFFF:
                    print(f"  [{off:03X}] = {val} (0x{val:X})")

if __name__ == "__main__":
    main()
