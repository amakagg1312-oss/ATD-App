"""
fast_watch rewritten with corrected address range (catches < 4GB heap allocations).
Covers:
  - All manager objects from team struct offsets FE8/FF0/12F8/10F8/1100/1108
  - The u64[1] targets from the 11 volatile module .data entries
  - Team struct itself + surrounding region
  - Also reads deep into the playbook object chain

Usage:
  python fast_watch2.py snap
  python fast_watch2.py diff
  python fast_watch2.py watch
"""
import sys, os, struct, json, time, ctypes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)

SNAP_FILE = 'fast_snap2.json'

ADDR_MIN = 0x10000
ADDR_MAX = 0x7FFFFFFFFFFF

def is_ptr(v):
    return ADDR_MIN < v < ADDR_MAX

# Volatile module .data entries that hold the playbook ID in byte[3]
VOLATILE_RVAS = [
    0x741F380, 0x741F4B0, 0x741F4D0, 0x741F510,
    0x741F520, 0x741F540, 0x741F550, 0x741F9E0,
    0x741FA08, 0x741FAA8, 0x741FEB8,
]

def get_targets(hproc, module_base, table_base):
    targets = []

    # Team extended region
    targets.append(('team_ext', table_base - 0x40000, 0x80000 + TEAM_STRIDE * 42))

    # Manager objects from team struct (fixed range)
    team_data = mem_read(hproc, table_base, TEAM_STRIDE)
    if team_data:
        for name, off in [('team+FE8', 0x0FE8), ('team+FF0', 0x0FF0),
                          ('team+12F8', 0x12F8), ('team+10F8', 0x10F8),
                          ('team+1100', 0x1100), ('team+1108', 0x1108)]:
            if off + 8 <= TEAM_STRIDE:
                ptr = struct.unpack_from('<Q', team_data, off)[0]
                if is_ptr(ptr):
                    targets.append((name, ptr, 65536))  # 64KB each

        # Also scan ALL offsets for interesting pointers
        for off in range(0, TEAM_STRIDE - 7, 8):
            ptr = struct.unpack_from('<Q', team_data, off)[0]
            if is_ptr(ptr) and off not in range(0, 0x80, 8):  # skip first 0x80 (already covered)
                targets.append(('team_ptr_{:X}'.format(off), ptr, 4096))

    # u64[1] targets from the volatile module .data entries
    for rva in VOLATILE_RVAS:
        entry = mem_read(hproc, module_base + rva, 16)
        if entry:
            u64_1 = struct.unpack_from('<Q', entry, 8)[0]
            if is_ptr(u64_1):
                targets.append(('vol_u64_{:X}'.format(rva), u64_1, 65536))

    # Deduplicate by address
    seen = set()
    unique = []
    for item in targets:
        label, addr = item[0], item[1]
        size = item[2] if len(item) > 2 else 4096
        if addr not in seen:
            seen.add(addr)
            unique.append((label, addr, size))
    return unique

def snap_targets(hproc, targets):
    snap = {}
    for label, addr, size in targets:
        data = mem_read(hproc, addr, size)
        if data:
            snap[label] = (addr, data.hex())
    return snap

def diff_snaps(snap_a, snap_b):
    results = []
    for label in snap_a:
        if label not in snap_b:
            continue
        addr_a, hex_a = snap_a[label]
        addr_b, hex_b = snap_b[label]
        if addr_a != addr_b:
            continue
        data_a = bytes.fromhex(hex_a)
        data_b = bytes.fromhex(hex_b)
        mn = min(len(data_a), len(data_b))
        diffs = [(j, data_a[j], data_b[j]) for j in range(mn) if data_a[j] != data_b[j]]
        if diffs:
            results.append((label, addr_a, diffs, data_a, data_b))
    return results

