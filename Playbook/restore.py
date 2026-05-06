import struct
import ctypes
from ctypes import wintypes
import subprocess

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE
ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
ReadProcessMemory.restype = wintypes.BOOL

result = subprocess.run(['powershell', '-Command', '(Get-Process NBA2K26).Id'], capture_output=True, text=True)
pid = int(result.stdout.strip())
hproc = OpenProcess(0x1F0FFF, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    if ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count)):
        return bytes(buf)
    return None

team_addr = 0x2A82E17D0
team_data = mem_read(hproc, team_addr, 6000)

# Restore 73 count, set play count entries
mem_write = lambda a, v: WriteProcessMemory(hproc, ctypes.c_void_p(a), ctypes.c_buffer(v), 4, ctypes.byref(ctypes.c_size_t())) if WriteProcessMemory else lambda a, v: False
import ctypes
WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL
def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    if WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count)):
        return write_count.value == len(data)
    return False

# Restore original values
WriteProcessMemory(hproc, team_addr + 0x340, struct.pack('<I', 0), 4, ctypes.byref(ctypes.c_size_t()))
WriteProcessMemory(hproc, team_addr + 0x350, struct.pack('<I', 0), 4, ctypes.byref(ctypes.c_size_t()))
WriteProcessMemory(hproc, team_addr + 0x358, struct.pack('<I', 1869348864), 4, ctypes.byref(ctypes.c_size_t()))

print('Original values restored')

print('\nCurrent team playbook area:')
for off in [0x33c, 0x340, 0x348, 0x350, 0x358]:
    val = struct.unpack('<I', team_data[off:off+4])[0]
    print(f'+0x{off:03x}: {val}')

CloseHandle(hproc)