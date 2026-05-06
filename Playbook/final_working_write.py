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

pid = 58172
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

WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL

# I think what might work is to target a pointer address we found - look at that 0x2FFCA19D0 and find team structure around that directly from memory where we're finding references to this address - let me find any direct references to this in the team area

# Searching for references from team's address to known working playbooks - as a simpler step I'll use target addresses we know function and modify them with our specific test to identify which one is truly used. The most likely answer is to make our writes stand out!

testing_offset = 0xDEED  # Special code - unique, obviously wrong for normal play but indicates write worked, should make index 0 completely change (display unknown or blank)

# We'll test a set that I think is best: modify to our working playbook addresses we confirmed can read from properly earlier

# The addresses known good: use this as primary base
work_playbook_addresses = [0x2FFCA19D0]

for test_addr_check in work_playbook_addresses:
    if mem_write(hproc, test_addr_check, struct.pack('<I', testing_offset)):
        print('Test 1 - Wrote {} to {} successfully'. format(testing_offset, hex(test_addr_check)))
        
        # Confirm immediately  
        check_val = mem_read(hproc, test_addr_check, 4)
        if check_val:
            retrieved = struct.unpack('<I', check_val)[0]
            print(f'Read back: {hex(retrieved)}')
            # Only proceed if confirmed our test value (0xDEED)
            if retrieved == testing_offset:
                # Now find actual play index values to use as replacement
                # We'll use three actual valid known play offsets for testing in indices 0-4
                
                valid_known_play_offsets = [550, 712, 896]  # FIST 21, CHEST, MIL34 for example
                
                print('Now writing these real offsets to test locations in same base:')
                for i in range(3):
                    # At i*0x30 offset from this base
                    target = test_addr_check + (i * 0x30)
                    if mem_write(hproc, target, struct.pack('<I', valid_known_play_offsets[i])):
                        print(f'  Index {i}: Wrote play offset {valid_known_play_offsets[i]} => should show as playable #{i}')
                
                print('Now verify these writes:')
                for i in range(3):
                    target = test_addr_check + (i * 0x30)
                    reading = mem_read(hproc, target, 4)
                    if reading:
                        retrieved2 = struct.unpack('<I', reading)[0]
                        print(f'  Location {hex(target)} index {i} =  {retrieved2} (expected {valid_known_play_offsets[i]})')

# If none of these show up in-game then we know this memory area isn't active during runtime, so more investigation will be warranted

CloseHandle(hproc)