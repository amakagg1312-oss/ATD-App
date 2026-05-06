# Search memory for Lakers playbook using known play indices (wider search)
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

print(f"Searching for Lakers playbook with indices: {list(lal_indices)[:5]}...")

found = 0
for base in range(0x24000000, 0x25000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    raw = buf.raw
    
    for i in range(0, 0x100000 - 400, 4):
        cnt = struct.unpack('<I', raw[i:i+4])[0]
        # Search for any count 5-100
        if 5 <= cnt <= 100:
            addr = base + i
            data = create_string_buffer(cnt * 4 + 4)
            if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr), data, cnt*4+4, byref(c_size_t(0))):
                vc = struct.unpack('<I', data.raw[:4])[0]
                if vc == cnt:
                    plays = []
                    for j in range(cnt):
                        v = struct.unpack('<I', data.raw[4+j*4:4+(j+1)*4])[0]
                        plays.append(v)
                    
                    # Check if any of our known LAL indices are in this array
                    matches = sum(1 for p in plays if p in lal_indices)
                    if matches >= 3:  # At least 3 Lakers plays found
                        print(f"  {hex(addr)}: count={cnt}, LAL matches={matches}")
                        print(f"    plays: {plays[:10]}")
                        found += 1

print(f"Total candidates with LAL plays: {found}")
CloseHandle(hproc)
