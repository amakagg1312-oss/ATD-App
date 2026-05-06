import sys, struct
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

# Search for staff-related strings
searches = [
    encode_wstring("COACH"),
    encode_wstring("Coach"),
    encode_wstring("STAFF"),
    encode_wstring("Assistant"),
    encode_wstring("Trainer"),
]

for search in searches:
    print(f"Searching for: {search}")
    for region_base, region_size, _ in iter_memory_regions(handle, 0x27000000, 0x28000000):
        try:
            buf = read_memory(handle, region_base, region_size)
        except:
            buf = None
        if buf and search in buf:
            idx = buf.find(search)
            print(f"  Found at 0x{region_base + idx:X}")

print("Done")
CloseHandle(handle)