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
    _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG), ('dwFlags', wintypes.DWORD), ('szExeFile', ctypes.c_wchar * 260)]

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

pid = find_pid('NBA2K26.exe')
module_base = get_module_base(pid, 'NBA2K26.exe')
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

team_rva = 0x7E1E318
ptr_addr = module_base + team_rva
table_base = read_uint64(hproc, ptr_addr)

# The team struct at offset 0x200+ might contain playbook data
# Let's dump the full team struct and look for patterns
team_addr = table_base + 5672  # Bucks index 1
team_data = mem_read(hproc, team_addr, 5672)

if team_data:
    # Save to file for analysis
    with open(r'D:\project\Playbook\bucks_full_dump.bin', 'wb') as f:
        f.write(team_data)
    
    print(f'Dumped full Bucks team struct: {len(team_data)} bytes')
    print(f'Saved to: D:\project\Playbook\bucks_full_dump.bin')
    
    # Look for any non-zero, non-pointer data in the struct
    # Pointers are 8-byte values > 0x100000000
    print('\nAnalyzing team struct...')
    pointer_regions = []
    data_regions = []
    
    i = 0
    while i < len(team_data):
        if i + 8 <= len(team_data):
            val = struct.unpack('<Q', team_data[i:i+8])[0]
            if 0x100000000 < val < 0x7FF000000000:
                pointer_regions.append((i, val))
                i += 8
                continue
        i += 1
    
    print(f'Found {len(pointer_regions)} pointers in team struct')
    
    # Show non-pointer regions (likely data)
    print('\nNon-pointer data regions (potential playbook data):')
    in_data = False
    data_start = 0
    for i in range(len(team_data)):
        is_pointer = False
        if i + 8 <= len(team_data):
            val = struct.unpack('<Q', team_data[i:i+8])[0]
            if 0x100000000 < val < 0x7FF000000000:
                is_pointer = True
        
        if not is_pointer and team_data[i] != 0:
            if not in_data:
                data_start = i
                in_data = True
        else:
            if in_data:
                length = i - data_start
                if length >= 4:  # Only show regions >= 4 bytes
                    hex_preview = ' '.join(f'{b:02X}' for b in team_data[data_start:min(data_start+32, i)])
                    print(f'  Offset 0x{data_start:04X} - 0x{i-1:04X} ({length} bytes): {hex_preview}')
                in_data = False

CloseHandle(hproc)
