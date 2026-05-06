# Scan broader memory for playbook changes
import ctypes
from ctypes import wintypes, byref, c_size_t, create_string_buffer
import struct
import json

kern = ctypes.WinDLL('kernel32', use_last_error=True)
hproc = kern.OpenProcess(0x1F0FFF, False, 38868)
if not hproc:
    print('Could not open process')
    exit()

CloseHandle = kern.CloseHandle

# Scan larger range
SCAN_START = 0x23000000
SCAN_END = 0x25000000

print(f"Scanning {hex(SCAN_START)}-{hex(SCAN_END)}...")

playbooks = []
chunk_size = 0x100000  # 1MB chunks

for chunk_base in range(SCAN_START, SCAN_END, chunk_size):
    buf = create_string_buffer(chunk_size)
    if not kern.ReadProcessMemory(hproc, ctypes.c_void_p(chunk_base), buf, chunk_size, byref(c_size_t(0))):
        continue
    
    raw = buf.raw
    
    for i in range(0, len(raw) - 8, 4):
        count = struct.unpack('<I', raw[i:i+4])[0]
        if 1 <= count <= 125:
            max_check = min(count, 10)
            valid = 0
            for j in range(max_check):
                offset = i + 4 + j * 4
                if offset + 4 <= len(raw):
                    v = struct.unpack('<I', raw[offset:offset+4])[0]
                    if 1 <= v <= 12506:
                        valid += 1
            
            if valid >= max_check * 0.8:
                addr = chunk_base + i
                plays = []
                for j in range(count):
                    offset = i + 4 + j * 4
                    if offset + 4 <= len(raw):
                        v = struct.unpack('<I', raw[offset:offset+4])[0]
                        plays.append(v)
                
                playbooks.append({
                    'addr': hex(addr),
                    'count': count,
                    'plays': plays,
                    'plays_str': str(plays)
                })

print(f"Found {len(playbooks)} playbook structures")

# Load old and compare
with open("D:/project/Playbook/playbook_snapshot.json", 'r') as f:
    old_snapshot = json.load(f)

old_playbooks = {}
for pb in old_snapshot['playbooks']:
    old_playbooks[pb['addr']] = pb

print("\nComparing...")
for pb in playbooks:
    addr = pb['addr']
    if addr in old_playbooks:
        if pb['plays_str'] != old_playbooks[addr].get('plays_str', ''):
            print(f"\nChanged: {addr}")
            old = old_playbooks[addr]
            print(f"  Count: {old['count']} -> {pb['count']}")
            print(f"  Old: {old['plays'][:10]}")
            print(f"  New: {pb['plays'][:10]}")

# Check for new addresses
new_addrs = set(pb['addr'] for pb in playbooks)
old_addrs = set(old_playbooks.keys())
new_only = new_addrs - old_addrs
if new_only:
    print(f"\nNew addresses: {new_only}")
    for addr in list(new_only)[:10]:
        for pb in playbooks:
            if pb['addr'] == addr:
                print(f"  {addr}: count={pb['count']}, plays={pb['plays'][:10]}")

import json
CloseHandle(hproc)