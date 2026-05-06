"""
Global page-level diff scanner.
Step 1: python page_diff.py snap   -> saves ALL committed RW pages to page_snap_A.bin
Step 2: Change playbook in-game
Step 3: python page_diff.py diff   -> byte-level diff of changed pages

The snapshot uses: 8-byte addr + 4-byte size + raw bytes per region (LZ4-like grouping).
Typical game process: ~1-3GB committed RW -> stored as 2-4GB compressed. Too large.

ALTERNATIVE: checksum scan first (4MB), then re-snap only changed pages.
  python page_diff.py checksum    -> saves page checksums
  python page_diff.py checkdiff   -> finds changed pages, re-reads them, diffs vs stored checksums
                                     (can't byte-diff without old data — just reports WHICH pages changed)

RECOMMENDED WORKFLOW:
  python page_diff.py snap        -> saves only pages within a targeted 64MB range + all pointed-to regions
  (change playbook)
  python page_diff.py diff        -> full byte diff
"""
import sys, os, struct, ctypes, json, hashlib, time, zlib
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, enumerate_regions,
                               GAME_EXE, PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)

PAGE_SIZE  = 4096
SNAP_A_BIN = 'page_snap_A.bin'
CHECK_FILE = 'page_checksums.json'

# ─── helpers ──────────────────────────────────────────────────────────────────

def checksum_page(data):
    if len(data) < 8:
        return 0
    result = 0
    for i in range(0, len(data) - 7, 8):
        result ^= struct.unpack_from('<Q', data, i)[0]
    return result

def get_all_regions(hproc):
    return enumerate_regions(hproc)

# ─── CHECKSUM mode: fast, covers ALL memory ───────────────────────────────────

def cmd_checksum(hproc, table_base):
    print('Enumerating all committed RW pages (checksum only)...')
    t0 = time.time()
    regions = get_all_regions(hproc)
    snap = []  # list of [addr, checksum]
    total_bytes = 0
    for base, size in regions:
        chunk_size = 262144
        for off in range(0, size, chunk_size):
            addr = base + off
            length = min(chunk_size, size - off)
            data = mem_read(hproc, addr, length)
            if not data:
                continue
            for po in range(0, len(data), PAGE_SIZE):
                page = data[po:po+PAGE_SIZE]
                if len(page) < 16:
                    continue
                snap.append([addr + po, checksum_page(page)])
                total_bytes += len(page)
    elapsed = time.time() - t0
    print('Checksummed {:,} pages ({:.0f} MB) in {:.1f}s'.format(
        len(snap), total_bytes/1e6, elapsed))
    with open(CHECK_FILE, 'w') as f:
        json.dump(snap, f)
    print('Saved to {}'.format(CHECK_FILE))
    print()
    print('NOW CHANGE THE PLAYBOOK IN-GAME, then run: python page_diff.py checkdiff')

def cmd_checkdiff(hproc, table_base):
    if not os.path.exists(CHECK_FILE):
        print('Run "python page_diff.py checksum" first.'); return
    with open(CHECK_FILE) as f:
        old_list = json.load(f)
    old_snap = {addr: cs for addr, cs in old_list}
    print('Loaded {:,} pages from {}'.format(len(old_snap), CHECK_FILE))

    print('Re-checksumming all pages...')
    t0 = time.time()
    regions = get_all_regions(hproc)
    changed = []
    new_pages = []
    for base, size in regions:
        chunk_size = 262144
        for off in range(0, size, chunk_size):
            addr = base + off
            length = min(chunk_size, size - off)
            data = mem_read(hproc, addr, length)
            if not data:
                continue
            for po in range(0, len(data), PAGE_SIZE):
                page = data[po:po+PAGE_SIZE]
                if len(page) < 16:
                    continue
                pa = addr + po
                cs_b = checksum_page(page)
                if pa not in old_snap:
                    new_pages.append(pa)
                elif old_snap[pa] != cs_b:
                    changed.append((pa, page))
    elapsed = time.time() - t0
    print('Done in {:.1f}s. Changed pages: {:,}  New pages: {:,}'.format(
        elapsed, len(changed), len(new_pages)))

    if not changed and not new_pages:
        print('\nNo changes detected. Did you actually change the playbook?')
        return

    # Categorize and report
    print('\n=== CHANGED PAGES ===')
    team_pages = []
    other_pages = []
    for addr, _ in changed:
        if table_base - 0x400000 <= addr <= table_base + 0x800000:
            team_pages.append(addr)
        else:
            other_pages.append(addr)

    if team_pages:
        print('\n[NEAR TEAM STRUCT] {:} pages:'.format(len(team_pages)))
        for addr in sorted(team_pages)[:30]:
            print('  0x{:X}  (offset from team table: {:+d})'.format(
                addr, addr - table_base))
    if other_pages:
        print('\n[OTHER REGIONS] {:} pages (showing first 30):'.format(len(other_pages)))
        for addr in sorted(other_pages)[:30]:
            print('  0x{:X}'.format(addr))

    if new_pages:
        print('\n[NEWLY ALLOCATED] {:} pages (showing first 10):'.format(len(new_pages)))
        for addr in sorted(new_pages)[:10]:
            print('  0x{:X}'.format(addr))

    # Save the changed page addresses for further investigation
    result = {
        'team_table': hex(table_base),
        'changed_pages': [hex(a) for a, _ in changed],
        'new_pages': [hex(a) for a in new_pages[:20]],
    }
    with open('changed_pages.json', 'w') as f:
        json.dump(result, f, indent=2)
    print('\nSaved page list to changed_pages.json')
    print('\nNow run: python page_diff.py investigate')

