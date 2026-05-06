# Compare playbook snapshots to find changes
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

SCAN_START = 0x24000000
SCAN_END = 0x24100000

print("Taking new snapshot...")

playbooks = []
chunk_size = 0x10000

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
            plays = []
            for j in range(max_check):
                offset = i + 4 + j * 4
                if offset + 4 <= len(raw):
                    v = struct.unpack('<I', raw[offset:offset+4])[0]
                    if 1 <= v <= 12506:
                        valid += 1
                        plays.append(v)
            
            if valid >= max_check * 0.8:
                addr = chunk_base + i
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
                    'valid': valid,
                    'plays_str': str(all_plays)
                })

print(f"Found {len(playbooks)} playbook structures")

# Load previous snapshot
with open("D:/project/Playbook/playbook_snapshot.json", 'r') as f:
    old_snapshot = json.load(f)

old_playbooks = {}
for pb in old_snapshot['playbooks']:
    pb['plays_str'] = str(pb.get('plays', []))
    old_playbooks[pb['addr']] = pb

print("\nComparing snapshots...")

changes = []
for pb in playbooks:
    addr = pb['addr']
    if addr in old_playbooks:
        old = old_playbooks[addr]
        if pb['plays_str'] != old['plays_str']:
            changes.append({
                'addr': addr,
                'old_count': old['count'],
                'new_count': pb['count'],
                'old_plays': old['plays'],
                'new_plays': pb['plays']
            })

if changes:
    print(f"\nFound {len(changes)} changed playbooks:")
    for c in changes[:5]:
        print(f"\n  {c['addr']}:")
        print(f"    Old count: {c['old_count']}, New count: {c['new_count']}")
        print(f"    Old plays: {c['old_plays'][:15]}")
        print(f"    New plays: {c['new_plays'][:15]}")
        
        # Find the specific difference
        old_set = set(c['old_plays'])
        new_set = set(c['new_plays'])
        added = new_set - old_set
        removed = old_set - new_set
        if added:
            print(f"    Added: {added}")
        if removed:
            print(f"    Removed: {removed}")
else:
    print("\nNo changes found in scanned range")

# Also check for new playbooks not in old snapshot
new_addrs = set(pb['addr'] for pb in playbooks)
old_addrs = set(old_playbooks.keys())
new_only = new_addrs - old_addrs
if new_only:
    print(f"\nNew playbook addresses: {new_only}")

CloseHandle(hproc)