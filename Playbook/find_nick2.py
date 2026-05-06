import psutil, ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer

kernel = WinDLL('kernel32')
RPM = kernel.ReadProcessMemory
RPM.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)

# Search for various encodings
searches = [
    b'Nick',
    b'Nick ',
    b'Nurse',
    b'Nick\x00',
    b'Nurse\x00',
]

for base in range(0x26000000, 0x2A000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if RPM(h, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        raw = buf.raw
        for s in searches:
            if s in raw:
                idx = raw.find(s)
                print(f'Found {s} at 0x{base+idx:X}')

print('Done')