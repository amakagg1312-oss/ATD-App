# Search for "LAL FIST" play name strings in memory
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Search for "LAL" string
print("Searching for 'LAL FIST' in memory...")
search_str = b'LAL FIST'

for base in range(0x23000000, 0x25000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    
    idx = buf.raw.find(search_str)
    if idx != -1:
        addr = base + idx
        # Extract string
        string_data = buf.raw[idx:idx+30]
        try:
            s = string_data.decode('ascii', errors='ignore').split('\0')[0]
            print(f"  Found at {hex(addr)}: {s}")
        except:
            pass

print("Done")
CloseHandle(hproc)