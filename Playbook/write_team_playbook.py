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

# Find exact location our team's playbook is by using reference to our known addresses

# Get team location - find the structure's START for our team
phi_data = mem_read(hproc, 0x2d000000, 0x400000)
if phi_data:
    phi_offset = phi_data.find(b'PHI')
    if phi_offset >= 0:
        team_base = 0x2d000000 + phi_offset - 0x30  # Team base probably just before name
        
        team = mem_read(hproc, team_base, 5700)
        if team:
            print('Team structure at {}'.format(hex(team_base)))
            
            # Look for ANY pointer to our known playbooks in this team structure space
            for offset in range(0, 5700, 4):
                try:
                    val = struct.unpack('<I', team[offset:offset+4])[0]
                    
                    # Any reference to 0x2FFCAxxx range
                    if 0x2FFCA000 <= val <= 0x2FFCB000:
                        print('Playbook pointer at team+0x{:x}: {}'.format(offset, hex(val)))
                        
                        # Try writing test to this location
                        target_addr = team_base + offset
                        test_offset = 550
                        
                        if mem_write(hproc, target_addr, struct.pack('<I', test_offset)):
                            verify = mem_read(hproc, target_addr, 4)
                            if verify and struct.unpack('<I', verify)[0] == test_offset:
                                print('\nWRITE SUCCESS at {}!'.format(hex(target_addr)))
                                print('Check game now!')
                                break
                except:
                    pass

CloseHandle(hproc)