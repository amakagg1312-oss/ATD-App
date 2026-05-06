# Search memory for Lakers playbook by searching for play names
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Search for "LAL" string in memory
print("Searching for 'LAL' string in memory...")
for base in range(0x24000000, 0x25000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    raw = buf.raw
    
    idx = raw.find(b'LAL')
    while idx != -1:
        addr = base + idx
        # Read surrounding data
        data = create_string_buffer(100)
        if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr - 20), data, 100, byref(c_size_t(0))):
            # Check if nearby there's a count + play indices structure
            for offset in range(0, 100, 4):
                cnt = struct.unpack('<I', data.raw[offset:offset+4])[0]
                if 60 <= cnt <= 80:
                    plays_addr = addr - 20 + offset + 4
                    plays_data = create_string_buffer(cnt * 4)
                    if kern.ReadProcessMemory(hproc, ctypes.c_void_p(plays_addr), plays_data, cnt * 4, byref(c_size_t(0))):
                        plays = []
                        for j in range(cnt):
                            v = struct.unpack('<I', plays_data.raw[j*4:(j+1)*4])[0]
                            plays.append(v)
                        valid = sum(1 for p in plays if 1 <= p <= 12506)
                        if valid >= cnt * 0.5:
                            print(f"  Found near 'LAL' at {hex(addr)}: count={cnt}, valid={valid}")
                            print(f"    plays: {plays[:10]}")
        
        idx = raw.find(b'LAL', idx + 1)

CloseHandle(hproc)
