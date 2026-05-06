import sys
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

search = encode_wstring("Nurse")
print(f"Searching full memory for: {search}")

count = 0
for region_base, region_size, _ in iter_memory_regions(handle, 0, 0x7FFFFFFFFFFF):
    try:
        buf = read_memory(handle, region_base, region_size)
    except:
        buf = None
    if buf and search in buf:
        idx = buf.find(search)
        print(f"Found at 0x{region_base + idx:X} (region size: 0x{region_size:X})")
        count += 1
        if count > 10:
            break

print(f"Total: {count}")
CloseHandle(handle)