def cmd_investigate(hproc, table_base):
    """Read 64B context around each changed page and look for small ints (playbook IDs)."""
    if not os.path.exists('changed_pages.json'):
        print('Run checkdiff first.'); return
    with open('changed_pages.json') as f:
        data = json.load(f)
    pages = [int(p, 16) for p in data.get('changed_pages', [])]
    if not pages:
        print('No changed pages to investigate.'); return

    print('Investigating {:} changed pages for playbook-related values...'.format(len(pages)))
    for page_addr in sorted(pages)[:100]:
        cur = mem_read(hproc, page_addr, PAGE_SIZE)
        if not cur:
            continue
        # Look for small integers (1-200) that could be playbook IDs
        small_ints_32 = []
        for j in range(0, PAGE_SIZE - 3, 4):
            v = struct.unpack_from('<I', cur, j)[0]
            if 1 <= v <= 200:
                small_ints_32.append((j, v))

        small_ints_16 = []
        for j in range(0, PAGE_SIZE - 1, 2):
            v = struct.unpack_from('<H', cur, j)[0]
            if 1 <= v <= 200:
                small_ints_16.append((j, v))

        # Only print pages with few small ints (more likely to be data, not code)
        if 0 < len(small_ints_32) <= 30:
            print('\n  Page 0x{:X} (off from team: {:+d}):'.format(
                page_addr, page_addr - table_base))
            print('    uint32 small(1-200): {}'.format(small_ints_32[:12]))
            # Hex dump first 64 bytes
            hex_s = ' '.join('{:02X}'.format(b) for b in cur[:64])
            asc   = ''.join(chr(b) if 32<=b<127 else '.' for b in cur[:32])
            print('    First 64B: {}  {}'.format(hex_s[:47], asc))


# ─── TARGETED SNAP mode: store full data for pages near team + all pointers ───

def cmd_snap(hproc, table_base):
    """Store full page data for a targeted region (fast, ~30MB)."""
    team_data = mem_read(hproc, table_base, TEAM_STRIDE)

    # Collect targeted regions
    targets = []
    # 8MB around team struct
    targets.append((table_base - 0x200000, 0x800000))
    # All pointer targets (1MB each)
    for i in range(0, TEAM_STRIDE - 7, 8):
        val = struct.unpack_from('<Q', team_data, i)[0]
        if 0x100000000 < val < 0x7FF000000000:
            # Align to page
            base = val & ~(PAGE_SIZE - 1)
            targets.append((base, 1048576))  # 1MB per pointer

    # Deduplicate / merge overlapping ranges
    targets.sort()
    merged = []
    for base, size in targets:
        if merged and base <= merged[-1][0] + merged[-1][1]:
            end = max(merged[-1][0] + merged[-1][1], base + size)
            merged[-1] = (merged[-1][0], end - merged[-1][0])
        else:
            merged.append([base, size])

    total_bytes = sum(s for _, s in merged)
    print('Targeted snap: {} regions, {:.1f} MB total'.format(len(merged), total_bytes/1e6))

    pages = {}  # addr -> bytes
    for base, size in merged:
        for off in range(0, size, PAGE_SIZE):
            addr = base + off
            data = mem_read(hproc, addr, PAGE_SIZE)
            if data and len(data) == PAGE_SIZE:
                pages[addr] = data

    print('Captured {:,} pages.'.format(len(pages)))

    # Save as binary: [8-byte addr][4096-byte data] per page
    with open(SNAP_A_BIN, 'wb') as f:
        for addr in sorted(pages):
            f.write(struct.pack('<Q', addr))
            f.write(pages[addr])
    size_mb = os.path.getsize(SNAP_A_BIN) / 1e6
    print('Saved {:.1f} MB to {}'.format(size_mb, SNAP_A_BIN))
    print()
    print('NOW CHANGE THE PLAYBOOK IN-GAME, then run: python page_diff.py diff')

