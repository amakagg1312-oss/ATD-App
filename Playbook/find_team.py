import struct
import ctypes
from ctypes import wintypes
import sys
import io
import json

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

# Search for 76ers team data
# Look for "PHI" or team ID patterns
print('=== Searching for 76ers team data ===')

# Search in team data region (typically around 0x2FFB0000 - 0x2FFC0000)
search_start = 0x2FFB0000
search_size = 0x20000

data = mem_read(hproc, search_start, search_size)
if data:
    # Look for PHI (76ers abbreviation)
    pos = data.find(b'PHI\x00\x00')
    if pos >= 0:
        print('Found PHI at offset {} from base {}'.format(pos, hex(search_start)))
        
        # Get the team struct base
        team_base = search_start + pos - 100  # Go back a bit to get start
        
        # Read around this area to find team data
        team_data = mem_read(hproc, team_base, 2000)
        if team_data:
            print('Team data at {}'.format(hex(team_base)))
            
            # Search for playbook pointer pattern
            # Look for pointers to our known playbook region
            for i in range(0, len(team_data) - 4, 4):
                val = struct.unpack('<I', team_data[i:i+4])[0]
                # Check if it points in the playbook area
                if 0x2FFCA000 <= val <= 0x2FFCB000:
                    print('Possible playbook pointer at offset {}: {}'.format(i, hex(val)))

# Also search more broadly for team structures
print('\n=== Searching for 76ers (PHI) team structure ===')

# Try different team base addresses from 2k26_offsets.json
# The team struct is typically at a known base + team_index * teamSize
# Team size is 5672 bytes

# First, find the team data pointers from known base
base_pointers = [0x2d100000]  # Common team area, adjust as needed

# Search for PHI in a wider area
for base in range(0x2d000000, 0x2d100000, 0x10000):
    try:
        data = mem_read(hproc, base, 0x10000)
        if data and b'PHI' in data[:100]:
            print('Found PHI at base {}'.format(hex(base)))
    except:
        pass

# If not found, try searching for the exact offsets we know about playbook
# from 2k26_offsets.json, the playbook offset is around offset ~200+ in team

print('\n=== Looking at known team structures ===')

# Try finding teams and their playbook pointers
# Team data typically has team ID at start, then different attributes

# Let's read the first few KB and look for patterns
# Use the earlier playbook address as reference

# Get the playbook array addresses we know
playbook_addrs = [0x2FFCA1910, 0x2FFCA19D0]

# Search backwards from playbook to find team reference
for playbook_addr in playbook_addrs:
    print('\nSearching around {}'.format(hex(playbook_addr)))
    # Read 0x200 bytes before playbook
    search_data = mem_read(hproc, playbook_addr - 0x200, 0x200)
    if search_data:
        # Look for pointers to this playbook
        for i in range(0, len(search_data) - 4, 4):
            val = struct.unpack('<I', search_data[i:i+4])[0]
            if val == playbook_addr:
                print('  Found reference at offset {} from {}'.format(i, hex(playbook_addr - 0x200 + i)))

# Let's try a different approach: dump all teams and look for PHI
print('\n=== Trying to scan for team structures ===')

# Use a base address we might find from game offsets
# Try scanning memory for team-like structures

# Search larger region for PHI team
search_regions = [
    (0x2FF800000, 0x100000),
    (0x2FF000000, 0x100000),
    (0x2d000000, 0x200000),
]

for base, size in search_regions:
    data = mem_read(hproc, base, size)
    if data:
        pos = data.find(b'PHI')
        if pos >= 0:
            print('Found PHI at {} + {}'.format(hex(base), pos))
            # Show context
            start = max(0, pos - 20)
            print('Context: {}'.format(data[start:pos+30]))

CloseHandle(hproc)