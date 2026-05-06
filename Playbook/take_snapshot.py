import struct
import ctypes
from ctypes import wintypes
import os

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

# Dump 50MB region around the team struct (25MB before, 25MB after)
dump_size = 50 * 1024 * 1024  # 50MB
dump_start = table_base - 25 * 1024 * 1024
dump_end = table_base + 25 * 1024 * 1024

print('Dumping 50MB from 0x{:X} to 0x{:X}...'.format(dump_start, dump_end))

# Read in chunks and save to file
output_path = 'D:\\project\\Playbook\\snapshot2.bin'
with open(output_path, 'wb') as f:
    pos = dump_start
    total_read = 0
    while pos < dump_end:
        chunk_size = min(0x100000, dump_end - pos)  # 1MB chunks
        data = mem_read(hproc, pos, chunk_size)
        if data:
            f.write(data)
            total_read += len(data)
        pos += chunk_size
        if total_read % (5 * 1024 * 1024) == 0:
            print('  Read {}MB...'.format(total_read // (1024 * 1024)))

print('Snapshot 1 saved to: {}'.format(output_path))
print('Total bytes read: {} ({:.1f}MB)'.format(total_read, total_read / (1024 * 1024)))

CloseHandle(hproc)