def cmd_diff(hproc, table_base):
    """Byte-level diff of saved pages vs current memory."""
    if not os.path.exists(SNAP_A_BIN):
        print('Run "python page_diff.py snap" first.'); return

    # Load saved pages
    pages_A = {}
    with open(SNAP_A_BIN, 'rb') as f:
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            addr = struct.unpack('<Q', hdr)[0]
            data = f.read(PAGE_SIZE)
            if len(data) < PAGE_SIZE:
                break
            pages_A[addr] = data
    print('Loaded {:,} pages from {}'.format(len(pages_A), SNAP_A_BIN))

    # Read current state and diff
    print('Reading current state and diffing...')
    all_diffs = []
    for addr in sorted(pages_A):
        cur = mem_read(hproc, addr, PAGE_SIZE)
        if not cur or len(cur) < PAGE_SIZE:
            continue
        prev = pages_A[addr]
        diffs = [(j, prev[j], cur[j]) for j in range(PAGE_SIZE) if prev[j] != cur[j]]
        if diffs:
            all_diffs.append((addr, diffs))

    print('\n=== DIFF RESULTS: {:} pages changed ==='.format(len(all_diffs)))
    if not all_diffs:
        print('No changes. Change the playbook and run diff again.')
        return

    for page_addr, diffs in all_diffs[:20]:
        print('\nPage 0x{:X} (team offset: {:+d})  [{:} bytes differ]'.format(
            page_addr, page_addr - table_base, len(diffs)))
        # Group into runs
        blocks = []
        blk = [diffs[0]]
        for d in diffs[1:]:
            if d[0] == blk[-1][0] + 1:
                blk.append(d)
            else:
                blocks.append(blk); blk = [d]
        blocks.append(blk)
        for blk in blocks[:8]:
            off = blk[0][0]
            abs_addr = page_addr + off
            raw_a = bytes(x[1] for x in blk[:4]).ljust(4, b'\x00')
            raw_b = bytes(x[2] for x in blk[:4]).ljust(4, b'\x00')
            u32_a = struct.unpack('<I', raw_a)[0]
            u32_b = struct.unpack('<I', raw_b)[0]
            hex_a = ' '.join('{:02X}'.format(x[1]) for x in blk[:8])
            hex_b = ' '.join('{:02X}'.format(x[2]) for x in blk[:8])
            print('  +0x{:04X} abs 0x{:X}: [{}] -> [{}]  u32: {} -> {}  ({} bytes)'.format(
                off, abs_addr, hex_a, hex_b, u32_a, u32_b, len(blk)))


# ─── main ─────────────────────────────────────────────────────────────────────

COMMANDS = {
    'checksum':    cmd_checksum,
    'checkdiff':   cmd_checkdiff,
    'investigate': cmd_investigate,
    'snap':        cmd_snap,
    'diff':        cmd_diff,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print('Commands: {}'.format(' | '.join(COMMANDS)))
        print()
        print('FAST WORKFLOW (covers ALL game memory):')
        print('  1. python page_diff.py checksum   <- before changing playbook')
        print('  2. (change playbook in-game)')
        print('  3. python page_diff.py checkdiff  <- finds changed pages')
        print('  4. python page_diff.py investigate <- shows small-int values in changed pages')
        print()
        print('DETAILED WORKFLOW (targeted 8MB + all pointer regions):')
        print('  1. python page_diff.py snap')
        print('  2. (change playbook)')
        print('  3. python page_diff.py diff')
        sys.exit(0)

    pid = find_pid(GAME_EXE)
    module_base = get_module_base(pid, GAME_EXE)
    hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]
    print('PID: {}  Team table: 0x{:X}'.format(pid, table_base))

    COMMANDS[sys.argv[1]](hproc, table_base)
    kernel32.CloseHandle(hproc)
