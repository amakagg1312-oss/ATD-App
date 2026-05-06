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

def read_uint16(hproc, addr):
    data = mem_read(hproc, addr, 2)
    if data: return struct.unpack('<H', data)[0]
    return None

def read_string_utf16(hproc, addr, max_len=100):
    result = []
    for i in range(0, max_len * 2, 2):
        data = mem_read(hproc, addr + i, 2)
        if not data: break
        ch = struct.unpack('<H', data)[0]
        if ch == 0: break
        result.append(chr(ch))
    return ''.join(result)

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

# Examine the data blocks at offsets 0x1020-0x10B8
interesting_offsets = [0x1020, 0x1028, 0x1030, 0x1058, 0x1060, 0x1068, 0x1070, 0x1078, 0x1080, 0x1088, 0x1090, 0x1098, 0x10A0, 0x10A8, 0x10B0, 0x10B8]

for offset in interesting_offsets:
    addr = read_uint64(hproc, table_base + offset)
    if not addr:
        continue
    
    print('\n=== Offset 0x{:04X} -> 0x{:X} ==='.format(offset, addr))
    
    # Read 512 bytes at the target
    data = mem_read(hproc, addr, 512)
    if data is None:
        continue
    
    # Print as hex dump
    for i in range(0, min(256, len(data)), 16):
        hex_str = ' '.join('{:02X}'.format(b) for b in data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print('  0x{:04X}: {:48s} {}'.format(i, hex_str, ascii_str))
    
    # Try to interpret as array of uint32
    print('  As uint32 array:')
    values = []
    for i in range(0, min(128, len(data)-3), 4):
        val = struct.unpack_from('<I', data, i)[0]
        values.append(val)
    print('    {}'.format(values[:20]))
    
    # Try to interpret as array of uint16
    print('  As uint16 array:')
    values16 = []
    for i in range(0, min(128, len(data)-1), 2):
        val = struct.unpack_from('<H', data, i)[0]
        values16.append(val)
    print('    {}'.format(values16[:30]))

CloseHandle(hproc)
print('\nDone.')
