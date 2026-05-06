"""
Test playbook injection stability OUTSIDE the Edit Plays carousel.

The volatile entries at RVA+0x741F9E0 / +0x741FA08 cycle through all available
playbooks at ~17ms per step while the Edit Plays preview animation is running.
Outside that screen the entries should hold a single stable value.

Run this script, then IMMEDIATELY navigate away from Edit Plays in-game.
The script will:
  1. Detect when cycling stops (stable for 500ms)
  2. Try an injection to a different playbook
  3. Monitor for 5 seconds to see if it holds
"""
import sys, struct, time, ctypes, json, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               TEAM_RVA, TEAM_STRIDE)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

VOLATILE_RVA1 = 0x741F9E0
VOLATILE_RVA2 = 0x741FA08

def read_entry(rva):
    e = mem_read(hproc, module_base + rva, 16)
    return bytes(e) if e else None

def write_u64(addr, value):
    data = struct.pack('<Q', value)
    buf = (ctypes.c_char * 8)(*data)
    written = ctypes.c_size_t(0)
    return kernel32.WriteProcessMemory(hproc, ctypes.c_ulonglong(addr),
                                       buf, 8, ctypes.byref(written))

def load_map():
    if os.path.exists('playbook_map.json'):
        with open('playbook_map.json') as f:
            raw = json.load(f)
        return {int(k): v for k, v in raw.items()}
    return {}

pb_map = load_map()
print('Loaded playbook map: {}'.format(sorted(pb_map.keys())))

# ── PHASE 1: Detect stable vs cycling ────────────────────────────────────────
print('\nMonitoring volatile entry (RVA+0x{:X})...'.format(VOLATILE_RVA1))
print('Navigate AWAY from Edit Plays. Waiting for entries to stabilize...\n')

WINDOW = 1.0       # seconds of stability required
TIMEOUT = 60.0     # give up after this long

seen_ids = {}
start = time.time()
stable_since = None
last_id = None
prev_id = None

# Collect distribution
sample_start = time.time()
while time.time() - start < TIMEOUT:
    e = read_entry(VOLATILE_RVA1)
    if e is None:
        time.sleep(0.01)
        continue
    cur_id = e[3]
    cur_u64 = struct.unpack_from('<Q', e, 8)[0]

    # Track seen IDs over rolling 1-second window
    now = time.time()
    seen_ids[now] = cur_id

    # Purge entries older than WINDOW
    cutoff = now - WINDOW
    seen_ids = {t: v for t, v in seen_ids.items() if t > cutoff}

    unique_recent = len(set(seen_ids.values()))

    if cur_id != prev_id:
        print('  t={:.1f}s  id={} obj=0x{:X}  (unique in last {}s: {})'.format(
            now - start, cur_id, cur_u64, WINDOW, unique_recent))
        prev_id = cur_id

    if unique_recent == 1:
        if stable_since is None:
            stable_since = now
        if now - stable_since >= WINDOW:
            print('\n>>> STABLE! pb_id={} obj=0x{:X} (stable for {:.1f}s)'.format(
                cur_id, cur_u64, now - stable_since))
            stable_id = cur_id
            stable_u64 = cur_u64
            break
    else:
        stable_since = None

    time.sleep(0.002)
else:
    e = read_entry(VOLATILE_RVA1)
    all_ids = set(seen_ids.values())
    print('\nTIMEOUT. Still seeing {} unique IDs in last {}s: {}'.format(
        len(all_ids), WINDOW, sorted(all_ids)))
    print('The carousel animation may still be running (still in Edit Plays?)')
    print()
    if e:
        stable_id = e[3]
        stable_u64 = struct.unpack_from('<Q', e, 8)[0]
        print('Using current state: pb_id={} obj=0x{:X}'.format(stable_id, stable_u64))
    else:
        kernel32.CloseHandle(hproc)
        sys.exit(1)

# ── PHASE 2: Injection test ───────────────────────────────────────────────────
# Pick a different target
if len(pb_map) < 2:
    print('\nNeed at least 2 playbooks in map to test injection.')
    print('Run: python inject_playbook.py discover')
    kernel32.CloseHandle(hproc)
    sys.exit(1)

targets = [k for k in sorted(pb_map.keys()) if k != stable_id]
if not targets:
    print('No other playbooks to inject — only 1 in map.')
    kernel32.CloseHandle(hproc)
    sys.exit(1)

target_id = targets[0]
target_obj = pb_map[target_id]
print('\n=== INJECTION TEST ===')
print('Current: pb_id={} obj=0x{:X}'.format(stable_id, stable_u64))
print('Target:  pb_id={} obj=0x{:X}'.format(target_id, target_obj))

# Write u64[1] to both volatile addrs
for rva in [VOLATILE_RVA1, VOLATILE_RVA2]:
    write_u64(module_base + rva + 8, target_obj)

print('\nMonitoring for 5 seconds post-injection...')
inject_time = time.time()
samples = []
while time.time() - inject_time < 5.0:
    e = read_entry(VOLATILE_RVA1)
    if e:
        samples.append((time.time() - inject_time, e[3],
                        struct.unpack_from('<Q', e, 8)[0]))
    time.sleep(0.05)

# Summarize
from collections import Counter
id_counts = Counter(s[1] for s in samples)
print('\nResult distribution over 5s:')
for pb_id_k, count in sorted(id_counts.items()):
    pct = count * 100 // len(samples)
    marker = ' <-- INJECTED' if pb_id_k == target_id else (
             ' <-- ORIGINAL' if pb_id_k == stable_id else '')
    print('  pb_id={}: {} samples ({:3d}%){}'.format(pb_id_k, count, pct, marker))

if id_counts.get(target_id, 0) > len(samples) * 0.9:
    print('\nSUCCESS: Injection held for >90% of 5 seconds!')
    print('=> Volatile entry injection works OUTSIDE the Edit Plays carousel.')
    print('=> The u64[1] write is sufficient to change playbooks permanently.')
elif id_counts.get(target_id, 0) > 0:
    first_seen = next(s[0] for s in samples if s[1] == target_id)
    last_seen  = max(s[0] for s in samples if s[1] == target_id)
    print('\nPARTIAL: Injection seen for {:.1f}s then overridden.'.format(
        last_seen - first_seen))
else:
    print('\nFAILED: Injection had no effect.')
    print('=> There is another mechanism controlling playbook selection.')

# Final state
e = read_entry(VOLATILE_RVA1)
if e:
    print('\nFinal state: pb_id={} obj=0x{:X}'.format(
        e[3], struct.unpack_from('<Q', e, 8)[0]))

kernel32.CloseHandle(hproc)
