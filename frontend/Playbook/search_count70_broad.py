# Broader search for count=70 with valid indices
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Search larger range
print("Searching for count=70 with valid plays in 0x23000000-0x25000000...")
for base in range(0x23000000, 0x25000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    
    # Look for count=70
    search_bytes = struct.pack('<I', 70)
    idx = buf.raw.find(search_bytes)
    while idx != -1:
        addr = base + idx
        
        # Check for plays - valid indices should be 1-12506
        plays = []
        for j in range(70):
            offset = idx + 4 + j * 4
            if offset + 4 <= len(buf.raw):
                v = struct.unpack('<I', buf.raw[offset:offset+4])[0]
                if 1 <= v <= 12506:
                    plays.append(v)
        
        if len(plays) >= 50:
            print(f"  Found at {hex(addr)}, valid={len(plays)}")
            print(f"    plays: {plays[:10]}")
        
        # Limit output
        if idx > 0x80000:
            break
        idx = buf.raw.find(search_bytes, idx + 4)

print("Done")
CloseHandle(hproc)