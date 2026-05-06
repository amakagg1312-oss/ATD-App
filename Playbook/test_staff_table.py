import sys, struct
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

# Search for staff table by looking for valid staff entries
# Staff stride = 432, first_name at 0x28, last_name at 0x0
# Look for entries where first_name offset has readable data

staff_stride = 432
staff_first_offset = 0x28

print("Searching for staff table...")

# Scan game memory for potential staff bases
for region_base, region_size, _ in iter_memory_regions(handle, 0x27000000, 0x28000000):
    try:
        buf = read_memory(handle, region_base, region_size)
    except:
        buf = None
    if not buf or region_size < staff_stride * 5:
        continue
    
    # Look for consecutive entries with valid-looking data at first_name offset
    for offset in range(0, region_size - staff_stride * 3, 4):
        # Check if this could be a staff base
        # Read first_name at offset + 0x28 for 3 consecutive entries
        valid = 0
        for slot in range(3):
            entry_start = offset + slot * staff_stride
            name_off = entry_start + staff_first_offset
            if name_off + 4 <= region_size:
                # Check if there's non-zero data
                val = struct.unpack('<I', buf[name_off:name_off+4])[0]
                if val > 0:
                    valid += 1
        
        if valid >= 2:
            print(f"Potential staff table at 0x{region_base + offset:X}")
            break

print("Done")
CloseHandle(handle)