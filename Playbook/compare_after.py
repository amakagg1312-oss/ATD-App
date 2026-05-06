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
print('NBA2K26 PID: {}'.format(pid))

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

before_file = r'D:\project\Playbook\playbook_snapshot.bin'

print('Loading BEFORE snapshot...')
with open(before_file, 'rb') as f:
    before_data = f.read()

print('Taking AFTER snapshot...')

after_data = mem_read(hproc, 0x2FFCA0000, 0x20000)

if not after_data:
    print('Failed to read after memory')
    CloseHandle(hproc)
    exit()

print('Comparing...')

differences = []
for i in range(min(len(before_data), len(after_data))):
    if before_data[i] != after_data[i]:
        differences.append(i)

print('Found {} differences'.format(len(differences)))

if not differences:
    print('No differences found in this region!')
    CloseHandle(hproc)
    exit()

# Analyze groups
groups = []
current_group = [differences[0]]
for i in range(1, len(differences)):
    if differences[i] == differences[i-1] + 1:
        current_group.append(differences[i])
    else:
        groups.append(current_group)
        current_group = [differences[i]]
groups.append(current_group)

print('\nConsecutive groups: {}'.format(len(groups)))

# Show first 30 groups
for i, group in enumerate(groups[:30]):
    start_addr = 0x2FFCA0000 + group[0]
    end_addr = 0x2FFCA0000 + group[-1]
    size = len(group)
    print('Group {}: offset {} ({} bytes) at {}'.format(i, hex(group[0]), size, hex(start_addr)))

# Try writing test - find first large group and try to modify
if groups:
    first_large = groups[0]
    test_addr = 0x2FFCA0000 + first_large[0]
    
    # Read current value
    current = mem_read(hproc, test_addr, 4)
    if current:
        print('\nCurrent value at {}: {}'.format(hex(test_addr), hex(struct.unpack('<I', current)[0])))
        
        # Try writing test value
        test_val = 550
        if mem_write(hproc, test_addr, struct.pack('<I', test_val)):
            verify = mem_read(hproc, test_addr, 4)
            if verify and struct.unpack('<I', verify)[0] == test_val:
                print('Wrote {} - SUCCESS! Check if playbook changed in game.'.format(test_val))

CloseHandle(hproc)