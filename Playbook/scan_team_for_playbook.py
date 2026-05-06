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

# Simple approach - let's write unique values to EXACT player attribute addresses we KNOW work
# and also to different locations around team base where playbook might be,
# then check what's different in-game

# Our known good player offset for editing - let's replicate that pattern

# First, let's search for what ADDRESSES we KNOW work for player editing from earlier research
# In 2k26_offsets, attributes are at various offsets from team base

# Similarly, playbook should be at a similar fixed offset from team

# Looking at player info: attributes typically at offset ~240+ in team structure

# Let's find team playbook by scanning for arrays in team region
# We'll use pattern: look for sequences of 60+ valid play offsets

team_start = 0x2d190000
team_size = 0x10000

print('=== Scanning team region for playbook arrays ===')

team_data = mem_read(hproc, team_start, team_size)
if team_data:
    # Look for sequences of small offsets at stride 0x30 (48 bytes)
    for search_pos in range(0, team_size - (60*0x30), 0x30):
        # Check first few offsets at this position
        try:
            first = struct.unpack('<I', team_data[search_pos:search_pos+4])[0]
            if first > 0 and first < 0x10000:  # Valid offset range
                # Check pattern - at stride 0x30 = 48 bytes apart, there should be more valid offsets
                more_valid = 0
                for i in range(1, 12):  # Check 12 more entries
                    test_pos = search_pos + i*0x30
                    if test_pos + 4 < team_size:
                        val = struct.unpack('<I', team_data[test_pos:test_pos+4])[0]
                        if 0 < val < 0x10000:
                            more_valid += 1
                
                # If we have 8 or more valid in sequence, this is our playbook!
                if more_valid >= 8:
                    playbook_addr = team_start + search_pos
                    print('FOUND playbook array candidate at {}'.format(hex(playbook_addr)))
                    
                    # Show first 10 offsets
                    print('First 10 play offsets:')
                    for i in range(10):
                        off = struct.unpack('<I', team_data[search_pos + i*0x30 : search_pos + i*0x30 + 4])[0]
                        print('  [{}] offset {} = {}'.format(i, off, hex(off)))
                    
                    # Found it! Now let's modify and test
                    # Write our unique marker at index 0
                    test_offset = 0x1337  # Unique test value
                    
                    if mem_write(hproc, playbook_addr, struct.pack('<I', test_offset)):
                        print('\nWRITING test value {} to this address!'.format(hex(test_offset)))
                        print('Check game if first play changed!')
                    
                    exit()
        except:
            pass

print('Done - tell me what happens in-game!')

CloseHandle(hproc)