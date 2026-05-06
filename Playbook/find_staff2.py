import psutil, ctypes, struct
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer, c_void_p

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = c_void_p
RPM = kernel.ReadProcessMemory
RPM.argtypes = [c_void_p, c_void_p, c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

pid = [p.pid for p in psutil.process_iter() if 'NBA2K26' in p.name()][0]
h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)

# Search for staff table by looking for consecutive entries with valid data
# Staff stride = 432, first_name at 0x28

# Try around the team area
for base in range(0x27000000, 0x28000000, 0x100000):
    buf = create_string_buffer(0x100000)
    if RPM(h, c_void_p(base), buf, 0x100000, byref(c_size_t(0))):
        raw = buf.raw
        # Look for team_id followed by staff-like pattern
        for i in range(0, len(raw) - 0x200, 4):
            team_id = struct.unpack('<I', raw[i:i+4])[0]
            if 0 <= team_id <= 30:
                # Check offset 0x130 for playbook count
                po = 0x130
                if i + po + 4 <= len(raw):
                    cnt = struct.unpack('<I', raw[i+po:i+po+4])[0]
                    if 50 <= cnt <= 100:
                        # Found a team - check nearby for staff
                        team_addr = base + i
                        # Try different offsets for staff
                        for staff_off in [0x758, 0x800, 0x900, 0xA00, 0xB00, 0xC00]:
                            staff_addr = team_addr + staff_off
                            if staff_addr < base + len(raw):
                                staff_data = raw[staff_addr - base:staff_addr - base + 50]
                                if staff_data[:20] != b'\x00' * 20:
                                    print(f"Team {team_id} at 0x{team_addr:X}, staff+0x{staff_off:X}: {staff_data[:30]}")
                        break