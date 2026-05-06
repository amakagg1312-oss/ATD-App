# Search for count=70 in wider memory range
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

print("Searching for count=70 in wider memory range...")
found = 0

for base in range(0x23000000, 0x26000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    raw = buf.raw
    
    # Search for count=70
    search_bytes = struct.pack('<I', 70)
    idx = raw.find(search_bytes)
    while idx != -1:
        addr = base + idx
        found += 1
        
        # Read surrounding data
        data = create_string_buffer(300)
        if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr - 20), data, 300, byref(c_size_t(0))):
            # Check if this looks like a playbook structure
            # Read 70 uint32 values after the count
            plays = []
            for j in range(70):
                offset = 20 + j * 4
                if offset + 4 <= 300:
                    v = struct.unpack('<I', data.raw[offset:offset+4])[0]
                    plays.append(v)
            
            valid = sum(1 for p in plays if 1 <= p <= 12506)
            if valid >= 30:  # At least 30 valid play indices
                print(f"  {hex(addr)}: count=70, valid={valid}")
                print(f"    first 10: {plays[:10]}")
                print(f"    last 5: {plays[-5:]}")
        
        if found >= 100:
            break
        idx = raw.find(search_bytes, idx + 1)

print(f"Total count=70 occurrences: {found}")
CloseHandle(hproc)
