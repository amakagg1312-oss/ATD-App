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

# Find 76ers team AND find any pointer to our known playbook addresses
# Team size is 5672 bytes

# First find PHI in memory
search_base = 0x2d000000
search_size = 0x300000

phi_data = mem_read(hproc, search_base, search_size)
if phi_data:
    phi_pos = phi_data.find(b'PHI')
    if phi_pos >= 0:
        phi_name_addr = search_base + phi_pos
        
        # Try different team starts
        # Team ID should be small number within 30 (team index)
        # Try going back to find team ID
        test_starts = [phi_name_addr - 0x50, phi_name_addr - 0x40, phi_name_addr - 0x30, phi_name_addr - 0x20]
        
        for test_team_start in test_starts:
            try:
                team_id_data = mem_read(hproc, test_team_start, 4)
                if team_id_data:
                    team_id = struct.unpack('<I', team_id_data)[0]
                    if 0 < team_id < 50:
                        print('Found team at {}'.format(hex(test_team_start)))
                        
                        # Now scan FIRST 2000 bytes of team for any pointer to playbook range
                        team_struct = mem_read(hproc, test_team_start, 2000)
                        if team_struct:
                            playbook_ptrs = []
                            for offset in range(0, 2000, 4):
                                val = struct.unpack('<I', team_struct[offset:offset+4])[0]
                                
                                # Any pointer in range around our known playbooks
                                if 0x2FFCA000 <= val <= 0x2FFCB000:
                                    playbook_ptrs.append((offset, val))
                            
                            if playbook_ptrs:
                                print('FOUND playbook pointers in team at offsets:')
                                for off, addr in playbook_ptrs:
                                    print('  team+0x{:x} = {}'.format(off, hex(addr)))
                                
                                # Test by writing VALID offset to FIRST one we find
                                # Use a VALID play offset that we know works: 550
                                test_play_offset = 550
                                
                                write_addr = test_team_start + playbook_ptrs[0][0]
                                
                                if mem_write(hproc, write_addr, struct.pack('<I', test_play_offset)):
                                    print('\nWrote valid play offset {} to address {}'.format(test_play_offset, hex(write_addr)))
                                    
                                    # Verify
                                    verify = mem_read(hproc, write_addr, 4)
                                    if verify:
                                        print('Verification: {}'.format(struct.unpack('<I', verify)[0]))
                                
                                exit()
            except Exception as e:
                pass

# If not found above, search more broadly
print('Searching broader area for pointers to know playbook addresses in team area...')

# Search for any refs to 0x2FFCA1910 or 0x2FFCA19D0 in team region
known_addrs = [0x2FFCA1910, 0x2FFCA19D0]

for addr in known_addrs:
    search_bytes = struct.pack('<I', addr)
    
    # Search in team area
    search_data = mem_read(hproc, 0x2D000000, 0x400000)
    pos = search_data.find(search_bytes)
    if pos >= 0:
        found_addr = 0x2D000000 + pos
        print('Found reference to {} at {}'.format(hex(addr), hex(found_addr)))
        
        # This is our target - write test value here
        test_offset = 550
        
        if mem_write(hproc, found_addr, struct.pack('<I', test_offset)):
            print('Wrote {} to this location'.format(test_offset))
            
            # Verify
            verify = mem_read(hproc, found_addr, 4)
            if verify:
                retrieved = struct.unpack('<I', verify)[0]
                if retrieved == test_offset:
                    print('VERIFIED! Check game for change at first play position') 

CloseHandle(hproc)