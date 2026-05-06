"""
Capture the full 16-byte volatile entry for each playbook state.
Then test: write the full entry for playbook X and check if it sticks.
Also test writing ONLY u64[1] to see if that alone controls byte[3].
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

VOLATILE_ADDR = module_base + 0x741F9E0
VOLATILE_ADDR2 = module_base + 0x741FA08  # both track same playbook

def read_entry(addr):
    e = mem_read(hproc, addr, 16)
    return bytes(e) if e else None

def write_mem(addr, data):
    buf = (ctypes.c_char * len(data))(*data)
    written = ctypes.c_size_t(0)
    return kernel32.WriteProcessMemory(hproc, ctypes.c_ulonglong(addr),
                                       buf, len(data), ctypes.byref(written))

# --- Phase 1: Capture entry bytes for each playbook ---
pb_entries = {}
entry = read_entry(VOLATILE_ADDR)
if entry:
    pb_id = entry[3]
    pb_entries[pb_id] = entry
    print('Start: pb_id={} entry={}'.format(pb_id, entry.hex()))

print('\nCycle through all 3 playbooks (watch for detection), then press Enter...')
prev_id = pb_id
deadline = time.time() + 60
while time.time() < deadline and len(pb_entries) < 3:
    time.sleep(0.02)
    e = read_entry(VOLATILE_ADDR)
    if e and e[3] != prev_id:
        new_id = e[3]
        pb_entries[new_id] = e
        print('  Captured pb_id={}: {}'.format(new_id, e.hex()))
        prev_id = new_id

print('\n=== CAPTURED ENTRIES ===')
for pb_id_k in sorted(pb_entries.keys()):
    e = pb_entries[pb_id_k]
    u64_1 = struct.unpack_from('<Q', e, 8)[0]
    print('  pb_id={}: {} (u64[1]=0x{:X})'.format(pb_id_k, e.hex(), u64_1))

if len(pb_entries) < 2:
    print('Need at least 2 playbooks captured.')
    kernel32.CloseHandle(hproc)
    sys.exit(1)

# --- Phase 2: Test writing full entry ---
# Pick a target playbook different from current
current = read_entry(VOLATILE_ADDR)[3]
targets = [k for k in pb_entries if k != current]
target_id = targets[0]
target_entry = pb_entries[target_id]
target_u64_1 = struct.unpack_from('<Q', target_entry, 8)[0]

print('\n=== TEST 1: Write ONLY u64[1] (bytes 8-15) ===')
print('Current pb_id={}, writing u64[1]=0x{:X} (pb={})'.format(current, target_u64_1, target_id))
write_mem(VOLATILE_ADDR + 8, target_entry[8:16])
time.sleep(0.005)
after = read_entry(VOLATILE_ADDR)
print('After 5ms:  pb={} u64[1]=0x{:X}'.format(after[3] if after else '?',
    struct.unpack_from('<Q', after, 8)[0] if after else 0))
time.sleep(0.1)
after = read_entry(VOLATILE_ADDR)
print('After 100ms: pb={} u64[1]=0x{:X}'.format(after[3] if after else '?',
    struct.unpack_from('<Q', after, 8)[0] if after else 0))

print('\n=== TEST 2: Write FULL 16-byte entry ===')
print('Writing full entry for pb={}'.format(target_id))
write_mem(VOLATILE_ADDR, target_entry)
time.sleep(0.005)
after = read_entry(VOLATILE_ADDR)
print('After 5ms:  pb={} full={}'.format(after[3] if after else '?',
    after.hex() if after else '?'))
time.sleep(0.1)
after = read_entry(VOLATILE_ADDR)
print('After 100ms: pb={} full={}'.format(after[3] if after else '?',
    after.hex() if after else '?'))
time.sleep(1.0)
after = read_entry(VOLATILE_ADDR)
print('After 1s:    pb={} full={}'.format(after[3] if after else '?',
    after.hex() if after else '?'))

print('\n=== TEST 3: Write BOTH volatile addrs simultaneously ===')
write_mem(VOLATILE_ADDR, target_entry)
write_mem(VOLATILE_ADDR2, target_entry)
time.sleep(0.005)
a1 = read_entry(VOLATILE_ADDR)
a2 = read_entry(VOLATILE_ADDR2)
print('After 5ms:   addr1.pb={} addr2.pb={}'.format(a1[3] if a1 else '?', a2[3] if a2 else '?'))
time.sleep(0.5)
a1 = read_entry(VOLATILE_ADDR)
a2 = read_entry(VOLATILE_ADDR2)
print('After 500ms: addr1.pb={} addr2.pb={}'.format(a1[3] if a1 else '?', a2[3] if a2 else '?'))

kernel32.CloseHandle(hproc)
