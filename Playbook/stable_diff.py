"""
Stable-diff scanner: find the authoritative playbook storage.

Strategy:
  1. Scan all 22MB of module .data for every QWORD (8-byte aligned)
  2. Take 3 baselines (spaced 0.3s apart) to identify NOISY addresses (change spontaneously)
  3. User presses button ONCE
  4. Scan again -> addresses that CHANGED from stable baseline = candidates
  5. Wait 1s -> check which candidates STAYED changed (not written back by game)
     -> These are the authoritative ones

Usage:
  python stable_diff.py snap    <- step 1-3: build stable baseline (takes ~5s)
  python stable_diff.py diff    <- step 4-5: diff after button press (takes ~2s)
  python stable_diff.py watch   <- continuously poll stable addresses only
"""
import sys, os, struct, json, time, ctypes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)

SNAP_FILE  = 'stable_snap.bin'  # binary: list of (rva_4byte, value_4byte) pairs

# Known noisy RVAs to skip
KNOWN_NOISY = {0x741F383, 0x741F4B3, 0x741F4D3, 0x741F513,
               0x741F523, 0x741F543, 0x741F553, 0x741F9E3,
               # frame counters
               0x741BDF0, 0x741BED1, 0x741BEE1}

SCAN_START_RVA = 0x7000000
SCAN_END_RVA   = 0x8500000  # 22MB window

def read_module_data(hproc, module_base):
    return mem_read(hproc, module_base + SCAN_START_RVA, SCAN_END_RVA - SCAN_START_RVA)

def extract_u8_values(data):
    """Return dict of offset -> byte for all non-zero bytes."""
    return {i: data[i] for i in range(len(data)) if data[i] != 0}

def find_changed(data_a, data_b):
    """Return list of (offset, old_val, new_val) for changed bytes."""
    mn = min(len(data_a), len(data_b))
    return [(i, data_a[i], data_b[i]) for i in range(mn) if data_a[i] != data_b[i]]

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
print('module=0x{:X}'.format(module_base))

cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'

if cmd == 'snap':
    print('Reading baseline A ({:.0f} MB)...'.format((SCAN_END_RVA - SCAN_START_RVA)/1e6))
    t0 = time.time()
    data_a = read_module_data(hproc, module_base)
    ta = time.time() - t0
    print('  Read in {:.2f}s ({:,} bytes)'.format(ta, len(data_a)))

    time.sleep(0.3)
    print('Reading baseline B...')
    t0 = time.time()
    data_b = read_module_data(hproc, module_base)
    tb = time.time() - t0
    print('  Read in {:.2f}s'.format(tb))

    time.sleep(0.3)
    print('Reading baseline C...')
    data_c = read_module_data(hproc, module_base)

    # Find noisy offsets (changed between A->B or B->C)
    noisy_ab = set(i for i, _, _ in find_changed(data_a, data_b))
    noisy_bc = set(i for i, _, _ in find_changed(data_b, data_c))
    noisy = noisy_ab | noisy_bc
    # Also add known noisy RVAs
    for rva in KNOWN_NOISY:
        noisy.add(rva - SCAN_START_RVA)
    print('Noisy offsets (spontaneously changing): {:,}'.format(len(noisy)))

    # Save stable snapshot: only offsets NOT in noisy, using data_c as baseline
    # Pack as: 4-byte offset, 1-byte value
    stable = {}
    for i in range(len(data_c)):
        if i not in noisy:
            v = data_c[i]
            if v != 0:  # skip zeros (too many)
                stable[i] = v

    print('Stable non-zero bytes: {:,}'.format(len(stable)))

    with open(SNAP_FILE, 'wb') as f:
        for off, val in stable.items():
            f.write(struct.pack('<IB', off, val))
    sz = os.path.getsize(SNAP_FILE)
    print('Saved {:,} bytes to {}'.format(sz, SNAP_FILE))
    print()
    print('NOW PRESS THE PLAYBOOK BUTTON ONCE, then run: python stable_diff.py diff')

