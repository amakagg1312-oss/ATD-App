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

# The 76ers team is at index 0 in team table: 0x2A82E17D0
# Maybe there's a "playbook pointer" that needs to be set

# Find all teams: look for value 0x2A (team index 0 = PHI) or team pointer
# Maybe we can find where playbook gets assigned in-game

print('Looking for loaded roster in memory...')

# Search for "RosterNBA0020" string or similar in memory
search_for = b'0020'

for base in range(0x2D000000, 0x32000000, 0x100000):
    data = mem_read(hproc, base, 0x100000)
    if data:
        pos = data.find(search_for)
        if pos >= 0:
            print('Found "0020" at {} + {}'.format(hex(base), hex(pos)))
            
            # Look around for team data
            near = mem_read(hproc, base + pos - 50, 100)
            if near:
                print('Nearby:', near[:30])
            break

# What about if we do this - check if memory has references to roster that are readable

# Actually - let's search for reference to our team that has valid data
team_table = 0x2A82E17D0

# Find team+0x464 play - what does it point to?
team_data = mem_read(hproc, team_table, 0x500)
if team_data:
    val = struct.unpack('<I', team_data[0x464:0x468])[0]
    print('\n76ers team+0x464 value: {} ({})'.format(val, hex(val)))
    
    # Check if that value is a valid pointer
    if val > 0x1000000:
        play_data = mem_read(hproc, val, 20)
        if play_data:
            print('Has valid memory at that address')
            print('First bytes:', play_data[:20])
        else:
            print('Not a valid pointer - read failed')
    else:
        print('Value too small, not a pointer')

# Could the playbook be elsewhere? Search where 0x464 value comes FROM in team
# The game reads from roster and loads into memory when team is selected

# Perhaps the issue is simpler - we might need to also set the play count AND set valid play entries

# Let's verify our writes are still in memory
current = struct.unpack('<I', team_data[0x464:0x468])[0]
print('\nCurrent at team+0x464:', current)

CloseHandle(hproc)