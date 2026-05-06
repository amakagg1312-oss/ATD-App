import struct, ctypes, subprocess
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer

kernel32 = WinDLL('kernel32', use_last_error=True)
pid = int(subprocess.run(['powershell', '-Command', '(Get-Process NBA2K26).Id'], capture_output=True, text=True).stdout.strip())
hproc = kernel32.OpenProcess(0x1F0FFF, False, pid)

rpm = kernel32.ReadProcessMemory
rpm.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(c_size_t)]
rpm.restype = wintypes.BOOL

# Search for play indices 2840, 2841
print('Searching for plays 2840, 2841...')
for base in range(0x24000000, 0x26000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if not rpm(hproc, ctypes.c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        continue
    raw = buf.raw
    for i in range(0, 0x100000 - 12, 4):
        if struct.unpack('<I', raw[i:i+4])[0] == 2840:
            if i + 12 <= len(raw):
                if struct.unpack('<I', raw[i+4:i+8])[0] == 2841:
                    print('Found [2840,2841] at ' + hex(base+i))
                    break