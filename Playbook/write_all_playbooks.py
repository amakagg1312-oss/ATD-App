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

# Let's try writing to a specific playbook that matches what we know is real
# The playbook at 0x2FFCA1A00 had the right values: [1352, 1133, 557, 742, 2591...]
# This matches our screenshot!

# Write our test plays to index 50 of THIS playbook
playbook_addr = 0x2FFCA1A00
index = 50

# Known play offsets from earlier
test_offsets = [
    550,    # FIST 21 IVERSON
    712,    # FIST CHEST FLARE  
    896,    # MIL FIST 34 DOWN SLIP
    1216,   # MEM PUNCH 5 WEAK
    2558,   # POR FIST 15
]

print('=== Writing test plays to {} at indices 50-54 ==='.format(hex(playbook_addr)))

wrote = []
for i, offset in enumerate(test_offsets):
    addr = playbook_addr + (50 + i) * 0x30
    data = struct.pack('<I', offset)
    
    if mem_write(hproc, addr, data):
        print('Wrote offset {} to index {}'.format(offset, 50 + i))
        wrote.append((50 + i, offset, addr))

# Verify what we wrote
print('\n=== Verification ===')
for i in range(50, 55):
    addr = playbook_addr + i * 0x30
    data = mem_read(hproc, addr, 4)
    if data:
        val = struct.unpack('<I', data)[0]
        print('[{}] {} = {}'.format(i, hex(addr), val))

# Also try writing to other likely playbook bases
other_bases = [0x2FFCA1910, 0x2FFCA19D0]

for base in other_bases:
    print('\nTrying base: {}'.format(hex(base)))
    for i, offset in enumerate(test_offsets):
        addr = base + (50 + i) * 0x30
        data = struct.pack('<I', offset)
        if mem_write(hproc, addr, data):
            print('  Wrote to index {}'.format(50 + i))

print('\n\nDone! Please check:')
print('1. Open the game')
print('2. Go to 76ers playbook')
print('3. Look at BLOB 06 (indices 50-54)')
print('4. Tell me what plays you see!')

CloseHandle(hproc)