# Find ANY playbook with 50-80 plays
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

print("Searching for any playbook with 50-80 plays...")
count = 0

for base in range(0x23000000, 0x25000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    
    raw = buf.raw
    
    # Search for any count in range 50-80
    for i in range(len(raw) - 4):
        count_val = struct.unpack('<I', raw[i:i+4])[0]
        if 50 <= count_val <= 80:
            addr = base + i
            
            # Read plays
            plays = []
            valid = 0
            for j in range(count_val):
                offset = i + 4 + j * 4
                if offset + 4 <= len(raw):
                    v = struct.unpack('<I', raw[offset:offset+4])[0]
                    if 1 <= v <= 12506:
                        valid += 1
                        plays.append(v)
            
            if valid >= 40:
                count += 1
                if count <= 5:
                    print(f"  {hex(addr)}: count={count_val}, valid={valid}")
                    print(f"    plays: {plays[:10]}")
    
    if count >= 5:
        break

print(f"Total found: {count}")
CloseHandle(hproc)