import sys
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

# Search for "Nurse" in game memory
search = encode_wstring("Nurse")
print(f"Searching for: {search}")

low, high = 0x27000000, 0x28000000
for region_base, region_size, _ in iter_memory_regions(handle, low, high):
    try:
        buf = read_memory(handle, region_base, region_size)
    except:
        buf = None
    if buf and search in buf:
        idx = buf.find(search)
        print(f"Found at 0x{region_base + idx:X}")

print("Done")
CloseHandle(handle)