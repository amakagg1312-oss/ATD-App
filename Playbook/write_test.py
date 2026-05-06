"""
Write test: inject playbook ID to the 8 known addresses and verify.
Usage:
  python write_test.py read     - show current values
  python write_test.py write N  - write playbook ID N to all 8 addresses
  python write_test.py cycle    - cycle through values 24->26->28->24 every 2s (for visual test)
"""
import sys, struct, ctypes, time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess)

# The 8 RVA offsets where byte[3] of the 16-byte entry holds the playbook ID
PLAYBOOK_RVAS = [
    0x741F383,
    0x741F4B3,
    0x741F4D3,
    0x741F513,
    0x741F523,
    0x741F543,
    0x741F553,
    0x741F9E3,
]

def write_byte(hproc, addr, value):
    buf = ctypes.create_string_buffer(bytes([value]))
    written = ctypes.c_size_t(0)
    ok = kernel32.WriteProcessMemory(hproc, ctypes.c_void_p(addr), buf, 1, ctypes.byref(written))
    return ok and written.value == 1

def read_playbook(hproc, module_base):
    vals = []
    for rva in PLAYBOOK_RVAS:
        d = mem_read(hproc, module_base + rva, 1)
        vals.append(d[0] if d else -1)
    return vals

def write_playbook(hproc, module_base, pb_id):
    results = []
    for rva in PLAYBOOK_RVAS:
        ok = write_byte(hproc, module_base + rva, pb_id)
        results.append(ok)
    return results

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

cmd = sys.argv[1] if len(sys.argv) > 1 else 'read'

if cmd == 'read':
    vals = read_playbook(hproc, module_base)
    for rva, v in zip(PLAYBOOK_RVAS, vals):
        print('  RVA+0x{:X}: {}'.format(rva, v))

elif cmd == 'write':
    if len(sys.argv) < 3:
        print('Usage: python write_test.py write <playbook_id>')
        sys.exit(1)
    pb_id = int(sys.argv[2])
    print('Current values:')
    vals = read_playbook(hproc, module_base)
    for rva, v in zip(PLAYBOOK_RVAS, vals):
        print('  RVA+0x{:X}: {}'.format(rva, v))

    print('\nWriting playbook_id={} (0x{:02X}) to all {} addresses...'.format(pb_id, pb_id, len(PLAYBOOK_RVAS)))
    results = write_playbook(hproc, module_base, pb_id)
    ok_count = sum(1 for r in results if r)
    print('Wrote {} / {} addresses OK'.format(ok_count, len(PLAYBOOK_RVAS)))

    time.sleep(0.1)
    print('\nValues after write:')
    vals2 = read_playbook(hproc, module_base)
    for rva, v in zip(PLAYBOOK_RVAS, vals2):
        changed = ' <- CHANGED' if vals[PLAYBOOK_RVAS.index(rva)] != v else ''
        print('  RVA+0x{:X}: {}{}'.format(rva, v, changed))

    print('\nCheck the game UI now - has the playbook display changed?')
    print('If the game overwrites these values, they will revert next poll.')
    input('Press Enter to read values again after 1 second...')
    time.sleep(1.0)
    print('\nValues 1 second later:')
    vals3 = read_playbook(hproc, module_base)
    for rva, v in zip(PLAYBOOK_RVAS, vals3):
        note = ''
        if v != pb_id:
            note = ' <- REVERTED to {} (game overwrote!)'.format(v)
        print('  RVA+0x{:X}: {}{}'.format(rva, v, note))

elif cmd == 'cycle':
    print('Cycling playbook every 2s: 24->26->28->24... (Ctrl+C to stop)')
    ids = [24, 26, 28]
    i = 0
    try:
        while True:
            pb_id = ids[i % 3]
            results = write_playbook(hproc, module_base, pb_id)
            ok = sum(1 for r in results if r)
            print('[{}] Wrote playbook={} ({}/{} OK)'.format(
                time.strftime('%H:%M:%S'), pb_id, ok, len(PLAYBOOK_RVAS)))
            i += 1
            time.sleep(2.0)
    except KeyboardInterrupt:
        print('\nStopped.')

kernel32.CloseHandle(hproc)
