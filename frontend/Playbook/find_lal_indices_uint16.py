# Search for Lakers play indices as uint16 in memory
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Known Lakers play indices
lal_indices = [7849, 7876, 7850, 7878, 8068, 7772, 7831, 7896, 7899, 7941, 9237, 7962, 7964, 9238, 9241, 9244]

print(f"Searching for Lakers play indices as uint16 in memory...")

for play_idx in lal_indices[:3]:  # Search for first 3
    search_bytes = struct.pack('<H', play_idx)
    print(f"  Searching for {play_idx} as uint16...")
    found_count = 0
    
    for base in range(0x24000000, 0x25000000, 0x100000):
        buf = create_string_buffer(0x100000)
        if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
            continue
        raw = buf.raw
        
        idx = raw.find(search_bytes)
        while idx != -1:
            addr = base + idx
            found_count += 1
            if found_count <= 3:
                print(f"    Found at {hex(addr)}")
                # Read surrounding data as uint16
                data = create_string_buffer(100)
                if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr - 20), data, 100, byref(c_size_t(0))):
                    # Show context as uint16
                    vals = []
                    for j in range(0, 100, 2):
                        v = struct.unpack('<H', data.raw[j:j+2])[0]
                        vals.append(v)
                    print(f"      context (uint16): {vals[:20]}")
            
            idx = raw.find(search_bytes, idx + 1)
    
    print(f"    Total: {found_count}")

print("Done searching")
CloseHandle(hproc)