elif cmd == 'diff':
    if not os.path.exists(SNAP_FILE):
        print('Run snap first.'); kernel32.CloseHandle(hproc); sys.exit(1)

    # Load stable baseline
    stable = {}
    with open(SNAP_FILE, 'rb') as f:
        data = f.read()
    for i in range(0, len(data) - 4, 5):
        off = struct.unpack_from('<I', data, i)[0]
        val = data[i + 4]
        stable[off] = val
    print('Loaded {:,} stable candidates'.format(len(stable)))

    print('Reading current state...')
    t0 = time.time()
    cur_data = read_module_data(hproc, module_base)
    print('  Read in {:.2f}s'.format(time.time() - t0))

    # Find changed stable bytes
    changed = [(off, stable[off], cur_data[off])
               for off in stable
               if off < len(cur_data) and cur_data[off] != stable[off]]
    print('Changed stable bytes: {:,}'.format(len(changed)))

    if not changed:
        print('No changes detected. Did you press the playbook button?')
        kernel32.CloseHandle(hproc); sys.exit(0)

    # Wait 1s and re-read to filter out newly-noisy ones
    print('Waiting 1s to filter noisy ones...')
    time.sleep(1.0)
    cur_data2 = read_module_data(hproc, module_base)

    persistent = [(off, old, new) for off, old, new in changed
                  if cur_data2[off] == new]  # still at new value
    reverted   = [(off, old, new) for off, old, new in changed
                  if cur_data2[off] == old]  # reverted back
    other      = [(off, old, new) for off, old, new in changed
                  if cur_data2[off] != old and cur_data2[off] != new]

    print('\n=== PERSISTENT changes (stayed at new value): {:} ==='.format(len(persistent)))
    for off, old, new in persistent[:50]:
        rva = SCAN_START_RVA + off
        raw4 = cur_data2[off:off+4]
        u32 = struct.unpack('<I', raw4.ljust(4, b'\x00')[:4])[0] if len(raw4) >= 4 else 0
        print('  RVA+0x{:X}: {} -> {}  (u32 at this offset: {})'.format(rva, old, new, u32))

    print('\n=== REVERTED changes (game wrote back): {:} ==='.format(len(reverted)))
    for off, old, new in reverted[:20]:
        rva = SCAN_START_RVA + off
        print('  RVA+0x{:X}: {} -> {} -> {} (REVERTED)'.format(rva, old, new, old))

    if other:
        print('\n=== OTHER (changed to 3rd value): {:} ==='.format(len(other)))
        for off, old, new in other[:10]:
            rva = SCAN_START_RVA + off
            print('  RVA+0x{:X}: {} -> {} -> {} (CHANGED AGAIN)'.format(rva, old, new, cur_data2[off]))

    # Focus: look for byte changing from 28->26 or similar small values
    print('\n=== FOCUS: small-value changes (old<=40 or new<=40) ===')
    small = [(off, old, new) for off, old, new in persistent if old <= 40 or new <= 40]
    for off, old, new in small[:30]:
        rva = SCAN_START_RVA + off
        # Read 32 bytes of context
        ctx = cur_data2[max(0, off-8):off+24]
        h = ' '.join('{:02X}'.format(b) for b in ctx)
        print('  RVA+0x{:X}: {} -> {}  ctx: {}'.format(rva, old, new, h))

elif cmd == 'watch':
    if not os.path.exists(SNAP_FILE):
        print('Run snap first.'); kernel32.CloseHandle(hproc); sys.exit(1)
    stable = {}
    with open(SNAP_FILE, 'rb') as f:
        raw = f.read()
    for i in range(0, len(raw) - 4, 5):
        off = struct.unpack_from('<I', raw, i)[0]
        val = raw[i + 4]
        stable[off] = val

    # Build small-value candidates only (more interesting)
    small_cands = {off: val for off, val in stable.items() if 1 <= val <= 50}
    print('Watching {:,} small-value stable addresses...'.format(len(small_cands)))
    baseline = dict(small_cands)
    poll = 0
    try:
        while True:
            time.sleep(0.3)
            cur = read_module_data(hproc, module_base)
            changed = [(off, baseline[off], cur[off])
                       for off in small_cands
                       if cur[off] != baseline[off]]
            if changed:
                ts = time.strftime('%H:%M:%S')
                print('[{}] {} changes:'.format(ts, len(changed)))
                for off, old, new in changed[:20]:
                    rva = SCAN_START_RVA + off
                    print('  RVA+0x{:X}: {} -> {}'.format(rva, old, new))
                baseline = {off: cur[off] for off in small_cands}
            elif poll % 20 == 0:
                print('[{}] Polling ({} polls)...'.format(time.strftime('%H:%M:%S'), poll))
            poll += 1
    except KeyboardInterrupt:
        print('\nStopped.')

kernel32.CloseHandle(hproc)
