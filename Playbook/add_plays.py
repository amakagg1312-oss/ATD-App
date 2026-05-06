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
WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL

pid = 58172
playbook_base = 0x2FFCA19D0
stride = 0x30
play_string_base = 0x2FFCD8000

hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        return None
    return bytes(buf)

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    ok = WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count))
    return ok and write_count.value == len(data)

# Build play index first
str_data = mem_read(hproc, play_string_base, 0x10000)

play_list = []
i = 0
while i < len(str_data) - 1:
    null_pos = str_data.find(b'\x00\x00', i)
    if null_pos == -1:
        break
    start = null_pos + 2
    if start % 2 != 0:
        start += 1
    next_null = str_data.find(b'\x00\x00', start)
    if next_null == -1:
        next_null = len(str_data)
    play_bytes = str_data[start:next_null]
    if len(play_bytes) >= 4:
        try:
            play_name = play_bytes.decode('utf-16-le', errors='replace').strip()
            if play_name and len(play_name) > 2:
                play_list.append((start, next_null, play_name))
        except:
            pass
    i = null_pos + 2

print('Indexed {} plays'.format(len(play_list)))

# Find specific plays we want to add
# We'll use plays we KNOW exist from previous research
test_plays = [
    "FIST 21 IVERSON",
    "FIST CHEST FLARE",
    "MIL FIST 34 DOWN SLIP",
    "'16 MEM PUNCH 5 WEAK",
    "'06 POR FIST 15 UP"
]

# Find their offsets
play_offsets = {}
for target in test_plays:
    for offset, end, name in play_list:
        if target in name:
            play_offsets[target] = offset
            print('Found "{}" at offset {}'.format(name, offset))
            break

print('')
print('=== BEFORE: Current first 10 plays ===')
for i in range(10):
    data = mem_read(hproc, playbook_base + i * stride, 4)
    if data:
        off = struct.unpack('<I', data)[0]
        print('[{}] offset {}: {}'.format(i, off, 'used' if off else 'empty'))

# Now let's modify entries 50-54 (last 10) to show our test plays
# We'll use indices 50-54 to not disturb the first 10 plays

# The plays to write:
# Index 50: FIST 21 IVERSON
# Index 51: FIST CHEST FLARE
# Index 52: MIL FIST 34 DOWN SLIP
# Index 53: '16 MEM PUNCH 5 WEAK
# Index 54: '06 POR FIST 15 UP

modifications = [
    (50, "FIST 21 IVERSON", play_offsets.get("FIST 21 IVERSON")),
    (51, "FIST CHEST FLARE", play_offsets.get("FIST CHEST FLARE")),
    (52, "MIL FIST 34 DOWN SLIP", play_offsets.get("MIL FIST 34 DOWN SLIP")),
    (53, "'16 MEM PUNCH 5 WEAK", play_offsets.get("'16 MEM PUNCH 5 WEAK")),
    (54, "'06 POR FIST 15 UP", play_offsets.get("'06 POR FIST 15 UP")),
]

print('')
print('=== WRITING plays to indices 50-54 ===')
for idx, name, offset in modifications:
    if offset:
        packed = struct.pack('<I', offset)
        success = mem_write(hproc, playbook_base + idx * stride, packed)
        if success:
            print('Wrote "{}" (offset {}) to index {}'.format(name, offset, idx))
        else:
            print('FAILED to write "{}"'.format(name))
    else:
        print('Could not find offset for "{}"'.format(name))

print('')
print('=== AFTER: Modified entries 50-54 ===')
for i in range(50, 55):
    data = mem_read(hproc, playbook_base + i * stride, 4)
    if data:
        off = struct.unpack('<I', data)[0]
        # Find the play name
        play_name = 'NOT FOUND'
        for s, e, n in play_list:
            if s == off:
                play_name = n
                break
        print('[{}] offset {}: {}'.format(i, off, play_name))

print('')
print('SUCCESS! Written 5 test plays to 76ers playbook.')
print('In the game, check BLOB 06 (indices 50-59) to see the modified plays.')

CloseHandle(hproc)