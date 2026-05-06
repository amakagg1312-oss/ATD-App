# Search for playbook in 0x2407c000-0x2407d000 range more carefully
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

print("Scanning 0x2407c000-0x2407d000 for playbook structures...")
found_plays = []

# Read the entire range and scan for valid play sequences
chunk_size = 0x1000
for base in range(0x2407c000, 0x2407d000, chunk_size):
    data = create_string_buffer(chunk_size)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(base), data, chunk_size, byref(c_size_t(0))):
        continue
    
    # Look for count followed by sequence of valid play indices
    for offset in range(0, chunk_size - 8, 4):
        count = struct.unpack('<I', data.raw[offset:offset+4])[0]
        if 60 <= count <= 80:
            # Check if this offset has enough room for plays
            play_start = offset + 4
            max_plays = min(count, (chunk_size - play_start) // 4)
            if max_plays < count:
                continue
            
            # Read plays
            plays = []
            for j in range(count):
                if play_start + j*4 + 4 <= chunk_size:
                    v = struct.unpack('<I', data.raw[play_start + j*4:play_start + (j+1)*4])[0]
                    plays.append(v)
                else:
                    break
            
            valid = sum(1 for p in plays if 1 <= p <= 12506)
            if valid >= count * 0.8:
                addr = base + offset
                found_plays.append((addr, count, valid, plays[:10]))
                print(f"  {hex(addr)}: count={count}, valid={valid}, first 10: {plays[:10]}")

print(f"\nFound {len(found_plays)} potential playbook structures")
CloseHandle(hproc)