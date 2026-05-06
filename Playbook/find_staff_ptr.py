import psutil, ctypes, struct
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer, c_void_p

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = c_void_p
RPM = kernel.ReadProcessMemory
RPM.argtypes = [c_void_p, c_void_p, c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)

# Try reading staff entries at known team addresses
# From earlier: team at 0x27230BC4
# Staff stride = 432, first_name at 0x28, last_name at 0x0

team = 0x27230BC4

# Read team structure to find staff pointer
buf = create_string_buffer(0x1000)
RPM(h, c_void_p(team), buf, 0x1000, byref(c_size_t(0)))
raw = buf.raw

# Look for potential staff pointer in team structure
print("Team structure at 0x27230BC4:")
for off in range(0, 0x1000, 8):
    val = struct.unpack('<Q', raw[off:off+8])[0]
    if val > 0x1000000 and val < 0x200000000:
        # Try reading from this pointer
        buf2 = create_string_buffer(100)
        if RPM(h, c_void_p(val), buf2, 100, byref(c_size_t(0))):
            try:
                s = buf2.raw.decode('utf-16-le').strip('\x00')
                if len(s) >= 3 and s.replace(' ','').isalpha():
                    print(f"  0x{off:X} -> 0x{val:X}: {s[:40]}")
            except:
                pass