# Check if PHI playbook changed after switching to Lakers
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Check PHI playbook address
addr = 0x2407c260
data = create_string_buffer(50)
if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr), data, 50, byref(c_size_t(0))):
    count = struct.unpack('<I', data.raw[:4])[0]
    print(f"0x2407c260 - current count: {count}")
    
    if count <= 30:
        plays = []
        for j in range(count):
            v = struct.unpack('<I', data.raw[4+j*4:4+(j+1)*4])[0]
            plays.append(v)
        print(f"  plays: {plays}")

# Also check if there's another area with 70 plays
print("\nSearching for count=70 near 0x2407c000-0x2407d000...")
for check_addr in range(0x2407c000, 0x2407d000, 4):
    data = create_string_buffer(4)
    if kern.ReadProcessMemory(hproc, ctypes.c_void_p(check_addr), data, 4, byref(c_size_t(0))):
        val = struct.unpack('<I', data.raw)[0]
        if val == 70:
            print(f"  Found count=70 at {hex(check_addr)}")
            # Check nearby for plays
            plays_data = create_string_buffer(300)
            if kern.ReadProcessMemory(hproc, ctypes.c_void_p(check_addr + 4), plays_data, 300, byref(c_size_t(0))):
                plays = []
                for j in range(min(70, 75)):
                    if j*4 + 4 <= 300:
                        v = struct.unpack('<I', plays_data.raw[j*4:j*4+4])[0]
                        if 1 <= v <= 12506:
                            plays.append(v)
                print(f"    valid plays in first 75: {len(plays)}")
                if plays:
                    print(f"    first 10: {plays[:10]}")

CloseHandle(hproc)