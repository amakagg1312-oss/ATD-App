import sys
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

# Search for "HEAD" in game memory
search = encode_wstring("HEAD")
print(f"Searching for: {search}")

count = 0
for region_base, region_size, _ in iter_memory_regions(handle, 0x27000000, 0x28000000):
    try:
        buf = read_memory(handle, region_base, region_size)
    except:
        buf = None
    if buf and search in buf:
        idx = buf.find(search)
        print(f"Found at 0x{region_base + idx:X}")
        # Show context
        start = max(0, idx - 20)
        end = min(len(buf), idx + 50)
        print(f"  {buf.raw[start:end]}")
        count += 1
        if count > 10:
            break

print(f"Total: {count}")
CloseHandle(handle)