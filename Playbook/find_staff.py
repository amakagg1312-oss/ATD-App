"""Quick search for staff given team address"""

import psutil
import ctypes
import struct
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.OpenProcess.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_int]
RPM = kernel.ReadProcessMemory
RPM.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p.pid
    return None

def read_mem(handle, addr, size):
    buf = create_string_buffer(size)
    if RPM(handle, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

pid = find_process()
if not pid:
    print("Game not running")
    exit(1)

h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
print(f"PID: {pid}")

# Search for team base - look for team_id (0-30) at offset 0x130
team_addrs = []
for base in range(0x27000000, 0x28000000, 0x100000):
    raw = read_mem(h, base, 0x100000)
    if not raw:
        continue
    for i in range(0, len(raw) - 0x200, 4):
        team_id = struct.unpack('<I', raw[i:i+4])[0]
        if 0 <= team_id <= 30:
            playbook_offset = 0x130
            if i + playbook_offset + 4 <= len(raw):
                count = struct.unpack('<I', raw[i+playbook_offset:i+playbook_offset+4])[0]
                if 50 <= count <= 100:
                    team_addr = base + i
                    team_addrs.append(team_addr)
                    print(f"Found team at 0x{team_addr:X}, id={team_id}, count={count}")
                    break

# From user data: Packed set staff offset from team is 0xC4 (196)
for team_addr in team_addrs[:3]:
    print(f"\n--- Checking team at 0x{team_addr:X} ---")
    # Try staff offsets from your data
    # Set A/B/C: staff - team = 0x758 (1880)
    # Packed: staff - team = 0xC4 (196)
    for offset in [0xC4, 0x200, 0x300, 0x400, 0x500, 0x600, 0x700, 0x758, 0x800]:
        staff_addr = team_addr + offset
        raw = read_mem(h, staff_addr, 100)
        if raw:
            # Look for non-zero data
            if raw[:20] != b'\x00' * 20:
                print(f"Staff ptr at 0x{staff_addr:X} (+0x{offset:X}):")
                # First 8 bytes might be a pointer
                ptr = struct.unpack('<Q', raw[:8])[0]
                print(f"  First ptr: 0x{ptr:X}")
                if ptr and 0x10000 < ptr < 0x2000000000:
                    staff_data = read_mem(h, ptr, 200)
                    if staff_data:
                        print(f"  Staff data: {staff_data[:100]}")