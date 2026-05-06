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

# Team abbreviation search
team_names = [
    b'MIA', b'BOS', b'LAL', b'GSW', b'MIL', b'PHI',
    b'CHI', b'DEN', b'DAL', b'HOU', b'LAC', b'BKN',
    b'ATL', b'CHA', b'CLE', b'DET', b'IND', b'MEM',
    b'MIN', b'NO', b'OKC', b'ORL', b'PHX', b'POR',
    b'SAC', b'SAS', b'TOR', b'UTA', b'WAS', b'NOP'
]

# Search for team list in memory
print('=== Searching for team list ===')

# Try known team region around 0x2D
search_base = 0x2d000000
search_size = 0x300000

data = mem_read(hproc, search_base, search_size)
if data:
    print('Searching {} bytes...'.format(search_size))
    
    team_positions = {}
    for team_abbr in team_names:
        pos = data.find(team_abbr)
        if pos >= 0:
            # Found team name, now figure out the structure
            team_positions[team_abbr.decode('ascii')] = pos
    
    # Show teams found
    print('\nFound {} teams'.format(len(team_positions)))
    for name in sorted(team_positions.keys()):
        print('  {}: offset {}'.format(name, team_positions[name]))
    
    # Now find PHI (76ers) and check its structure
    if 'PHI' in team_positions:
        phi_offset = team_positions['PHI']
        # This should be the start of team data
        team_addr = search_base + phi_offset - 0x14  # Go back a bit - name is usually at offset +0x14 or similar in team struct
        
        # Actually let's get more accurate - try to find where team struct STARTS
        # by going backward until we find something that looks like start
        test_addr = search_base + phi_offset
        for offset in range(-100, 0, 4):
            check_addr = test_addr + offset
            raw = mem_read(hproc, check_addr, 4)
            if raw:
                val = struct.unpack('<I', raw)[0]
                # If we find a value that looks like team ID (small number), that's likely the team ID
                if 0 < val < 100:
                    team_addr = check_addr - 0x10
                    print('\n76ers team struct likely at: {}'.format(hex(team_addr)))
                    break
        else:
            team_addr = search_base + phi_offset - 0x10
            print('\n76ers team struct at (estimate): {}'.format(hex(team_addr)))
        
        # Now read team structure
        team_struct = mem_read(hproc, team_addr, 5700)  # Team size in 2k26 is ~5672
        if team_struct:
            print('\n=== Looking for playbook pointer in team struct ===')
            
            # Search for pointers in the 0x2FFCA000 range
            for i in range(0, len(team_struct) - 4, 4):
                val = struct.unpack('<I', team_struct[i:i+4])[0]
                # Look for pointers to any of our playbook addresses
                if 0x2FFCA000 <= val <= 0x2FFCB000:
                    print('Playbook pointer at team+0x{:x}: {}'.format(i, hex(val)))

CloseHandle(hproc)