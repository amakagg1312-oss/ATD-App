"""
Ultra-fast targeted snap/diff for playbook hunting.
Covers:
  1. Nick Nurse's full staff entry (604 bytes)
  2. All 80 staff entries (80 * 604 = ~48KB)
  3. Three manager objects from team struct (+0xFE8, +0xFF0, +0x12F8) - full 8KB each
  4. All 2nd-hop pointers from those manager objects (8-byte scan + 1KB reads)
  5. The 40-team franchise table at RVA+0x7E1E3D8 (full 840*40=33KB)
  6. Extended team struct region (+/- 1MB around team table)

Usage:
  python fast_watch.py snap    <- before change (takes < 2 seconds)
  python fast_watch.py diff    <- immediately after change (takes < 2 seconds)
  python fast_watch.py watch   <- live poll every 0.5s, prints changes
"""
import sys, os, struct, json, time, ctypes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)

SNAP_FILE = 'fast_snap.json'

FRANCHISE_RVA    = 0x7E1E3D8
FRANCHISE_STRIDE = 840
STAFF_RVA        = None  # resolved dynamically
STAFF_STRIDE     = 604
NUM_STAFF        = 80

def get_targets(hproc, module_base, table_base):
    """Return list of (label, base_addr, size) regions to watch."""
    targets = []

    # --- Team struct extended region (+-256KB around team table) ---
    targets.append(('team_ext', table_base - 0x40000, 0x80000 + TEAM_STRIDE * 42))

    # --- Manager objects from team struct ---
    team_data = mem_read(hproc, table_base, TEAM_STRIDE)
    if team_data:
        for off_name, off in [('team+FE8', 0x0FE8), ('team+FF0', 0x0FF0),
                               ('team+12F8', 0x12F8), ('team+10F8', 0x10F8),
                               ('team+1100', 0x1100), ('team+1108', 0x1108)]:
            if off + 8 <= TEAM_STRIDE:
                ptr = struct.unpack_from('<Q', team_data, off)[0]
                if 0x100000000 < ptr < 0xF00000000:
                    targets.append((off_name, ptr, 32768))  # 32KB each manager

    # --- Franchise table ---
    fbase_ptr = struct.unpack('<Q', mem_read(hproc, module_base + FRANCHISE_RVA, 8))[0]
    if 0x100000000 < fbase_ptr < 0xF00000000:
        targets.append(('franchise_table', fbase_ptr, FRANCHISE_STRIDE * 42))

    # --- Staff table (try multiple RVAs) ---
    for staff_rva in [0x7E1E358, 0x7E1E360, 0x7E1E368, 0x7E23D18]:
        try:
            sbase = struct.unpack('<Q', mem_read(hproc, module_base + staff_rva, 8))[0]
            if 0x100000000 < sbase < 0xF00000000:
                targets.append(('staff_rva_{:X}'.format(staff_rva), sbase,
                                 STAFF_STRIDE * NUM_STAFF))
                break
        except:
            pass

    # Deduplicate by address
    seen = set()
    unique = []
    for label, addr, size in targets:
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

def diff_snaps(snap_a, snap_b, table_base):
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

def print_diffs(results, table_base):
    for label, addr, diffs, data_a, data_b in results:
        # Group into blocks
        blocks = []
        blk = [diffs[0]]
        for d in diffs[1:]:
            if d[0] == blk[-1][0] + 1:
                blk.append(d)
            else:
                blocks.append(blk); blk = [d]
        blocks.append(blk)

        print('\n[{}] @ 0x{:X}  {:} bytes differ'.format(label, addr, len(diffs)))
        for blk in blocks[:12]:
            off = blk[0][0]
            abs_addr = addr + off
            raw_a = bytes(x[1] for x in blk[:4]).ljust(4, b'\x00')
            raw_b = bytes(x[2] for x in blk[:4]).ljust(4, b'\x00')
            u32_a = struct.unpack('<I', raw_a)[0]
            u32_b = struct.unpack('<I', raw_b)[0]
            u16_a = struct.unpack('<H', raw_a[:2])[0]
            u16_b = struct.unpack('<H', raw_b[:2])[0]
            hex_a = ' '.join('{:02X}'.format(x[1]) for x in blk[:8])
            hex_b = ' '.join('{:02X}'.format(x[2]) for x in blk[:8])
            # Is this a plausible playbook ID?
            playbook_flag = ''
            if (1 <= u32_a <= 200 or 1 <= u32_b <= 200) and len(blk) <= 4:
                playbook_flag = '  *** PLAYBOOK CANDIDATE ***'
            if (1 <= u16_a <= 200 or 1 <= u16_b <= 200) and len(blk) <= 2:
                playbook_flag = '  *** PLAYBOOK CANDIDATE (u16) ***'
            print('  +0x{:04X} (abs 0x{:X}): [{}] -> [{}]  u32: {} -> {}  u16: {} -> {}  ({} bytes){}'.format(
                off, abs_addr, hex_a, hex_b, u32_a, u32_b, u16_a, u16_b, len(blk), playbook_flag))

