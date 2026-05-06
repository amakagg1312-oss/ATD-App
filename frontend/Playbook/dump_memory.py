# Dump memory around known playbook addresses to see structure
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Known addresses from previous searches
addresses = [
    0x2407c258,  # PHI playbook
    0x2407c260,  # Another playbook
    0x2407c4e0,  # uint16 match
    0x2407c6f0,  # uint16 match
]

for addr in addresses:
    print(f"\nDumping memory at {hex(addr)}:")
    # Read 500 bytes
    data = create_string_buffer(500)
    if kern.ReadProcessMemory(hproc, ctypes.c_void_p(addr), data, 500, byref(c_size_t(0))):
        # Print as hex and ASCII
        for i in range(0, 500, 16):
            hex_str = ' '.join(f'{b:02x}' for b in data.raw[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data.raw[i:i+16])
            print(f"  {hex(addr + i)}: {hex_str:<48s} {ascii_str}")

CloseHandle(hproc)
