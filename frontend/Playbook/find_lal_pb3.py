# Search memory for Lakers playbook using uint16 indices
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
lal_indices = set([7849, 7876, 7850, 7878, 8068, 7772, 7831, 7896, 7899, 7941, 9237, 7962, 7964, 9238, 9241, 9244])

print(f"Searching for Lakers playbook (uint16)...")

found = 0
for base in range(0x24000000, 0x25000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    raw = buf.raw
    
    for i in range(0, 0x100000 - 200, 2):
        cnt = struct.unpack('<H', raw[i:i+2])[0]
        # Search for count around 70
        if 60 <= cnt <= 80:
            addr = base + i
            # Read count * 2 bytes for uint16 array
            data_size = cnt * 2
            data = create_string_buffer(data_size)
            if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr + 2), data, data_size, byref(c_size_t(0))):
                plays = []
                for j in range(cnt):
                    v = struct.unpack('<H', data.raw[j*2:(j+1)*2])[0]
                    plays.append(v)
                
                # Check if any of our known LAL indices are in this array
                matches = sum(1 for p in plays if p in lal_indices)
                if matches >= 5:
                    print(f"  {hex(addr)}: count={cnt}, LAL matches={matches}")
                    print(f"    plays: {plays[:10]}")
                    found += 1

print(f"Total candidates with LAL plays: {found}")
CloseHandle(hproc)