def main():
    if len(sys.argv) < 2:
        print('Usage: python fast_watch.py snap | diff | watch')
        sys.exit(0)

    cmd = sys.argv[1]
    pid = find_pid(GAME_EXE)
    module_base = get_module_base(pid, GAME_EXE)
    hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]
    print('Team table: 0x{:X}'.format(table_base))

    targets = get_targets(hproc, module_base, table_base)
    total_bytes = sum(s for _, _, s in targets)
    print('Watching {:} regions ({:.0f} KB total)'.format(len(targets), total_bytes/1024))
    for label, addr, size in targets:
        print('  {:25s} @ 0x{:X}  {:,} bytes'.format(label, addr, size))

    if cmd == 'snap':
        t0 = time.time()
        snap = snap_targets(hproc, targets)
        print('\nSnapped in {:.2f}s. Saved to {}'.format(time.time()-t0, SNAP_FILE))
        with open(SNAP_FILE, 'w') as f:
            json.dump({'table_base': hex(table_base),
                       'targets': [(l, hex(a), s) for l, a, s in targets],
                       'snap': {k: list(v) for k, v in snap.items()}}, f)
        print('CHANGE THE PLAYBOOK NOW, then run: python fast_watch.py diff')

    elif cmd == 'diff':
        if not os.path.exists(SNAP_FILE):
            print('Run snap first.'); kernel32.CloseHandle(hproc); return
        with open(SNAP_FILE) as f:
            saved = json.load(f)
        snap_A = {k: tuple(v) for k, v in saved['snap'].items()}

        t0 = time.time()
        snap_B_raw = snap_targets(hproc, targets)
        snap_B = {k: (a, d) for k, (a, d) in snap_B_raw.items()}
        print('Diff read in {:.2f}s'.format(time.time()-t0))

        # Convert snap_A to same format
        snap_A_fmt = {}
        for k, (a, d) in snap_A.items():
            snap_A_fmt[k] = (int(a, 16) if isinstance(a, str) else a, d)

        results = diff_snaps(snap_A_fmt, snap_B, table_base)
        if not results:
            print('\nNo changes detected in watched regions!')
            print('The playbook might be stored elsewhere. Try extending the scan.')
        else:
            print('\n=== DIFF RESULTS ===')
            print_diffs(results, table_base)

    elif cmd == 'watch':
        print('\nTaking baseline...')
        snap_a = snap_targets(hproc, targets)
        snap_a_fmt = {k: (a, d) for k, (a, d) in snap_a.items()}
        print('Watching for changes (Ctrl+C to stop)...')
        poll = 0
        try:
            while True:
                time.sleep(0.5)
                poll += 1
                snap_b_raw = snap_targets(hproc, targets)
                snap_b = {k: (a, d) for k, (a, d) in snap_b_raw.items()}
                results = diff_snaps(snap_a_fmt, snap_b, table_base)
                if results:
                    print('\n[{}] CHANGES DETECTED:'.format(time.strftime('%H:%M:%S')))
                    print_diffs(results, table_base)
                    # Update baseline for next poll
                    snap_a_fmt = snap_b
                elif poll % 20 == 0:
                    print('[{}] Polling... ({} polls)'.format(
                        time.strftime('%H:%M:%S'), poll))
        except KeyboardInterrupt:
            print('\nStopped.')

    kernel32.CloseHandle(hproc)

if __name__ == '__main__':
    main()
