import psutil, ctypes, struct
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer

kernel = WinDLL('kernel32')
RPM = kernel.ReadProcessMemory
RPM.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, c_size_t, ctypes.POINTER(c_size_t)]
CloseHandle = kernel.CloseHandle

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)

print(f'PID: {pid}')

found = []
for base in range(0x27000000, 0x28000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if RPM(h, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        raw = buf.raw
        for i in range(0, len(raw) - 0x200, 4):
            team_id = struct.unpack('=I', raw[i:i+4])[0]
            if 0 <= team_id <= 30:
                po = 0x130
                if i + po + 4 <= len(raw):
                    cnt = struct.unpack('=I', raw[i+po:i+po+4])[0]
                    if 50 <= cnt <= 100:
                        addr = base + i + po
                        pb_buf = create_string_buffer(4 + cnt * 4)
                        if RPM(h, ctypes.c_void_p(addr), pb_buf, 4 + cnt * 4, byref(c_size_t(0))):
                            pb_raw = pb_buf.raw
                            plays = []
                            for j in range(cnt):
                                v = struct.unpack('=I', pb_raw[4+j*4:4+(j+1)*4])[0]
                                if 1 <= v <= 12506:
                                    plays.append(v)
                            if len(plays) >= 50:
                                found.append((addr, cnt, plays))
                                print(f'Found at 0x{addr:X}, count={cnt}, valid={len(plays)}')

print(f'Total: {len(found)}')
CloseHandle(h)