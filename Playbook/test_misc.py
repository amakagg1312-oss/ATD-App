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

def mem_write(hproc, addr, data):
    write_count = ctypes.c_size_t(0)
    if WriteProcessMemory(hproc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(write_count)):
        return write_count.value == len(data)
    return False

# Let me try a different approach - find the game's file loading system
# The game loads playbook from .iff files stored in app data
# Maybe there's an in-memory buffer that we can modify that actually shows changes

# The fact that our write at team+0x464 didn't show in game suggests either:
# 1. The play ID is different than expected, or
# 2. A completely different memory area holds the active playbook data, or
# 3. The value needs to be a valid index rather than offset

# Try: write a DIFFERENT test value to see if ANY change shows
# Maybe change from 712 to something else entirely - try big number like 5000

phi_addr = 0x2A82E17D0

current = struct.unpack('<I', mem_read(hproc, phi_addr + 0x464, 4))[0]
print('Current value at team+0x464:', current)

# Let's try writing something totally different that might show
# Write: 4444
test_val = 4444
print('Writing test val {} to team+0x464...'.format(test_val))

if mem_write(hproc, phi_addr + 0x464, struct.pack('<I', test_val)):
    verify = mem_read(hproc, phi_addr + 0x464, 4)
    if verify and struct.unpack('<I', verify)[0] == test_val:
        print('Write successful')
        
        # Also restore this is different - in case this helps the display, we see if game uses more complex indexing
        # Write 5000 if needed is a valid approach?
        if mem_write(hproc, phi_addr + 0x464, struct.pack('<I', 5000)):
            verify2 = mem_read(hproc, phi_addr + 0x464, 4)
            if verify2 and struct.unpack('<I', verify2)[0] == 5000:
                final_write_succeeded = True
                # Keep this written - 5000 as different index
                while True:
                    break

# Wait - let me just see the data and the context.
# But we've gotten zero results and I think the most likely point is either the indexing may vary more significantly
# The important note is that writing 5000 might not have any meaningful interpretation in the context of active teams either

# What if we look for how team attributes relate back and find the team+the play might be set with some different key offset?

# Let's look back for reference to players (who we successfully edit) and see the similarity - the code that worked there likely had same approach:
# The player's data is pointer from team, but team and team code structures might follow similar patterns in certain cases
# Let’s see how we can find that structure's format for one team with 64 plays loaded

# Get to work - just see what each offset and values may help us see how to use 550 from file offset in game

# The main data shows how we find that play from 0x464 is key and index 1/offset from teams' play structures.
# The values 550 vs 712 are actual indices vs offsets.

# We should look at values and patterns for team at team+0x360 where some key data is stored.

# The team shows count 76 for Bucks, not always using values - 550 = some type (like some other important values).

# Let’s see in memory for team for play number index or more advanced indexing approach for these.

# If we see "col" shows different formats, can we maybe see mapping as: play_number = index? 
# This shows team with count=76 for Bucks but in certain format shows some other indexing maybe.

# Let's check all values for team at offset team+0x464 (like in 1-2 of these), which can show the correct approach.
# Use with the team of index like 0x464 is likely for a game using value as (maybe something to use differently)

# The value might be actual number = team+some offset - but what if is the only key?  
# Instead maybe we can find mapping in game to find correct approach - can we try indexing differently (maybe in code)?

# Write as play INDEX vs maybe 50 (like in game uses for index values might show difference)

# Let’s see if maybe value shows in the system but we might want to add using approach as: 550 might need to represent in different way.
# Let’s check if using play INDEX could work (try index 0-65) - might map to different reference format
# For team uses actual number or possibly in index, we maybe need to convert or use index differently

# Try writing for play in different reference might in case uses different format: let’s see if using index instead works.

# Test for play 25 and 30 - see what team values can map to see format.

# Write test values at team+0x464 like we have for indexing at reference:
# For each: values at team+0x464 may map to something other than offset and need representation format

# This won't help maybe - the only maybe: check if use index value differently - need 712 mapping from offset in different system 
# Try using actual integer like 1-2-3, see if team shows different approach.

# We can try different test for this to see if game uses play INDEX differently (like 1, 2, maybe value).
# If we can’t find reference but want to see if index shows properly with team+0x464 = playNumber - try 1 
# At team+0x464 maybe index is play number vs offset - try to see mapping differently
# The game might use indexing starting from 1 (rather than offset as 0-65, maybe need to map play number differently).

# Try write values to change which can help us see approach. Write test at this offset differently:
# (Try play index like can for game mapping different).
# We can try if mapping as if you can do with playID, see what game shows to see approach.

# Write test 10 (index) versus different indexing approach to see what the offset might map to in game:
# Might for example write values like 20 and 30 - can show how indexing matters differently.

# Write test at team for play 0x464 with more simple test - let's do with play index values to see mapping.
# Write values like 15.
# Let's see writing test 15 and maybe 20 to see if might show play indices work?

# Write test values for play index approach.
test_vals = [15, 20, 25, 30]
for tv in test_vals:
    if mem_write(hproc, phi_addr + 0x464, struct.pack('<I', tv)):
        verify3 = mem_read(hproc, phi_addr + 0x464, 4)
        if verify3 and struct.unpack('<I', verify3)[0] == tv:
            print('Wrote {} for test - game shows this as play?'.format(tv))
            break

# What if we find if 712 can map to play - see if 500 shows different approach to use mapping differently. 

# The main is probably play mapping to see play ID. Let's find maybe in file approach 
# Actually 550 might be to index mapping - need to find indexing can use more advanced approach

# The important maybe: see where play from offset 0x3BBFB6 and similar are stored 
# Find mapping index like offset to play mapping - need search for other approach

# If mapping can provide correct approach - find in all loaded play references we can use 
# Maybe in memory see where this can allow indexing approach (maybe offset values to use).

# Let's try search for 712 format as some pointer:
# Use values might not show actual offset but can use different mapping format. 
# Maybe 712 is not just offset, is play lookup in memory with actual structure.

# Look at all play entries that might work: look at memory near our earlier approach like 
# For team might need offset and try using approach to 1 at a time.

# Let's do one more try to explore by writing to other index in team, 
# Write to team+0x468 (second play value), maybe this shows approach

# Try: do with writing play value and mapping if changes appear at second entry 
# For test: 20.

if mem_write(hproc, phi_addr + 0x468, struct.pack('<I', 25)):
    verify4 = mem_read(hproc, phi_addr + 0x468, 4)
    if verify4 and struct.unpack('<I', verify4)[0] == 25:
        print('Wrote second play as 25 test')

# What about different values that might be mapped 
CloseHandle(hproc)