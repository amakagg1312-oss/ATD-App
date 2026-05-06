import psutil, ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer

kernel = WinDLL('kernel32')
RPM = kernel.ReadProcessMemory
RPM.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)

# Search in chunks
search_bytes = b'N\x00i\x00c\x00k\x00 \x00N\x00u\x00r\x00s\x00e\x00'

for base in range(0x26000000, 0x27000000, 0x100000):
    buf = create_string_buffer(0x100000)
    try:
        if RPM(h, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
            raw = buf.raw
            idx = raw.find(search_bytes)
            if idx >= 0:
                print(f"Found 'Nick Nurse' UTF16 at 0x{base+idx:X}")
    except:
        pass

print("Done")