"""Quick write + verify without interactive input."""
import sys, struct, ctypes, time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess)

PLAYBOOK_RVAS = [
    0x741F383, 0x741F4B3, 0x741F4D3, 0x741F513,
    0x741F523, 0x741F543, 0x741F553, 0x741F9E3,
]

def write_byte(hproc, addr, value):
    buf = ctypes.create_string_buffer(bytes([value]))
    written = ctypes.c_size_t(0)
    ok = kernel32.WriteProcessMemory(hproc, ctypes.c_void_p(addr), buf, 1, ctypes.byref(written))
    return ok and written.value == 1

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

target_id = int(sys.argv[1]) if len(sys.argv) > 1 else 26

# Read before
before = [mem_read(hproc, module_base + r, 1)[0] for r in PLAYBOOK_RVAS]
print('Before: {}'.format(before[0]))

# Write
ok = 0
for rva in PLAYBOOK_RVAS:
    if write_byte(hproc, module_base + rva, target_id):
        ok += 1
print('Wrote {} to {}/{} addresses'.format(target_id, ok, len(PLAYBOOK_RVAS)))

# Read immediately after
time.sleep(0.05)
after_imm = [mem_read(hproc, module_base + r, 1)[0] for r in PLAYBOOK_RVAS]
print('After (immediate): {} (expected {})'.format(after_imm[0], target_id))
if after_imm[0] != target_id:
    print('  -> WRITE DID NOT STICK (game blocked writes?)')
    kernel32.CloseHandle(hproc)
    sys.exit()

# Poll for 3 seconds to see if game reverts
for t in range(1, 7):
    time.sleep(0.5)
    cur = [mem_read(hproc, module_base + r, 1)[0] for r in PLAYBOOK_RVAS]
    if cur[0] != target_id:
        print('After {:.1f}s: {} (REVERTED from {})'.format(t*0.5, cur[0], target_id))
    else:
        print('After {:.1f}s: {} (still holds)'.format(t*0.5, cur[0]))

kernel32.CloseHandle(hproc)
