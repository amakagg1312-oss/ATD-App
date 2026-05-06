import struct
import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_ALL_ACCESS = 0x1F0FFF
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD), ('szExeFile', ctypes.c_wchar * 260)]

class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('th32ModuleID', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD), ('GlblcntUsage', wintypes.DWORD), ('ProccntUsage', wintypes.DWORD), ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)), ('modBaseSize', wintypes.DWORD), ('hModule', wintypes.HMODULE), ('szModule', ctypes.c_wchar * 256), ('szExePath', ctypes.c_wchar * 260)]

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE
CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL
ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
ReadProcessMemory.restype = wintypes.BOOL
CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
CreateToolhelp32Snapshot.restype = wintypes.HANDLE
Process32FirstW = kernel32.Process32FirstW
Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
Process32FirstW.restype = wintypes.BOOL
Process32NextW = kernel32.Process32NextW
Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
Process32NextW.restype = wintypes.BOOL
Module32FirstW = kernel32.Module32FirstW
Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
Module32FirstW.restype = wintypes.BOOL
Module32NextW = kernel32.Module32NextW
Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
Module32NextW.restype = wintypes.BOOL

def find_pid(exe_name):
    target = exe_name.lower()
    snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE_VALUE: return None
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    pid = None
    try:
        if Process32FirstW(snap, ctypes.byref(entry)):
            while True:
                if entry.szExeFile.lower() == target:
                    pid = entry.th32ProcessID
                    break
                if not Process32NextW(snap, ctypes.byref(entry)): break
    finally:
        CloseHandle(snap)
    return pid

def get_module_base(pid, module_name):
    target = module_name.lower()
    flags = TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32
    snap = CreateToolhelp32Snapshot(flags, pid)
    if snap == INVALID_HANDLE_VALUE: return None
    me32 = MODULEENTRY32W()
    me32.dwSize = ctypes.sizeof(MODULEENTRY32W)
    base = None
    try:
        if Module32FirstW(snap, ctypes.byref(me32)):
            while True:
                if me32.szModule.lower() == target:
                    base = ctypes.cast(me32.modBaseAddr, ctypes.c_void_p).value
                    break
                if not Module32NextW(snap, ctypes.byref(me32)): break
    finally:
        CloseHandle(snap)
    return base

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t()
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n: return None
    return bytes(buf)

def read_uint64(hproc, addr):
    data = mem_read(hproc, addr, 8)
    if data: return struct.unpack('<Q', data)[0]
    return None

def read_uint32(hproc, addr):
    data = mem_read(hproc, addr, 4)
    if data: return struct.unpack('<I', data)[0]
    return None

def read_float(hproc, addr):
    data = mem_read(hproc, addr, 4)
    if data: return struct.unpack('<f', data)[0]
    return None

def is_valid_pointer(addr, module_base, module_size):
    return module_base <= addr < module_base + module_size

pid = find_pid('NBA2K26.exe')
if not pid:
    pid = 51204
module_base = get_module_base(pid, 'NBA2K26.exe')
if not module_base:
    print('Failed to get module base')
    exit(1)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

team_rva = 0x7E1E318
ptr_addr = module_base + team_rva
table_base = read_uint64(hproc, ptr_addr)

print('Team table base: 0x{:X}'.format(table_base))
print('Module base: 0x{:X}'.format(module_base))

# Dump the team struct and identify all pointers
team_size = 5672
team_data = mem_read(hproc, table_base, team_size)

print('\n=== Team Struct Analysis ===')
print('Looking for pointers that might lead to playbook data...\n')

# Find all 64-bit pointers in the team struct
pointers = []
for i in range(0, team_size - 7, 8):
    val = struct.unpack_from('<Q', team_data, i)[0]
    # Check if it's a valid pointer (within heap range, typically 0x200000000+)
    if 0x200000000 <= val < 0x300000000:
        pointers.append((i, val))

print('Found {} pointers in team struct:'.format(len(pointers)))
for offset, addr in pointers:
    # Read some data at the pointer target
    target_data = mem_read(hproc, addr, 64)
    if target_data:
        ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in target_data[:40])
        print('  Offset 0x{:04X} -> 0x{:X}: {}'.format(offset, addr, ascii_repr))

# Now look for pointers that point to data blocks that might contain play IDs
# Play IDs are likely stored as arrays of integers or short strings
print('\n=== Searching for playbook-like data structures ===')

# Look for arrays of small integers (potential play IDs) near the team struct
for ptr_offset, ptr_addr in pointers:
    # Read the first few values at the pointer target
    data = mem_read(hproc, ptr_addr, 256)
    if data is None:
        continue
    
    # Check if it looks like an array of small integers (play IDs)
    values = []
    for i in range(0, min(64, len(data)-3), 4):
        val = struct.unpack_from('<I', data, i)[0]
        values.append(val)
    
    # Look for patterns: many small values (< 1000) could be play IDs
    small_count = sum(1 for v in values if 0 < v < 1000)
    if small_count > 10:
        print('  Pointer at offset 0x{:04X} (0x{:X}) has {} small values:'.format(ptr_offset, ptr_addr, small_count))
        print('    First 20 values: {}'.format(values[:20]))

CloseHandle(hproc)
print('\nDone.')
