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

pid = 58172
playbook_base = 0x2FFCA19D0
stride = 0x30

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    ok = WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count))
    return ok and write_count.value == len(data)

# Known offsets from previous research
play_offsets = {
    "FIST 21 IVERSON": 550,
    "FIST CHEST FLARE": 712,
    "MIL FIST 34 DOWN SLIP": 896,
    "MEM PUNCH 5 WEAK": 1216,
    "POR FIST 15 UP": 2558,
}

print('=== Writing 5 plays to 76ers playbook ===')
print('Target indices: 50-54 (BLOB 06)')
print('')

# Write to indices 50-54
entries = [
    (50, "FIST 21 IVERSON", 550),
    (51, "FIST CHEST FLARE", 712),
    (52, "MIL FIST 34 DOWN SLIP", 896),
    (53, "MEM PUNCH 5 WEAK", 1216),
    (54, "POR FIST 15 UP", 2558),
]

for idx, name, offset in entries:
    addr = playbook_base + idx * stride
    packed = struct.pack('<I', offset)
    success = mem_write(hproc, addr, packed)
    if success:
        print('OK: Wrote "{}" (offset {}) to index {}'.format(name, offset, idx))
    else:
        print('FAIL: Could not write "{}"'.format(name))

print('')
print('=== VERIFY: Reading back the written plays ===')
for i in range(50, 55):
    data = mem_read(hproc, playbook_base + i * stride, 4)
    if data:
        off = struct.unpack('<I', data)[0]
        print('[{}] offset = {}'.format(i, off))

print('')
print('Done! Go check BLOB 06 in the 76ers playbook menu.')
print('You should see these plays: FIST 21 IVERSON, FIST CHEST FLARE, etc.')

CloseHandle(hproc)