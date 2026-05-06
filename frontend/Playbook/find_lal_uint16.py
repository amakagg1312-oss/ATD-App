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

print(f"Searching for Lakers play indices as uint16...")

# Search for first index 7849 as uint16
search_bytes = struct.pack('<H', 7849)

for base in range(0x24000000, 0x25000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    raw = buf.raw
    
    idx = raw.find(search_bytes)
    while idx != -1:
        addr = base + idx
        # Check if this is part of a playbook structure
        # Look for count before this (at offset -2)
        if idx >= 2:
            cnt = struct.unpack('<H', raw[idx-2:idx])[0]
            if 60 <= cnt <= 80:
                # Read the full playbook
                plays_addr = addr
                plays_data = create_string_buffer(cnt * 2)
                if kern.ReadProcessMemory(hproc, ctypes.c_void_p(plays_addr), plays_data, cnt * 2, byref(c_size_t(0))):
                    plays = []
                    for j in range(cnt):
                        v = struct.unpack('<H', plays_data.raw[j*2:(j+1)*2])[0]
                        plays.append(v)
                    valid = sum(1 for p in plays if 1 <= p <= 12506)
                    if valid >= cnt * 0.5:
                        print(f"  {hex(addr - 2)}: count={cnt}, valid={valid}")
                        print(f"    plays: {plays[:10]}")
        
        idx = raw.find(search_bytes, idx + 1)

print("Done searching")
CloseHandle(hproc)
