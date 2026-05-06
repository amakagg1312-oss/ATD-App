import struct
import ctypes
from ctypes import wintypes
import subprocess

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
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
hproc = OpenProcess(0x1F0FFF, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    if ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count)):
        return bytes(buf)
    return None

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    return WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count)) and write_count.value == len(data)

# Earlier we saw team structure at 0x2A82E17D0 is read from file
# Maybe there's ANOTHER location where the team is loaded and is WRITABLE  
# Search for other references to team or play data in memory

# Search memory for reference to team+0x464 which we found has play data
search_val = 0x2A82E17D0 + 0x464  # team + playbook offset

# Actually, let's find ALL places that reference play-related values
# Look for data we know: value 73 at team+0x33c

# Find where else this pattern occurs: look for value 73 in memory near known team
print('Searching for value 73 around teams...')

for base in [0x2A800000, 0x2A820000, 0x2A840000]:
    data = mem_read(hproc, base, 0x20000)
    if data:
        for i in range(0, 0x20000, 4):
            try:
                val = struct.unpack('<I', data[i:i+4])[0]
                if val == 73:
                    print(f'Found 73 at {hex(base+i)}')
                    # Check surrounding for context
                    print(f'  +4: {struct.unpack(\"<I\", data[i+4:i+8])[0]}')
                    print(f'  +8: {struct.unpack(\"<I\", data[i+8:i+12])[0]}')
            except:
                pass

CloseHandle(hproc)