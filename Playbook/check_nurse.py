import psutil, ctypes, struct
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer, c_void_p

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = c_void_p
RPM = kernel.ReadProcessMemory
RPM.argtypes = [c_void_p, c_void_p, c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)

addr = 0xC1976D7E2
print(f"Checking 0x{addr:X}")

# Read around it
for offset in [-200, -100, -50, 0]:
    buf = create_string_buffer(200)
    if RPM(h, c_void_p(addr + offset), buf, 200, byref(c_size_t(0))):
        raw = buf.raw
        print(f"\nAt 0x{addr+offset:X}:")
        print(repr(raw))