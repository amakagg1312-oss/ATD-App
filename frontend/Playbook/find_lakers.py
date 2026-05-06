# Search for "Lakers" or "LAKERS" string in memory
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

print("Searching for 'Lakers' or 'LAKERS' in memory...")

for base in range(0x24000000, 0x25000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    raw = buf.raw
    
    # Search for "Lakers" (case insensitive)
    for search_str in [b'Lakers', b'LAKERS', b'lakers']:
        idx = raw.find(search_str)
        while idx != -1:
            addr = base + idx
            # Read surrounding data
            data = create_string_buffer(200)
            if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr - 50), data, 200, byref(c_size_t(0))):
                # Look for count=70 nearby
                for offset in range(0, 200, 4):
                    cnt = struct.unpack('<I', data.raw[offset:offset+4])[0]
                    if cnt == 70:
                        print(f"  Found 'Lakers' at {hex(addr)}, count=70 at offset {offset}")
                        # Read more data around count
                        plays_addr = addr - 50 + offset + 4
                        plays_data = create_string_buffer(70 * 4)
                        if kern.ReadProcessMemory(hproc, ctypes.c_void_p(plays_addr), plays_data, 70 * 4, byref(c_size_t(0))):
                            plays = []
                            for j in range(70):
                                v = struct.unpack('<I', plays_data.raw[j*4:(j+1)*4])[0]
                                plays.append(v)
                            valid = sum(1 for p in plays if 1 <= p <= 12506)
                            print(f"    plays: {plays[:10]}, valid={valid}")
            
            idx = raw.find(search_str, idx + 1)

print("Done searching")
CloseHandle(hproc)
