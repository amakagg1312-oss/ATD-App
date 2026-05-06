# Search for play types in memory
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Search for play types
search_strings = [b'Pick & Roll', b'Pick & Fade 3pt', b'Pick & Roll Option', b'Isolation', b'Post Up High']

for search_str in search_strings:
    print(f"Searching for '{search_str.decode()}' in memory...")
    found_count = 0
    
    for base in range(0x24000000, 0x25000000, 0x100000):
        buf = create_string_buffer(0x100000)
        if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
            continue
        raw = buf.raw
        
        idx = raw.find(search_str)
        while idx != -1:
            addr = base + idx
            found_count += 1
            if found_count <= 5:
                print(f"  Found at {hex(addr)}")
                # Read surrounding data
                data = create_string_buffer(100)
                if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr - 20), data, 100, byref(c_size_t(0))):
                    # Look for count=70 nearby
                    for offset in range(0, 100, 4):
                        cnt = struct.unpack('<I', data.raw[offset:offset+4])[0]
                        if cnt == 70:
                            print(f"    count=70 at offset {offset}")
            
            idx = raw.find(search_str, idx + 1)
    
    print(f"  Total: {found_count}")

print("Done searching")
CloseHandle(hproc)
