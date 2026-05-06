"""Find team table by searching for roster arrays."""

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import struct

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.OpenProcess.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_int]
kernel.ReadProcessMemory.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, 
    c_size_t, ctypes.POINTER(c_size_t)
]

def read_memory(h, addr, size):
    buf = create_string_buffer(size)
    if kernel.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p.pid
    return None

def main():
    pid = find_process()
    if not pid:
        print("NBA2K26.exe not running!")
        return
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    # We know Nick Nurse's roster array is at 0x2A82B17D0
    # This is pointed to by staff entry at 0x018
    
    # The team table should have similar roster arrays
    # Let's search for the team table by looking for a structure that contains
    # roster array pointers
    
    # First, let's examine the region around the staff roster arrays
    # Staff roster arrays are at:
    # Nick Nurse: 0x2A82B17D0
    # Doc Rivers: 0x2A82B2DF8
    # Billy Donovan: 0x2A82B4420
    # Kenny Atkinson: 0x2A82B5A48
    # Joe Mazzulla: 0x2A82B7070
    
    # These are spaced by 0x1628 (5672) - same as team stride!
    # So the staff roster arrays ARE in the team table!
    
    print("Staff roster array locations:")
    staff_roster_addrs = [0x2A82B17D0, 0x2A82B2DF8, 0x2A82B4420, 0x2A82B5A48, 0x2A82B7070]
    for i, addr in enumerate(staff_roster_addrs):
        if i > 0:
            diff = addr - staff_roster_addrs[i-1]
            print(f"  [{i}] 0x{addr:X} (diff: 0x{diff:X} = {diff})")
        else:
            print(f"  [{i}] 0x{addr:X}")
    
    # The roster arrays are at offset 0x018 in the staff entry
    # So the staff entry base = roster_addr - 0x018
    print(f"\nCalculating staff entry bases:")
    for i, roster_addr in enumerate(staff_roster_addrs):
        staff_base = roster_addr - 0x018
        print(f"  [{i}] Staff base: 0x{staff_base:X}")
    
    # Now let's check if these staff bases match the team table
    # The team name is at offset 0x2E2 from team base
    # Let's read at team_base + 0x2E2 for each
    
    print(f"\nChecking team names at staff bases:")
    for i, roster_addr in enumerate(staff_roster_addrs):
        staff_base = roster_addr - 0x018
        name_addr = staff_base + 0x2E2
        name_data = read_memory(h, name_addr, 40)
        if name_data:
            name = name_data.decode('utf-16-le', errors='ignore').split('\x00')[0]
            print(f"  [{i}] 0x{staff_base:X} -> Team name: '{name}'")
    
    # The staff entries and team entries might be the same structure!
    # Let's dump the full structure at the first staff/team base
    
    print(f"\n{'='*80}")
    print("Dumping team/staff structure...")
    
    team_stride = 5672
    first_base = staff_roster_addrs[0] - 0x018
    
    for i in range(3):
        team_addr = first_base + (i * team_stride)
        raw = read_memory(h, team_addr, 512)
        
        if raw:
            name = raw[0x2E2:0x2E2+48].decode('utf-16-le', errors='ignore').split('\x00')[0]
            print(f"\nTeam {i}: '{name}' @ 0x{team_addr:X}")
            
            # Show all pointers
            for off in range(0, 512, 8):
                val = struct.unpack('<Q', raw[off:off+8])[0]
                if 0x10000000 < val < 0x300000000:
                    ptr_data = read_memory(h, val, 64)
                    if ptr_data:
                        # Check for playbook indices
                        pb_ids = []
                        for j in range(0, 40, 2):
                            w = struct.unpack('<H', ptr_data[j:j+2])[0]
                            if 0 < w < 300:
                                pb_ids.append(w)
                        
                        if len(pb_ids) > 5:
                            print(f"  [{off:03X}] 0x{val:X} -> PLAYBOOK: {pb_ids[:15]}")
                        else:
                            # Check for string
                            try:
                                text = ptr_data[:30].decode('utf-16-le', errors='ignore')
                                printable = ''.join(c if c.isprintable() else '.' for c in text)
                                if len([c for c in printable if c.isalpha()]) > 3:
                                    print(f"  [{off:03X}] 0x{val:X} -> STRING: {printable[:25]}")
                            except:
                                pass

if __name__ == "__main__":
    main()