def print_diffs(results):
    for label, addr, diffs, data_a, data_b in results:
        blocks = []
        blk = [diffs[0]]
        for d in diffs[1:]:
            if d[0] == blk[-1][0] + 1:
                blk.append(d)
            else:
                blocks.append(blk); blk = [d]
        blocks.append(blk)
        print('\n[{}] @ 0x{:X}  {} bytes differ'.format(label, addr, len(diffs)))
        for blk in blocks[:10]:
            off = blk[0][0]
            abs_addr = addr + off
            raw_a = bytes(x[1] for x in blk[:4]).ljust(4, b'\x00')
            raw_b = bytes(x[2] for x in blk[:4]).ljust(4, b'\x00')
            u32_a = struct.unpack('<I', raw_a)[0]
            u32_b = struct.unpack('<I', raw_b)[0]
            u16_a = struct.unpack('<H', raw_a[:2])[0]
            u16_b = struct.unpack('<H', raw_b[:2])[0]
            hex_a_s = ' '.join('{:02X}'.format(x[1]) for x in blk[:8])
            hex_b_s = ' '.join('{:02X}'.format(x[2]) for x in blk[:8])
            pb_flag = ''
            if (1 <= u32_a <= 60 or 1 <= u32_b <= 60) and len(blk) <= 4:
                pb_flag = '  *** PLAYBOOK CANDIDATE ***'
            print('  +0x{:04X} (0x{:X}): [{}]->[{}] u32:{}->{} u16:{}->{} ({} bytes){}'.format(
                off, abs_addr, hex_a_s, hex_b_s, u32_a, u32_b, u16_a, u16_b, len(blk), pb_flag))

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'
    pid = find_pid(GAME_EXE)
    module_base = get_module_base(pid, GAME_EXE)
    hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]
    print('team_table=0x{:X}'.format(table_base))

    targets = get_targets(hproc, module_base, table_base)
    total_kb = sum(s for _, _, s in targets) / 1024
    print('Watching {} regions ({:.0f} KB)'.format(len(targets), total_kb))

    if cmd == 'snap':
        t0 = time.time()
        snap = snap_targets(hproc, targets)
        elapsed = time.time() - t0
        print('Snapped {} regions in {:.2f}s'.format(len(snap), elapsed))
        with open(SNAP_FILE, 'w') as f:
            json.dump({'table_base': hex(table_base),
                       'targets': [(l, hex(a), s) for l, a, s in targets],
                       'snap': {k: list(v) for k, v in snap.items()}}, f)
        print('CHANGE THE PLAYBOOK NOW, then run: python fast_watch2.py diff')

    elif cmd == 'diff':
        if not os.path.exists(SNAP_FILE):
            print('Run snap first.'); kernel32.CloseHandle(hproc); return
        with open(SNAP_FILE) as f:
            saved = json.load(f)
        snap_A = {k: (int(a, 16) if isinstance(a, str) else a, d)
                  for k, (a, d) in saved['snap'].items()}

        t0 = time.time()
        snap_B_raw = snap_targets(hproc, targets)
        snap_B = {k: (a, d) for k, (a, d) in snap_B_raw.items()}
        print('Diff read in {:.2f}s'.format(time.time() - t0))

        results = diff_snaps(snap_A, snap_B)
        if not results:
            print('No changes detected!')
        else:
            print('=== DIFF RESULTS ===')
            print_diffs(results)

    elif cmd == 'watch':
        print('Baseline...')
        snap_a = snap_targets(hproc, targets)
        snap_a_fmt = {k: (a, d) for k, (a, d) in snap_a.items()}
        print('Watching (Ctrl+C to stop)...')
        poll = 0
        try:
            while True:
                time.sleep(0.5)
                poll += 1
                snap_b_raw = snap_targets(hproc, targets)
                snap_b = {k: (a, d) for k, (a, d) in snap_b_raw.items()}
                results = diff_snaps(snap_a_fmt, snap_b)
                if results:
                    print('\n[{}] CHANGES:'.format(time.strftime('%H:%M:%S')))
                    print_diffs(results)
                    snap_a_fmt = snap_b
                elif poll % 10 == 0:
                    print('[{}] polling...'.format(time.strftime('%H:%M:%S')))
        except KeyboardInterrupt:
            print('\nStopped.')

    kernel32.CloseHandle(hproc)

if __name__ == '__main__':
    main()
