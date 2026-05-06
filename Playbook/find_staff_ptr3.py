import sys, struct
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

# Search for staff table by looking for entries with valid string pointers
staff_stride = 432
staff_first_offset = 0x28

print("Searching for staff table with string pointers...")

for region_base, region_size, _ in iter_memory_regions(handle, 0x27000000, 0x28000000):
    try:
        buf = read_memory(handle, region_base, region_size)
    except:
        buf = None
    if not buf or region_size < staff_stride * 10:
        continue
    
    # Look for entries where first_name offset has a pointer to a string
    for offset in range(0, region_size - staff_stride * 5, staff_stride):
        entry_start = offset
        name_off = entry_start + staff_first_offset
        if name_off + 8 <= region_size:
            ptr = struct.unpack('<Q', buf[name_off:name_off+8])[0]
            if 0x1000000 < ptr < 0x200000000:
                # Try reading string from pointer
                str_buf = read_memory(handle, ptr, 40)
                if str_buf:
                    try:
                        name = str_buf.decode('utf-16-le').split('\x00')[0]
                        if name and len(name) >= 3 and name.replace(' ','').isalpha():
                            print(f"Found staff entry at 0x{region_base + offset:X}: {name}")
                    except:
                        pass

print("Done")
CloseHandle(handle)