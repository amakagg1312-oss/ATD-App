"""
Real-time playbook change detector.
Polls the volatile entry at 20ms. When byte[3] changes (playbook switch detected),
immediately scan a broad region to catch what else changed in the same frame.

Regions scanned every tick:
- Module .data: RVA+0x6000000 to RVA+0x8800000 (38MB) split into 128KB chunks
  (too slow at 20ms — instead: focused regions)
- All level-1 and level-2 pointer targets from team[0]
- Specific manager objects
"""
import sys, struct, time, ctypes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]

ADDR_MIN = 0x10000
ADDR_MAX = 0x7FFFFFFFFFFF

def is_ptr(v):
    return ADDR_MIN < v < ADDR_MAX

def read_pb_id():
    e = mem_read(hproc, module_base + 0x741F9E0, 16)
    if e:
        return e[3], struct.unpack_from('<Q', e, 8)[0]
    return None, None

# Build snapshot regions: all team[0] level-1 pointer targets (512 bytes each)
# Plus module .data 8KB chunks around the volatile entries
t0data = mem_read(hproc, table_base, TEAM_STRIDE)
regions = []

# Team struct itself
regions.append(('team0_raw', table_base, TEAM_STRIDE))

# Level-1 pointer targets (512 bytes each)
for off in range(0, TEAM_STRIDE - 7, 8):
    ptr = struct.unpack_from('<Q', t0data, off)[0]
    if is_ptr(ptr) and ptr != table_base:
        regions.append(('t0+{:X}->{:X}'.format(off, ptr), ptr, 512))

# Module .data: 4KB windows spaced 64KB apart across the volatile entry neighborhood
# and across the broader .data section
for rva_base in range(0x7000000, 0x8800000, 0x10000):
    regions.append(('data_{:X}'.format(rva_base), module_base + rva_base, 4096))

# Deduplicate by address
seen_addrs = set()
unique_regions = []
for label, addr, size in regions:
    if addr not in seen_addrs:
        seen_addrs.add(addr)
        unique_regions.append((label, addr, size))

print('Monitoring {} regions  ({:.0f} KB total)'.format(
    len(unique_regions), sum(s for _, _, s in unique_regions) / 1024))
print('Waiting for playbook change (press the cycle button in game)...')
print('Ctrl+C to stop\n')

# Baseline
pb_id_cur, pb_obj_cur = read_pb_id()
print('Current: playbook={} obj=0x{:X}'.format(pb_id_cur, pb_obj_cur))

def snap_all():
    return {label: (addr, bytes(mem_read(hproc, addr, size) or b''))
            for label, addr, size in unique_regions}

snap_prev = snap_all()
print('Baseline taken. Watching...\n')

try:
    while True:
        time.sleep(0.02)  # 20ms poll
        pb_id_new, pb_obj_new = read_pb_id()
        if pb_id_new is None:
            continue
        if pb_id_new != pb_id_cur:
            # Playbook changed! Immediately snap everything
            snap_now = snap_all()
            print('[CHANGE DETECTED] {} -> {}  obj: 0x{:X} -> 0x{:X}'.format(
                pb_id_cur, pb_id_new, pb_obj_cur, pb_obj_new))
            print('Diff vs previous:')
            found_any = False
            for label, addr, size in unique_regions:
                if label not in snap_prev or label not in snap_now:
                    continue
                _, data_a = snap_prev[label]
                _, data_b = snap_now[label]
                mn = min(len(data_a), len(data_b))
                diffs = [(i, data_a[i], data_b[i]) for i in range(mn) if data_a[i] != data_b[i]]
                if not diffs:
                    continue
                # Skip the known volatile entries (already known)
                label_rva = addr - module_base
                if 0x741F000 <= label_rva <= 0x742000:
                    continue
                found_any = True
                print('  [{}] @ 0x{:X}: {} bytes changed'.format(label, addr, len(diffs)))
                for i, old, new in diffs[:8]:
                    raw_a = data_a[i:i+4].ljust(4, b'\x00')
                    raw_b = data_b[i:i+4].ljust(4, b'\x00')
                    u32_a = struct.unpack('<I', raw_a[:4])[0]
                    u32_b = struct.unpack('<I', raw_b[:4])[0]
                    flag = '  *** PB CANDIDATE ***' if (1 <= old <= 60 or 1 <= new <= 60) and u32_b < 0x1000 else ''
                    print('    +0x{:04X} (abs 0x{:X}): {} -> {}  u32:{}->{}{}'.format(
                        i, addr + i, old, new, u32_a, u32_b, flag))
            if not found_any:
                print('  (no changes outside known volatile entries)')
            # Update baselines
            pb_id_cur, pb_obj_cur = pb_id_new, pb_obj_new
            snap_prev = snap_now
            print()
except KeyboardInterrupt:
    print('\nStopped.')

kernel32.CloseHandle(hproc)
