# Check address 0x2407c4e0 for uint16 count=70
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Check 0x2407c4e0 specifically
addr = 0x2407c4e0

# Read as uint16
data = create_string_buffer(8)
if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr), data, 8, byref(c_size_t(0))):
    val16 = struct.unpack('<H', data.raw[:2])[0]
    print(f"0x2407c4e0: uint16 = {val16}")
    
    if val16 == 70:
        # Read 70 uint16 values
        plays_addr = addr + 2
        plays_data = create_string_buffer(70 * 2)
        if kern.ReadProcessMemory(hproc, ctypes.c_void_p(plays_addr), plays_data, 70 * 2, byref(c_size_t(0))):
            plays = []
            for j in range(70):
                v = struct.unpack('<H', plays_data.raw[j*2:(j+1)*2])[0]
                plays.append(v)
            
            valid = sum(1 for p in plays if 1 <= p <= 12506)
            print(f"  count=70, valid={valid}")
            print(f"  plays (uint16): {plays[:10]}...")

# Also check nearby addresses
print("\nChecking 0x2407c500 to 0x2407c600:")
for check_addr in range(0x2407c500, 0x2407c600, 4):
    data = create_string_buffer(4)
    if kern.ReadProcessMemory(hproc, ctypes.c_void_p(check_addr), data, 4, byref(c_size_t(0))):
        val = struct.unpack('<I', data.raw)[0]
        if 50 <= val <= 80:
            print(f"  {hex(check_addr)}: {val}")

CloseHandle(hproc)