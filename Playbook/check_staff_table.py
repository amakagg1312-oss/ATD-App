import sys, struct
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

candidates = [0x270466B0, 0x274EFF58]
staff_stride = 432
staff_first_offset = 0x28

for base in candidates:
    print(f"\n--- Staff table at 0x{base:X} ---")
    # Read first few entries
    for slot in range(5):
        entry = base + slot * staff_stride
        # Read first_name at +0x28
        name_buf = read_memory(handle, entry + staff_first_offset, 40)
        if name_buf:
            try:
                name = name_buf.decode('utf-16-le').split('\x00')[0]
                if name:
                    print(f"  Slot {slot}: {name}")
            except:
                print(f"  Slot {slot}: (binary: {name_buf[:20]})")

CloseHandle(handle)