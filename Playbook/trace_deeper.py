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

# Trace the pointer array at offset 0x1020
ptr_array_addr = read_uint64(hproc, table_base + 0x1020)
print('\n=== Tracing pointer array at offset 0x1020 -> 0x{:X} ==='.format(ptr_array_addr))

# Read the pointer array (16 pointers, 8 bytes each = 128 bytes)
ptr_array = mem_read(hproc, ptr_array_addr, 128)
if ptr_array:
    pointers = []
    for i in range(0, 128, 8):
        val = struct.unpack_from('<Q', ptr_array, i)[0]
        if val > 0:
            pointers.append(val)
    
    print('Found {} pointers in array:'.format(len(pointers)))
    
    # Trace first few pointers
    for idx, ptr in enumerate(pointers[:8]):
        print('\n  Pointer {}: 0x{:X}'.format(idx, ptr))
        data = mem_read(hproc, ptr, 128)
        if data:
            # Print hex dump
            for i in range(0, min(64, len(data)), 16):
                hex_str = ' '.join('{:02X}'.format(b) for b in data[i:i+16])
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
                print('    0x{:04X}: {:48s} {}'.format(i, hex_str, ascii_str))
            
            # Try to read as UTF-16 string
            s = read_string_utf16(hproc, ptr, 50)
            if s and len(s) > 2:
                print('    UTF-16 string: "{}"'.format(s))

# Also search for playbook data in a wider memory range
print('\n=== Searching for playbook data in 20MB window ===')
search_start = table_base - 0xA00000
search_end = table_base + 0xA00000

# Search for UTF-16 encoded play names
playbook_terms_utf16 = [
    b'M\x00E\x00M\x00 \x00I\x00S\x00O\x00',
    b'F\x00I\x00S\x00T\x00',
    b'Q\x00U\x00I\x00C\x00K\x00',
    b'C\x00H\x00E\x00S\x00T\x00',
    b'I\x00S\x00O\x00L\x00A\x00T\x00I\x00O\x00N\x00',
    b'P\x00I\x00C\x00K\x00',
    b'P\x00L\x00A\x00Y\x00',
]

for term in playbook_terms_utf16:
    pos = search_start
    found = 0
    while pos < search_end and found < 3:
        chunk_size = min(0x20000, search_end - pos)
        data = mem_read(hproc, pos, chunk_size)
        if data is None:
            pos += chunk_size
            continue
        idx = data.find(term)
        while idx != -1 and found < 3:
            abs_pos = pos + idx
            context_start = max(0, idx - 20)
            context_end = min(chunk_size, idx + len(term) + 40)
            context = data[context_start:context_end]
            ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
            print('  Found at 0x{:X}: ...{}...'.format(abs_pos, ascii_ctx))
            found += 1
            idx = data.find(term, idx + 1)
        pos += chunk_size

CloseHandle(hproc)
print('\nDone.')
