import sys, struct
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

# Read team structure at known address
team = 0x27230BC4
buf = read_memory(handle, team, 0x2000)

if buf:
    print(f"Team structure at 0x{team:X}:")
    # Print values at various offsets
    for off in range(0, 0x2000, 4):
        val = struct.unpack('<I', buf[off:off+4])[0]
        if val > 0 and val < 0x200000000:
            # Try reading from this value as pointer
            ptr_buf = read_memory(handle, val, 40)
            if ptr_buf:
                try:
                    s = ptr_buf.decode('utf-16-le').split('\x00')[0]
                    if len(s) >= 3 and s.replace(' ','').isalpha():
                        print(f"  +0x{off:X}: 0x{val:X} -> {s}")
                except:
                    pass

CloseHandle(handle)