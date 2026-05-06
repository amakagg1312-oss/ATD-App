import struct
import ctypes
from ctypes import wintypes
import sys
import io
import json

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
play_string_base = 0x2FFCD8000
playbook_base = 0x2FFCA1910
stride = 0x30

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

# Read play string block
play_data = mem_read(hproc, play_string_base, 0x10000)

# Build lookup with search for each string
# Method: scan for valid UTF-16 strings and create mapping
play_names = {}  # byte_offset -> play_name
i = 0
while i < len(play_data) - 2:
    # Look for UTF-16 null terminator
    if play_data[i] == 0 and play_data[i+1] == 0:
        i += 2
        continue
    
    # Try to decode as UTF-16 from this position
    if i + 10 <= len(play_data):
        try:
            raw = play_data[i:i+80]
            decoded = raw.decode('utf-16-le', errors='replace')
            # Valid play name: at least 4 chars, contains letters
            stripped = decoded.strip('\x00')
            if len(stripped) >= 4 and any(c.isalpha() for c in stripped[:10]):
                # Check if mostly printable
                valid_chars = sum(1 for c in stripped[:30] if c.isprintable() or c in "'- ")
                if valid_chars > 10:
                    play_names[i] = stripped[:40]
        except:
            pass
    i += 2

print('Found {} plays'.format(len(play_names)))

# Read playbook entries
print('\n=== 76ers Playbook (60 plays) ===')
print('Index | Offset | Memory Play Name')
print('='*60)

playbook_read = []
for idx in range(60):
    addr = playbook_base + idx * stride
    data = mem_read(hproc, addr, 4)
    if data:
        offset = struct.unpack('<I', data)[0]
        
        # Try exact match first
        name = play_names.get(offset)
        
        # If not exact, search within small range
        if not name:
            for delta in range(-10, 11):
                if offset + delta in play_names:
                    name = play_names[offset + delta]
                    break
        
        playbook_read.append({'index': idx, 'offset': offset, 'name': name or '<NOT FOUND>'})
        
        print('{:4d} | {:5d} | {}'.format(idx, offset, name or '<NOT FOUND>'))

# Save results
output = {
    'base_address': hex(playbook_base),
    'stride': stride,
    ' Plays': playbook_read
}

with open('D:\\project\\Playbook\\76ers_verify_output.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print('\nSaved to 76ers_verify_output.json')

# Now compare with screenshot plays
print('\n=== COMPARISON WITH SCREENSHOT ===')
# From screenshot in order: Row1 (plays 0-9):
# FIST 64 STS, CLE FIST 15 DRA, SAS FIST 15 FLAT OU, FIST 21 IVERSON, FIST CHEST FLAR...
screenshot_first_10 = [
    "FIST 64 STS",
    "CLE FIST 15 DRA",
    "SAS FIST 15 FLAT OU",
    "FIST 21 IVERSON",
    "FIST CHEST FLAR",
    "'06 POR FIST 15 U",
    "MIL FIST 34 DOWN SLI",
    "FIST 64 ST",
    "'06 POR FIST 15 U",
    "'16 MEM PUNCH 5 WEA"
]

# Find their actual offsets in the string block
actual_offsets = {}
for name in screenshot_first_10:
    for offset, play_name in play_names.items():
        if name in play_name or play_name.startswith(name):
            actual_offsets[name] = offset
            break
    else:
        actual_offsets[name] = None

print('\nScreenshot plays → Actual memory offsets:')
for i, name in enumerate(screenshot_first_10):
    mem_offset = actual_offsets.get(name)
    playbook_offset = playbook_read[i]['offset'] if i < len(playbook_read) else None
    playbook_name = playbook_read[i]['name'] if i < len(playbook_read) else None
    
    match = '✓' if mem_offset == playbook_offset else '✗'
    print('[{}] {}'.format(i, name))
    print('    Memory offset:      {}'.format(mem_offset))
    print('    Playbook offset:   {}'.format(playbook_offset))
    print('    Playbook name:   {}'.format(playbook_name[:25] if playbook_name and len(playbook_name) > 25 else playbook_name))
    print('    Match: {}'.format(match))

CloseHandle(hproc)