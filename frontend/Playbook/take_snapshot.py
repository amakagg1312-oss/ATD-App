# Scan and store all playbook structures for diff
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct
import json
import os
import hashlib

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Scan range
SCAN_START = 0x24000000
SCAN_END = 0x24100000  # 1MB scan

print(f"Scanning {hex(SCAN_START)}-{hex(SCAN_END)} for playbook structures...")

playbooks = []

# Scan in chunks
chunk_size = 0x10000  # 64KB chunks
for chunk_base in range(SCAN_START, SCAN_END, chunk_size):
    buf = create_string_buffer(chunk_size)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(chunk_base), buf, chunk_size, byref(c_size_t(0))):
        continue
    
    raw = buf.raw
    
    # Look for any count value (1-125) followed by sequence of valid indices
    for i in range(0, len(raw) - 8, 4):
        count = struct.unpack('<I', raw[i:i+4])[0]
        if 1 <= count <= 125:
            # Verify it's a playbook by checking for valid play indices
            max_check = min(count, 10)  # Check first 10 plays
            valid = 0
            plays = []
            for j in range(max_check):
                offset = i + 4 + j * 4
                if offset + 4 <= len(raw):
                    v = struct.unpack('<I', raw[offset:offset+4])[0]
                    if 1 <= v <= 12506:
                        valid += 1
                        plays.append(v)
            
            if valid >= max_check * 0.8:  # At least 80% valid
                addr = chunk_base + i
                # Read all plays
                all_plays = []
                for j in range(count):
                    offset = i + 4 + j * 4
                    if offset + 4 <= len(raw):
                        v = struct.unpack('<I', raw[offset:offset+4])[0]
                        all_plays.append(v)
                
                playbooks.append({
                    'addr': hex(addr),
                    'count': count,
                    'plays': all_plays,
                    'valid': valid
                })

print(f"\nFound {len(playbooks)} playbook structures")

# Save snapshot
snapshot = {
    'timestamp': __import__('datetime').datetime.now().isoformat(),
    'scan_range': f"{hex(SCAN_START)}-{hex(SCAN_END)}",
    'playbooks': playbooks
}

with open("D:/project/Playbook/playbook_snapshot.json", 'w') as f:
    json.dump(snapshot, f, indent=2)

print("Saved to playbook_snapshot.json")
print("\nMake a change in-game, then run diff script.")
CloseHandle(hproc)