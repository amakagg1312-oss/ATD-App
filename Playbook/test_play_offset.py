import struct
import ctypes
from ctypes import wintypes
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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

import subprocess
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

phi_addr = 0x2A82E17D0
phi_data = mem_read(hproc, phi_addr, 5672)

# team+0x464 = first play offset?
first_play_offset = struct.unpack('<I', phi_data[0x464:0x468])[0]
print('First play offset at team+0x464:', first_play_offset, '({})'.format(hex(first_play_offset)))

# Look up in string block
string_block = mem_read(hproc, 0x2FFCD8000, 0x40000)
if string_block and first_play_offset < len(string_block):
    name_bytes = b''
    for j in range(first_play_offset, first_play_offset + 60, 2):
        if j+1 < len(string_block):
            w = struct.unpack('<H', string_block[j:j+2])[0]
            if w == 0:
                break
            name_bytes += struct.pack('<H', w)
    try:
        name = name_bytes.decode('utf-16le')
        print('Play name:', name)
    except:
        pass

# Now check more offsets after 0x464 - are these consecutive play entries?
print('\nNext few play offsets (consecutive from 0x464):')
for i in range(10):
    offset = 0x464 + i * 4
    val = struct.unpack('<I', phi_data[offset:offset+4])[0]
    if val > 0 and val < 0x40000:
        # Try lookup
        if string_block and val < len(string_block):
            name_bytes = b''
            for j in range(val, min(val+60, len(string_block)), 2):
                w = struct.unpack('<H', string_block[j:j+2])[0]
                if w == 0:
                    break
                name_bytes += struct.pack('<H', w)
            try:
                name = name_bytes.decode('utf-16le')
                print('  team+0x{:x}: {} ({}) - {}'.format(offset, val, hex(val), name))
            except:
                print('  team+0x{:x}: {} ({})'.format(offset, val, hex(val)))

# Test write - change first play to 550 (FIST 21 IVERSON)
# Current value is 550 - let's try 712 (FIST CHEST FLARE)

print('\nWriting test offset 712 to team+0x464...')
test_offset = 712

if mem_write(hproc, phi_addr + 0x464, struct.pack('<I', test_offset)):
    verify = mem_read(hproc, phi_addr + 0x464, 4)
    if verify and struct.unpack('<I', verify)[0] == test_offset:
        print('WRITE SUCCESS! Check game - first play should now be FIST CHEST FLARE')

CloseHandle(hproc)