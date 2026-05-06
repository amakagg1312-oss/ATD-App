# Check the new playbook addresses
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

new_addrs = [0x2408e6d8, 0x2408e7a0, 0x2408fbe0]

print("Checking new playbook addresses:")
for addr in new_addrs:
    data = create_string_buffer(300)
    if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr), data, 300, byref(c_size_t(0))):
        count = struct.unpack('<I', data.raw[:4])[0]
        print(f"\n{hex(addr)}: count={count}")
        
        if 1 <= count <= 125:
            plays = []
            for j in range(min(count, 80)):
                offset = 4 + j * 4
                if offset + 4 <= 300:
                    v = struct.unpack('<I', data.raw[offset:offset+4])[0]
                    if 1 <= v <= 12506:
                        plays.append(v)
            
            valid = len(plays)
            print(f"  valid plays: {valid}")
            print(f"  first 15 plays: {plays[:15]}")

CloseHandle(hproc)