# Find large playbooks (50+ plays) in current memory
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

SCAN_START = 0x23000000
SCAN_END = 0x25000000

print(f"Searching for large playbooks (count >= 50)...")
large_playbooks = []

chunk_size = 0x100000
for chunk_base in range(SCAN_START, SCAN_END, chunk_size):
    buf = create_string_buffer(chunk_size)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(chunk_base), buf, chunk_size, byref(c_size_t(0))):
        continue
    
    raw = buf.raw
    
    for i in range(0, len(raw) - 300, 4):
        count = struct.unpack('<I', raw[i:i+4])[0]
        if 50 <= count <= 125:
            # Find valid plays
            plays = []
            for j in range(count):
                offset = i + 4 + j * 4
                if offset + 4 <= len(raw):
                    v = struct.unpack('<I', raw[offset:offset+4])[0]
                    if 1 <= v <= 12506:
                        plays.append(v)
            
            valid = len(plays)
            if valid >= 40:  # At least 40 valid plays
                addr = chunk_base + i
                large_playbooks.append({
                    'addr': hex(addr),
                    'count': count,
                    'valid': valid,
                    'plays': plays
                })

print(f"\nFound {len(large_playbooks)} large playbooks")
for pb in large_playbooks[:10]:
    print(f"\n{pb['addr']}: count={pb['count']}, valid={pb['valid']}")
    print(f"  plays: {pb['plays'][:15]}...")
    print(f"  last 5: {pb['plays'][-5:]}")

CloseHandle(hproc)