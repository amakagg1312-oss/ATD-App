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

# The team table base from 2k26_offsets.json was 0x2A82E17D0
# Let's verify by looking at what's at that location's first team entry
# and cross-reference with what team_dumper.py found

table_base = 0x2A82E17D0
stride = 5672

first_team = mem_read(hproc, table_base, 0x100)
second_team = mem_read(hproc, table_base + stride, 0x100)

if first_team and second_team:
    print('First team at {}:'.format(hex(table_base)))
    # Look at player 1 offset (usually team has player array starting at offset 0)
    # Check for player name at offset ~738 (from team_dumper.py)
    player1_addr = struct.unpack('<I', first_team[0:4])[0]
    print('  First ptr: {}'.format(hex(player1_addr)))
    
    if player1_addr > 0x10000000 and player1_addr < 0x40000000:
        player_data = mem_read(hproc, player1_addr, 100)
        if player_data:
            print('Player name at offset 738:')
            # Read offset 738 as wstring
            for i in range(738, 758, 2):
                if i+1 < len(player_data):
                    w = struct.unpack('<H', player_data[i:i+2])[0]
                    if w == 0:
                        break
                    print(chr(w), end='')
            print()

# Now let's look at second team entry
second_addr = table_base + stride
print('\nSecond team (Bucks) at {}'.format(hex(second_addr)))

# What's the difference between team entries?
# Let's find team+0x33c area that has count

first_count = struct.unpack('<I', first_team[0x33c:0x340])[0]
second_count = struct.unpack('<I', second_team[0x33c:0x340])[0]
print('  First team count at +0x33c: {}'.format(first_count))
print('  Second team count at +0x33c: {}'.format(second_count))

CloseHandle(hproc)