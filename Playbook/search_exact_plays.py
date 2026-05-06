import struct
import ctypes
from ctypes import wintypes
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_ALL_ACCESS = 0x1F0FFF

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE
CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL
ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
ReadProcessMemory.restype = wintypes.BOOL

pid = 58172

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# Find exact plays from screenshot - need EXACT matching
# Looking for:
# - "FIST 15 MIDDLE" 
# - "52 FLAT" (maybe "GIVE 52 FLAT" or similar)
# - "FIST 21 IVERSON" 
# - "FIST CHEST FLARE"
# - "FIST 64 STS"

string_base = 0x2FFCD8000
str_data = mem_read(hproc, string_base, 0x10000)

# Build index of ALL plays with their exact names
plays_by_offset = {}
for offset in range(0, len(str_data) - 4, 2):
    # Look for UTF-16 null pattern: \x00\x00 then start of new string
    if str_data[offset] == 0 and str_data[offset+1] == 0:
        start = offset + 2
        if start % 2 != 0:
            start += 1
        if start >= len(str_data) - 4:
            continue
        
        # Decode this position as UTF-16
        try:
            raw = str_data[start:start+100]
            decoded = raw.decode('utf-16-le', errors='replace')
            # Get first null-terminated string
            first_str = decoded.split('\x00')[0].strip()
            if first_str and len(first_str) >= 5:
                # Check if mostly alphabetic
                alpha_count = sum(1 for c in first_str if c.isalpha() or c == "'")
                if alpha_count >= len(first_str) * 0.5:
                    plays_by_offset[start] = first_str
        except:
            pass

print('Found {} play strings'.format(len(plays_by_offset)))

# Now find specific plays by exact name
search_plays = [
    "FIST 15 MIDDLE",
    "52 FLAT", 
    "FIST 21 IVERSON",
    "FIST CHEST FLARE",
    "FIST 64 STS",
    "'06 POR FIST 15",
    "MIL FIST 34 DOWN SLIP",
    "'16 MEM PUNCH 5 WEAK"
]

print('\n=== Finding exact plays ===')
for search in search_plays:
    found = False
    for off, name in plays_by_offset.items():
        # Check exact or very close match
        if search == name or search in name or name in search:
            print('  "{}" Found at offset {}: "{}"'.format(search, off, name))
            found = True
            break
    if not found:
        # Show candidates that might match
        candidates = []
        for off, name in plays_by_offset.items():
            if search.split()[0] in name or (len(search.split()) > 1 and search.split()[1] in name):
                candidates.append((off, name))
        if candidates:
            print('  "{}" - Close matches: {}'.format(search, [(n, plays_by_offset[o]) for o, n in candidates[:3]]))
        else:
            print('  "{}" - NOT FOUND'.format(search))

# Now manually check the correct target offsets
print('\n=== Verified target offsets ===')
target_off = {
    "FIST 15 MIDDLE": None,
    "52 FLAT": 1958,
    "FIST 21 IVERSON": 557,
    "FIST CHEST FLARE": 742,
    "FIST 64 STS": 2252,
    "'06 POR FIST 15 U": 2558,
    "MIL FIST 34 DOWN SLI": 896,
    "'16 MEM PUNCH 5 WEA": 1245
}

for name, off in target_off.items():
    if off in plays_by_offset:
        print('  Offset {} = "{}"'.format(off, plays_by_offset[off]))

# Now scan more carefully around different base addresses to find sequence
print('\n=== Looking for playbook containing specific offset sequences ===')

# We need sequence like [FIST 15 MIDDLE or 52 FLAT, FIST 21 IVERSON, etc.]
# Check bases in wider range with stride 0x30

def find_name(off):
    if off in plays_by_offset:
        return plays_by_offset[off]
    # Search nearby
    for delta in range(-5, 6):
        if off + delta in plays_by_offset:
            return plays_by_offset[off + delta]
    return None

# Test specific base candidates around 0x2FFCA1910 (what we used before was wrong)
base_candidates = [
    0x2FFCA1910,
    0x2FFCA19D0,
    0x2FFCA1A30,
    0x2FFCA1590,
    0x2FFCA1500,
    0x2FFCA1000,
    0x2FFCAB000,
]

for test_base in base_candidates:
    data = mem_read(hproc, test_base, 0x30 * 10)
    if not data:
        continue
    
    first_10 = []
    for idx in range(10):
        off = struct.unpack('<I', data[idx*0x30:idx*0x30+4])[0]
        name = find_name(off)
        first_10.append((off, name))
    
    # Check how many match known plays
    matches = 0
    for off, name in first_10:
        if name:
            if "FIST 21 IVERSON" in name:
                matches += 1
            if "FIST CHEST" in name:
                matches += 1
            if "FIST 64 STS" in name:
                matches += 1
            if "MIL FIST" in name:
                matches += 1
    
    if matches > 0:
        print('\nBase {} has {} matches:'.format(hex(test_base), matches))
        for i, (off, name) in enumerate(first_10[:10]):
            print('  [{}] offset {}: {}'.format(i, off, name))

CloseHandle(hproc)