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

import subprocess
result = subprocess.run(['powershell', '-Command', '(Get-Process NBA2K26).Id'], capture_output=True, text=True)
pid = int(result.stdout.strip())
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t(0)
    if ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count)):
        return bytes(buf)
    return None

# Instead, let's look at what's at the OFFSET 550 from the team offset and see if it's a direct address
# Or look at the offset in team and see what we get if we interpret it DIFFERENTLY

phi_addr = 0x2A82E17D0
phi_data = mem_read(hproc, phi_addr, 5672)

# Current value at +0x464 is 712 (we wrote that)
first_play_offset = struct.unpack('<I', phi_data[0x464:0x468])[0]
print('Current first play value at team+0x464:', first_play_offset, '({})'.format(hex(first_play_offset)))

# Maybe instead of OFFSET into string block, it's actually an ABSOLUTE POINTER to the string data?
# Or maybe it's an INDEX into another array?

# Let's look at bytes AROUND this value to see patterns
print('\nLooking at team+0x460 to team+0x500 area:')
for offset in range(0x460, 0x500, 4):
    val = struct.unpack('<I', phi_data[offset:offset+4])[0]
    print('  team+0x{:x}: {}'.format(offset, hex(val)))

# Maybe interpret as pointers directly to where strings are
# Let's see if value 550 is actually at 0x2FFCD8000 + 550 or similar
possible_string_base = 0x2FFCD8000 + first_play_offset
print('\nPossible string at {}:'.format(hex(possible_string_base)))
s = mem_read(hproc, possible_string_base, 30)
if s:
    print('Bytes:', s[:20])

# Also try adding to different base addresses
# Perhaps the offset is relative to different base?
for base in [0x2FFCD8000, 0x2FFCA0000, 0x2E000000]:
    try_addr = base + first_play_offset
    data = mem_read(hproc, try_addr, 30)
    if data:
        # Check for UTF-16 null
        has_content = any(b != 0 for b in data[:20])
        if has_content:
            print('\nAt {}: {}'.format(hex(try_addr), data[:20].hex()))

CloseHandle(hproc)