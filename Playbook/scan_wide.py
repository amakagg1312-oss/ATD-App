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

# The game might use different memory mappings per-play
# Let's check: does the game read directly from our addresses when showing playbook?
# Let's find a better approach: scan for the EXACT pattern in our known play ORDER
# Screenshot shows: [FIST 21 IVERSON, FIST CHEST FLARE, MIL FIST 34, etc.]

# The in-game display shows 6 BLOB groups = 60 plays total
# BLOB_01 shows plays indexed 0-9 in menu order

# Let's search for the pattern of offsets we see in screenshot: [557, 712, 896, 1216...] in ORDER
# Or simply scan through a wider region to see what arrays look like playbook arrays

# Let's first try to find ALL the 60-play arrays in the game
# Using the pattern we know: each entry is 48 bytes (0x30) apart

print('=== Scanning wide memory for playbook arrays ===')

# Scan for 60-entry arrays of offsets in the play area
scan_base = 0x2FF80000  # Around play area
scan_size = 0x2000000

data = mem_read(hproc, scan_base, scan_size)
if data:
    print('Looking for sequences of small offsets...')
    found_arrays = 0
    
    # Look for sequences where offsets look like play pointers
    for start in range(0, len(data) - (60*4), 4):
        # Check first offset
        first_off = struct.unpack('<I', data[start:start+4])[0]
        
        # Should be small (< 0x10000) for play indexes
        if first_off > 0 and first_off < 0x10000:
            # This might be an array - check next few
            offsets = []
            for i in range(0, 50*4, 4):
                if start + i + 4 <= len(data):
                    val = struct.unpack('<I', data[start+i:start+i+4])[0]
                    offsets.append(val)
            
            # Valid play array should have mostly small offsets
            valid = sum(1 for o in offsets if o > 0 and o < 0x10000)
            if valid > 30:
                found_arrays += 1
                if found_arrays <= 5:
                    print('Found array at offset {} from base {}'.format(start, hex(scan_base)))
                    print('  First 10: {}'.format(offsets[:10]))
    
    print('Total candidate arrays: {}'.format(found_arrays))

# Let me try a simpler approach - verify what the game CAN modify
# Let's write to one specific location we found earlier that's DIFFERENT from the main ones we tested 

# Try scanning around team area for any playbook references
print('\n=== Looking near team for playbook ===')

team_base = 0x2d195000  # Team area
team_data = mem_read(hproc, team_base, 0x10000)
if team_data:
    # Look for any pointers in playbook range
    for i in range(0, len(team_data) - 4, 4):
        val = struct.unpack('<I', team_data[i:i+4])[0]
        if 0x2FFCA000 <= val <= 0x2FFCB000:
            print('Found playbook ref at team+0x{:x}: {}'.format(i, hex(val)))

# Try writing to 2FFCFAxxx addresses - sometimes they use a different memory map
print('\n=== Writing to alternative addresses ===')

# Try address near 0x2ffcfxxx
for base in [0x2ffcf0000, 0x2ffcf1000]:
    try:
        for i in range(10):
            addr = base + i*0x30
            data = struct.pack('<I', 0x1234 + i)  # Unique values
            if mem_write(hproc, addr, data):
                print('Wrote to {}'.format(hex(addr)))
    except:
        pass

CloseHandle(hproc)