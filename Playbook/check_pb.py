import psutil, ctypes, struct
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer

kernel = WinDLL('kernel32')
RPM = kernel.ReadProcessMemory
RPM.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)

addr = 0x27048834 + 0x130
buf = create_string_buffer(20)
RPM(h, ctypes.c_void_p(addr), buf, 20, byref(c_size_t(0)))
raw = buf.raw
count = struct.unpack('=I', raw[:4])[0]
print(f'Playbook addr: 0x{addr:X}')
print(f'Count: {count}')
print(f'First play ID: {struct.unpack("=I", raw[4:8])[0]}')