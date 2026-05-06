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

# The loaded snapshot should still have the playbook data in memory from before
# Compare loaded vs current to find differences

snapshot_file = r'D:\project\Playbook\playbook_loaded_snapshot.bin'
with open(snapshot_file, 'rb') as f:
    loaded_data = f.read()

# Read same region NOW
current_data = mem_read(hproc, 0x2E000000, 0x100000)

if current_data and loaded_data:
    # Find differences
    diffs = []
    for i in range(min(len(loaded_data), len(current_data))):
        if loaded_data[i] != current_data[i]:
            diffs.append(i)
    
    print('Found {} differences in 0x2E000000 region'.format(len(diffs)))
    
    if diffs:
        # Group consecutive
        groups = []
        current_group = [diffs[0]]
        for i in range(1, len(diffs)):
            if diffs[i] == diffs[i-1] + 1:
                current_group.append(diffs[i])
            else:
                groups.append(current_group)
                current_group = [diffs[i]]
        groups.append(current_group)
        
        print('Consecutive groups: {}'.format(len(groups)))
        
        # Show first 15 groups
        for i, group in enumerate(groups[:15]):
            addr = 0x2E000000 + group[0]
            size = len(group)
            print('Group {}: offset {} ({} bytes) at {}'.format(i, hex(group[0]), size, hex(addr)))
        
        # Try writing test to first group
        if groups:
            first_addr = 0x2E000000 + groups[0][0]
            print('\nTesting write at {}...'.format(hex(first_addr)))
            
            # Read current value
            current = mem_read(hproc, first_addr, 4)
            if current:
                val = struct.unpack('<I', current)[0]
                print('Current: {}'.format(hex(val)))
                
                # Write test
                test_val = 550
                if mem_write(hproc, first_addr, struct.pack('<I', test_val)):
                    verify = mem_read(hproc, first_addr, 4)
                    if verify and struct.unpack('<I', verify)[0] == test_val:
                        print('WRITE SUCCESS! Check game to see if playbook changed!')

CloseHandle(hproc)