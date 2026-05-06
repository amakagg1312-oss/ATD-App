"""
Live memory watcher - polls all team-struct-adjacent heap pages every 0.5s,
prints any byte that changes. Run this BEFORE changing the playbook in-game.
Press Ctrl+C to stop.
"""
import sys, struct, time, ctypes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playbook_scanner import (find_pid, get_module_base, mem_read,
                               GAME_EXE, PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE, enumerate_regions)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]
print('Team table: 0x{:X}'.format(table_base))

# Build list of all pointer targets from the 76ers team struct
team_data = mem_read(hproc, table_base, TEAM_STRIDE)
watch_regions = []

# Add the team struct itself
watch_regions.append(('team_struct', table_base, TEAM_STRIDE))

# Add all 5 team structs (76ers + next 4 to detect cross-team changes)
for i in range(5):
    watch_regions.append(('team[{}]'.format(i), table_base + i * TEAM_STRIDE, TEAM_STRIDE))

# Add all pointer targets (64KB each)
for i in range(0, TEAM_STRIDE - 7, 8):
    val = struct.unpack_from('<Q', team_data, i)[0]
    if 0x100000000 < val < 0x7FF000000000:
        watch_regions.append(('ptr+0x{:04X}'.format(i), val, 65536))

# Add 2MB around the team struct (wider net)
watch_regions.append(('heap_near_team', table_base - 0x100000, 0x200000))

# Deduplicate and sort
seen = set()
unique_regions = []
for label, base, size in watch_regions:
    key = (base, size)
    if key not in seen:
        seen.add(key)
        unique_regions.append((label, base, size))

print('Watching {} memory regions ({} total bytes)'.format(
    len(unique_regions), sum(s for _, _, s in unique_regions)))
print('Taking baseline snapshot...')

# Take baseline
baseline = {}
for label, base, size in unique_regions:
    d = mem_read(hproc, base, size)
    if d:
        baseline[(label, base)] = d

print('Baseline captured. NOW CHANGE THE PLAYBOOK IN-GAME.')
print('Any memory changes will appear below:')
print('-' * 60)

try:
    poll_count = 0
    while True:
        time.sleep(0.3)
        poll_count += 1
        changes_found = []

        for label, base, size in unique_regions:
            key = (label, base)
            if key not in baseline:
                continue
            cur = mem_read(hproc, base, size)
            if not cur:
                continue
            prev = baseline[key]
            min_len = min(len(prev), len(cur))
            diffs = [(j, prev[j], cur[j]) for j in range(min_len) if prev[j] != cur[j]]
            if diffs:
                changes_found.append((label, base, diffs))
                baseline[key] = cur  # update baseline to track further changes

        if changes_found:
            ts = time.strftime('%H:%M:%S')
            for label, base, diffs in changes_found:
                # Group diffs into blocks
                blocks = []
                blk = [diffs[0]]
                for d in diffs[1:]:
                    if d[0] == blk[-1][0] + 1: blk.append(d)
                    else: blocks.append(blk); blk = [d]
                blocks.append(blk)
                for blk in blocks[:5]:
                    off = blk[0][0]
                    raw_a = bytes(x[1] for x in blk[:4]).ljust(4, b'\x00')
                    raw_b = bytes(x[2] for x in blk[:4]).ljust(4, b'\x00')
                    u32_a = struct.unpack('<I', raw_a)[0]
                    u32_b = struct.unpack('<I', raw_b)[0]
                    abs_addr = base + off
                    hex_a = ' '.join('{:02X}'.format(x[1]) for x in blk[:8])
                    hex_b = ' '.join('{:02X}'.format(x[2]) for x in blk[:8])
                    print('[{}] {} +0x{:X} (abs 0x{:X}) {} bytes: [{}]->[{}]  u32: {} -> {}'.format(
                        ts, label, off, abs_addr, len(blk), hex_a[:23], hex_b[:23], u32_a, u32_b))

        if poll_count % 20 == 0:
            print('[{}] Polling... ({} polls so far)'.format(time.strftime('%H:%M:%S'), poll_count))

except KeyboardInterrupt:
    print('\nStopped.')

kernel32.CloseHandle(hproc)
