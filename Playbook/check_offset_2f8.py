import sys, struct
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

# From user data: Staff offset from team is 0x2F8 (760) for Set A
team = 0x27230BC4

# Try offset 0x2F8
for off in [0x2F8, 0x300, 0x400, 0x500, 0x600, 0x700, 0x758, 0x800]:
    addr = team + off
    buf = read_memory(handle, addr, 100)
    if buf:
        print(f"Team+0x{off:X} (0x{addr:X}): {buf[:50]}")

CloseHandle(handle)