# Read memory around PHI playbook to find pattern
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# PHI playbook was at 0x2407c258
addr = 0x2407c258
print(f"Reading memory around {hex(addr)} (PHI playbook)...")
data = create_string_buffer(256)
if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr - 100), data, 256, byref(c_size_t(0))):
    for offset in range(0, 256, 16):
        vals = []
        for j in range(4):
            v = struct.unpack('<I', data.raw[offset+j*4:offset+(j+1)*4])[0]
            vals.append(v)
        if vals[0] != 0 or vals[1] != 0 or vals[2] != 0 or vals[3] != 0:
            addr_str = hex(addr - 100 + offset)
            print(f"{addr_str}: {vals}")

# Also check if there's team info nearby
print("\nLooking for team ID near playbook...")
for offset in range(-0x100, 0x200, 4):
    check_addr = addr + offset
    data = create_string_buffer(4)
    if kern.ReadProcessMemory(hproc, ctypes.c_void_p(check_addr), data, 4, byref(c_size_t(0))):
        val = struct.unpack('<I', data.raw)[0]
        # Team ID might be 0-29
        if 0 <= val <= 30:
            print(f"  {hex(check_addr)}: team_id = {val}")

CloseHandle(hproc)