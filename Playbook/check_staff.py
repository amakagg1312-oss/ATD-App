import psutil, ctypes, struct
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer, c_void_p

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = c_void_p
RPM = kernel.ReadProcessMemory
RPM.argtypes = [c_void_p, c_void_p, c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)

# From user data: Staff = Team + 0xC4 for packed set
# Team at 0x27230BC4
team = 0x27230BC4

# Read at offset 0xC4
buf = create_string_buffer(100)
RPM(h, c_void_p(team + 0xC4), buf, 100, byref(c_size_t(0)))
raw = buf.raw
print(f"At team+0xC4: {raw[:50]}")

# Try reading as pointer
ptr = struct.unpack('<Q', raw[:8])[0]
print(f"Pointer: 0x{ptr:X}")

if ptr > 0x1000000 and ptr < 0x200000000:
    buf2 = create_string_buffer(500)
    RPM(h, c_void_p(ptr), buf2, 500, byref(c_size_t(0)))
    print(f"At 0x{ptr:X}: {buf2.raw[:200]}")