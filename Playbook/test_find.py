import sys
sys.path.insert(0, 'Playbook')
from find_bases_dynamic import *

pid = find_process_pid()
print(f"PID: {pid}")
if not pid:
    print("Game not running")
    exit(1)

handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
print(f"Handle: {handle}")

cfg = load_stride_and_name_offsets()
print(f"Config: stride={cfg['staff_stride']}, first_off={cfg['staff_first_offset']}")

# Just try to find Nick Nurse
staff_targets = [("Nick", "Nurse")]
staff_stride = cfg["staff_stride"] or 432
staff_first_offset = cfg["staff_first_offset"]
staff_last_offset = cfg["staff_last_offset"]
staff_name_length = cfg["staff_name_length"]

print(f"Searching for Nick Nurse...")
print(f"  stride={staff_stride}, first_off={staff_first_offset}, last_off={staff_last_offset}")

staff_hits, staff_base_votes = scan_player_names(
    handle,
    staff_stride,
    staff_first_offset,
    staff_last_offset,
    staff_name_length,
    staff_targets,
    window=12,
    min_matches=1,
)

print(f"Hits: {len(staff_hits)}")
for h in staff_hits:
    print(f"  {h}")

top_staff = summarize_candidates(staff_base_votes)
print(f"Candidates: {top_staff}")

CloseHandle(handle)