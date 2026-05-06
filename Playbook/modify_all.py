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

# Let's write a completely different, very recognizable play
# I'll use offset 550 for FIST 21 IVERSON to many different arrays and check if any shows

# First find ALL possible playbook arrays (anywhere in memory 0x2FFxxxxxx range that contains 60 plays)
# Then modify ALL of them with the same offset

print('=== Finding and modifying ALL possible playbook arrays ===')

target_offset = 9999  # Unique marker value

# Search the full expected range for 60-element arrays
# Scan in chunks and find arrays of offsets < 0x10000

scan_start = 0x2FF80000
scan_end = 0x2FFCF0000

found = 0
modified = []

# Scan by increments
check_interval = 0x1000  # 4KB

current = scan_start
while current < scan_end:
    try:
        # Read a chunk
        data = mem_read(hproc, current, 0x1000)
        if data:
            # Look for patterns of small offsets
            # For each potential array
            for offset_in_chunk in range(0, len(data)-(60*4), 4):
                try:
                    # Check first offset value
                    first = struct.unpack('<I', data[offset_in_chunk:offset_in_chunk+4])[0]
                    if first > 0 and first < 0x10000:
                        # Potentially valid array - verify by checking more
                        potential_base = current + offset_in_chunk
                        
                        # Read 10 more to check pattern  
                        test_data = mem_read(hproc, potential_base + 8*4, 20)
                        if test_data:
                            all_small = True
                            for i in range(0, 20, 4):
                                val = struct.unpack('<I', test_data[i:i+4])[0]
                                if val > 0x10000:
                                    all_small = False
                                    break
                            
                            if all_small:  # Looks like play offsets
                                # This is likely a playbook - modify index 0 to our test value
                                target = potential_base
                                
                                if mem_write(hproc, target, struct.pack('<I', target_offset)):
                                    modified.append(hex(target))
                                    found += 1
                except:
                    pass
    except:
        pass
    
    current += check_interval
    
    if found >= 20:
        break

print('Found {} potential arrays, modified {} of them'.format(found, len(modified)))
print('Modified addresses:')
for addr in modified[:10]:
    print('  {}'.format(addr))

# Now the game uses this offset 9999 - which should NOT resolve to any play
# (it's out of range) so hopefully you'd see an EMPTY or unknown play if mapping works

print('\n\nDone! Please check the game:')
print('- Go to 76ers playbook')
print('- Look for any BLANK or UNKNOWN play entries')
print('- Tell me what you see!')

CloseHandle(hproc)