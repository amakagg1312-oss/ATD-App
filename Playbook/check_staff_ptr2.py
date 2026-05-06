import sys, struct
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

# Try dereferencing pointers from first table
base = 0x270466B0
staff_stride = 432

for slot in range(10):
    entry = base + slot * staff_stride
    # Read first 8 bytes as pointer
    ptr_buf = read_memory(handle, entry, 8)
    if ptr_buf:
        ptr = struct.unpack('<Q', ptr_buf)[0]
        if ptr > 0x1000000 and ptr < 0x200000000:
            # Try reading string from pointer
            str_buf = read_memory(handle, ptr, 40)
            if str_buf:
                try:
                    name = str_buf.decode('utf-16-le').split('\x00')[0]
                    if name and len(name) >= 2:
                        print(f"Slot {slot}: 0x{ptr:X} -> {name}")
                except:
                    pass

CloseHandle(handle)