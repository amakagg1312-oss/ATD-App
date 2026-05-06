"""
Scan the NBA2K26 module .data section for all heap pointers.
For each pointer target, read 256 bytes and look for playbook-like values.
Then take a FAST snapshot of just these locations for before/after diff.

Usage:
  python scan_module_pointers.py snap    <- baseline (before playbook change)
  python scan_module_pointers.py diff    <- diff (immediately after change)
  python scan_module_pointers.py explore <- dump all pointer targets for inspection
"""
import sys, os, struct, json, ctypes, time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess, TEAM_RVA, TEAM_STRIDE)

SNAP_FILE = 'module_ptr_snap.json'
READ_SIZE = 8192  # bytes to read from each pointer target (8KB to catch deeper fields)

def scan_module_data(hproc, module_base):
    """Scan .data section of module for valid heap pointers."""
    # Wider scan: 0x7000000 to 0x8500000 (22MB window around known RVAs at ~0x7E...)
    HEAP_MIN = 0x100000000
    HEAP_MAX = 0xF00000000

    scan_start = module_base + 0x7000000
    scan_end   = module_base + 0x8500000

    print('Scanning module .data region: 0x{:X} - 0x{:X} ({:.1f} MB)'.format(
        scan_start, scan_end, (scan_end - scan_start) / 1e6))

    data = mem_read(hproc, scan_start, scan_end - scan_start)
    if not data:
        print('ERROR: could not read module data section')
        return []

    pointers = []
    for i in range(0, len(data) - 7, 8):
        val = struct.unpack_from('<Q', data, i)[0]
        if HEAP_MIN < val < HEAP_MAX:
            rva = scan_start + i - module_base
            pointers.append((rva, val))

    print('Found {:,} heap pointers in module .data'.format(len(pointers)))
    return pointers

def take_snap(hproc, pointers, label=''):
    """Read READ_SIZE bytes from each pointer target."""
    snap = {}
    for rva, addr in pointers:
        data = mem_read(hproc, addr, READ_SIZE)
        if data:
            snap[rva] = data.hex()
    print('Snapped {:,} pointer targets ({})'.format(len(snap), label))
    return snap

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'

    pid = find_pid(GAME_EXE)
    module_base = get_module_base(pid, GAME_EXE)
    hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]

    print('PID={}  module=0x{:X}  team_table=0x{:X}'.format(pid, module_base, table_base))

    pointers = scan_module_data(hproc, module_base)

    if cmd == 'snap':
        snap = take_snap(hproc, pointers, 'A')
        with open(SNAP_FILE, 'w') as f:
            json.dump({'pointers': [[r, hex(v)] for r, v in pointers], 'snap': snap}, f)
        print('Saved to {}'.format(SNAP_FILE))
        print('NOW CHANGE THE PLAYBOOK, then run: python scan_module_pointers.py diff')

    elif cmd == 'diff':
        if not os.path.exists(SNAP_FILE):
            print('Run snap first.'); kernel32.CloseHandle(hproc); return
        with open(SNAP_FILE) as f:
            saved = json.load(f)
        snap_A = saved['snap']
        pointers_A = [(r, int(v, 16)) for r, v in saved['pointers']]

        print('Comparing {} pointer targets...'.format(len(pointers_A)))
        diffs = []
        for rva, addr in pointers_A:
            rva_s = str(rva)
            if rva_s not in snap_A:
                continue
            cur = mem_read(hproc, addr, READ_SIZE)
            if not cur:
                continue
            prev = bytes.fromhex(snap_A[rva_s])
            changed = [(j, prev[j], cur[j]) for j in range(min(len(prev), len(cur)))
                       if prev[j] != cur[j]]
            if changed:
                diffs.append((rva, addr, changed))

        print('\n=== DIFF: {:} pointer targets changed ==='.format(len(diffs)))
        for rva, addr, changed in diffs[:30]:
            print('\n  RVA+0x{:X} -> 0x{:X}  [{:} bytes differ]'.format(rva, addr, len(changed)))
            # Group into runs
            blocks = []
            blk = [changed[0]]
            for d in changed[1:]:
                if d[0] == blk[-1][0] + 1: blk.append(d)
                else: blocks.append(blk); blk = [d]
            blocks.append(blk)
            for blk in blocks[:6]:
                off = blk[0][0]
                abs_a = addr + off
                raw_a = bytes(x[1] for x in blk[:4]).ljust(4, b'\x00')
                raw_b = bytes(x[2] for x in blk[:4]).ljust(4, b'\x00')
                u32_a = struct.unpack('<I', raw_a)[0]
                u32_b = struct.unpack('<I', raw_b)[0]
                hex_a = ' '.join('{:02X}'.format(x[1]) for x in blk[:8])
                hex_b = ' '.join('{:02X}'.format(x[2]) for x in blk[:8])
                print('    +{:4d} (0x{:X}): [{}] -> [{}]  u32: {} -> {}'.format(
                    off, abs_a, hex_a, hex_b, u32_a, u32_b))

    elif cmd == 'explore':
        # Dump all pointer targets looking for team/playbook-related data
        team_name_hits = []
        playbook_like = []

        for rva, addr in pointers[:500]:  # first 500
            data = mem_read(hproc, addr, READ_SIZE)
            if not data:
                continue
            # Look for "76ers" or "Sixers" strings
            for term in [b'76ers', b'Sixers', b'sixers', b'PHI', b'playbook', b'Playbook']:
                if term in data:
                    team_name_hits.append((rva, addr, term.decode('ascii', errors='replace')))
                    break
            # Look for small ints 1-200 at regular intervals (playbook IDs)
            small = [(j, struct.unpack_from('<I', data, j)[0])
                     for j in range(0, READ_SIZE-3, 4)
                     if 1 <= struct.unpack_from('<I', data, j)[0] <= 150]
            if 3 <= len(small) <= 20:
                playbook_like.append((rva, addr, small[:6]))

        if team_name_hits:
            print('\nTeam name hits:')
            for rva, addr, term in team_name_hits:
                print('  RVA+0x{:X} -> 0x{:X}  contains "{}"'.format(rva, addr, term))

        print('\nPointers with 3-20 small ints (1-150):')
        for rva, addr, small in playbook_like[:20]:
            print('  RVA+0x{:X} -> 0x{:X}: {}'.format(rva, addr, small))

    kernel32.CloseHandle(hproc)

if __name__ == '__main__':
    main()
