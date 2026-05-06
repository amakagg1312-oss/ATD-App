# Search memory for Lakers playbook by searching for sequence of known play indices
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Known Lakers play indices - search for first 3 as a sequence
# 7849, 7876, 7850
search_bytes = struct.pack('<III', 7849, 7876, 7850)

print(f"Searching for sequence 7849, 7876, 7850 in memory...")

for base in range(0x24000000, 0x25000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    raw = buf.raw
    
    idx = raw.find(search_bytes)
    while idx != -1:
        addr = base + idx
        # Read more data around this location
        data = create_string_buffer(300)
        if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr - 4), data, 300, byref(c_size_t(0))):
            # Check if there's a count before this
            cnt = struct.unpack('<I', data.raw[:4])[0]
            if 60 <= cnt <= 80:
                print(f"  Found at {hex(addr - 4)}: count={cnt}")
                plays = []
                for j in range(cnt):
                    v = struct.unpack('<I', data.raw[4+j*4:4+(j+1)*4])[0]
                    plays.append(v)
                print(f"    first 10: {plays[:10]}")
        
        idx = raw.find(search_bytes, idx + 1)

print("Done searching")
CloseHandle(hproc)
