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

# Found PHI at memory offset 1659611 from base 0x2d000000
phi_mem_offset = 1659611
search_base = 0x2d000000
phi_name_addr = search_base + phi_mem_offset

print('PHI name at: {}'.format(hex(phi_name_addr)))

# Find team struct start - go backwards until we find the team ID (small integer)
team_start = phi_name_addr
for offset in range(-200, 0, 4):
    check_addr = team_start + offset
    data = mem_read(hproc, check_addr, 4)
    if data:
        val = struct.unpack('<I', data)[0]
        # Team IDs are usually small numbers (0-30 range)
        if 0 < val <= 40:
            team_start = check_addr - 0x10  # A bit before the ID
            print('Found team ID at offset {}: {}'.format(offset, val))
            break

if team_start == phi_name_addr - 100:
    team_start = phi_name_addr - 0x30  # Default if not found
    
print('76ers team struct at: {}'.format(hex(team_start)))

# Now read the team struct and look for playbook pointer
team_struct = mem_read(hproc, team_start, 5700)
if team_struct:
    print('\n=== Team struct playbook references ===')
    
    # Known playbook address: 0x2FFCA19D0
    target_playbook = 0x2FFCA19D0
    
    # Find pointers to playbook array area
    for i in range(0, len(team_struct) - 4, 4):
        val = struct.unpack('<I', team_struct[i:i+4])[0]
        if 0x2FFCA000 <= val <= 0x2FFCB000:
            print('Possible playbook at team+0x{:x}: {}'.format(i, hex(val)))

# Now search for any pointer containing the known playbook addresses
# Our playbook at 0x2FFCA19D0 
# Search for this value in team struct

# Convert addresses to search for
addresses_to_find = [
    0x2FFCA1910,
    0x2FFCA19D0,
]

print('\n=== Searching for playbook pointers ===')

team_struct = mem_read(hproc, team_start, 5700)
for addr in addresses_to_find:
    # Search for this address
    search_val = struct.pack('<I', addr)
    
    # Convert to integer and search
    for i in range(0, len(team_struct) - 4, 4):
        val = struct.unpack('<I', team_struct[i:i+4])[0]
        if val == addr or (0x2FFCA000 <= val <= 0x2FFCB000):
            if i < 5000:  # Only look in first part of team struct
                print('Found pointer to {} at team+0x{:x}'.format(hex(addr), i))

# Let's do a different approach - look for the "playbook base" in team
# Usually the playbook pointer is at team+offset where offset 
# comes from the game offsets file

# Search more thoroughly throughout team structure for any 0x2FFCAxxx values
print('\n=== All playbook-like addresses in team ===')

for i in range(0, len(team_struct) - 4, 4):
    val = struct.unpack('<I', team_struct[i:i+4])[0]
    if 0x2FFC0000 <= val <= 0x2FFCF0000:
        # Print the offset and address
        print('[team+0x{:x}] {}'.format(i, hex(val)))

CloseHandle(hproc)