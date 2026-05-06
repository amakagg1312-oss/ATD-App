# Search for specific Lakers play indices in memory
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

print(f"Searching for Lakers play indices in memory...")

for play_idx in lal_indices[:5]:  # Search for first 5
    search_bytes = struct.pack('<I', play_idx)
    print(f"  Searching for {play_idx}...")
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
                # Read surrounding data
                data = create_string_buffer(100)
                if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr - 20), data, 100, byref(c_size_t(0))):
                    # Show context
                    vals = []
                    for j in range(0, 100, 4):
                        v = struct.unpack('<I', data.raw[j:j+4])[0]
                        vals.append(v)
                    print(f"      context: {vals[:10]}")
            
            idx = raw.find(search_bytes, idx + 1)
    
    print(f"    Total: {found_count}")

print("Done searching")
CloseHandle(hproc)
