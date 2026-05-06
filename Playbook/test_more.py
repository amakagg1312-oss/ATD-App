import struct
import ctypes
from ctypes import wintypes
import subprocess

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_ALL_ACCESS = 0x1F0FFF
OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE
CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL
ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
ReadProcessMemory.restype = wintypes.BOOL
WriteProcessMemory = kernel32.WriteProcessMemory  
WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL

result = subprocess.run(['powershell', '-Command', '(Get-Process NBA2K26).Id'], capture_output=True, text=True)
pid = int(result.stdout.strip())
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    if ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count)):
        return bytes(buf)
    return None

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    if WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count)):
        return write_count.value == len(data)
    return False

team_addr = 0x2A82E17D0

# Restore original value at +0x340
mem_write(hproc, team_addr + 0x340, struct.pack('<I', 0))

# Try writing to TWO places - both 73 and 65 counts might affect display
# If one is read-only count and other affects playable entries

# Try: write different test values to entry slots
# Play entries might be after count: at +0x340 (count 73) and +0x34c (count 65) 

# Let's check offset +0x33c = 73 play count - next entries should start at +0x340 
# But +0x340 is zero - maybe entries need different offset

# Try: entries might be at +0x350 (just after the second count)
print('Testing +0x350...')
if mem_write(hproc, team_addr + 0x350, struct.pack('<I', 100)):
    verify = mem_read(hproc, team_addr + 0x350, 4)
    if verify and struct.unpack('<I', verify)[0] == 100:
        print('Wrote 100 to +0x350')

# Try +0x358 which had some data
print('Testing +0x358...')
if mem_write(hproc, team_addr + 0x358, struct.pack('<I', 50)):
    verify = mem_read(hproc, team_addr + 0x358, 4)
    if verify and struct.unpack('<I', verify)[0] == 50:
        print('Wrote 50 to +0x358')

CloseHandle(hproc)