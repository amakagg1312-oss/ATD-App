import psutil, ctypes, struct
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer, c_void_p

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = c_void_p
RPM = kernel.ReadProcessMemory
RPM.argtypes = [c_void_p, c_void_p, c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)

# Check the game-specific addresses
candidates = [0x87BBD80, 0xE132EFB8, 0x2A70D2D61]

for addr in candidates:
    print(f"\n--- 0x{addr:X} ---")
    buf = create_string_buffer(200)
    if RPM(h, c_void_p(addr - 50), buf, 200, byref(c_size_t(0))):
        raw = buf.raw
        print(repr(raw))
        
        # Try to decode as UTF-16
        try:
            s = raw.decode('utf-16-le').strip('\x00')
            print(f"UTF16: {s[:80]}")
        except:
            pass