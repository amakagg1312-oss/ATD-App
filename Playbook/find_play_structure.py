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

# Search for structures that look like: [count][play1_id][play1_type][play1_shot][play1_other...][play2_id]...
# Typical values:
# - play_id: 0-1700 (small integers)
# - play_type: maybe strings like ISO, PnR, POST
# - shot_index: Quick 1-4 = likely small values

# Search in team memory for count + multiple play entries
team_base = 0x2A82E17D0
stride = 5672

# Search for count (60-70) followed by 4+ entries with typical play structure sizes
# Each play entry might be 8-16 bytes

print('Searching team structures for playbook...')

team_data = mem_read(hproc, team_base, 0x1000)
if team_data:
    # Check several offsets we found earlier
    for off in range(0x300, 0x500, 4):
        count = struct.unpack('<I', team_data[off:off+4])[0]
        if 60 <= count <= 70:
            print('\nFound count={} at team+0x{:x}'.format(count, off))
            
            # Check structure after count
            # Entry could be: 4 bytes (id only), 8 bytes (id + type), 12 bytes (id + type + shot), 16 bytes, etc.
            entry_sizes = [4, 8, 12, 16, 20]
            
            for entry_size in entry_sizes:
                # Read a few entries
                entries = []
                for i in range(min(5, count)):
                    start = off + 4 + i * entry_size
                    if start + entry_size <= len(team_data):
                        entry_data = team_data[start:start+entry_size]
                        values = []
                        for j in range(0, entry_size, 4):
                            values.append(struct.unpack('<I', entry_data[j:j+4])[0])
                        entries.append(values)
                
                # Check if values look valid
                valid_entry = False
                for e in entries:
                    if entry_size == 8:
                        # id + type: id small, type small or char
                        if 0 <= e[0] <= 2000 and 0 <= e[1] <= 2000:
                            valid_entry = True
                    elif entry_size == 12:
                        # id + type + shot: id small, type small, shot small
                        if 0 <= e[0] <= 2000 and 0 <= e[1] <= 2000 and 0 <= e[2] <= 2000:
                            valid_entry = True
                
                if valid_entry:
                    print('  Entry size {} looks valid!'.format(entry_size))
                    for e in entries[:3]:
                        print('    Entry: {}'.format(e[:min(4, len(e))]))

CloseHandle(hproc)