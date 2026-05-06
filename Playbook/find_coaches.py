import psutil, ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer, c_void_p

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = c_void_p
RPM = kernel.ReadProcessMemory
RPM.argtypes = [c_void_p, c_void_p, c_void_p, c_size_t, ctypes.POINTER(c_size_t)]
VirtualQueryEx = kernel.VirtualQueryEx
VirtualQueryEx.restype = ctypes.c_size_t
VirtualQueryEx.argtypes = [c_void_p, c_void_p, c_void_p, ctypes.c_size_t]

class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64),
        ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", ctypes.c_uint32),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
    ]

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)

mbr = MBI()
addr = 0
count = 0
searches = [b'Spoelstra', b'Rivers', b'Kerr', b'Popovich', b'Mazzulla']

while True:
    result = VirtualQueryEx(h, c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
    if result == 0:
        break
    
    if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x1000000:
        buf = create_string_buffer(mbr.RegionSize)
        if RPM(h, c_void_p(mbr.BaseAddress), buf, mbr.RegionSize, byref(c_size_t(0))):
            raw = buf.raw
            for s in searches:
                if s in raw:
                    idx = raw.find(s)
                    print(f"Found {s} at 0x{mbr.BaseAddress + idx:X}")
                    start = max(0, idx - 30)
                    end = min(len(raw), idx + 50)
                    print(f"  {raw[start:end]}")
                    count += 1
                    if count > 20:
                        break
    
    addr = mbr.BaseAddress + mbr.RegionSize

print(f"Total: {count}")