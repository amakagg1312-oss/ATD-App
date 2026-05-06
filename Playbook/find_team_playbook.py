"""Dump team structure to find playbook references."""

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import struct
import sys

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.OpenProcess.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_int]
kernel.ReadProcessMemory.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, 
    c_size_t, ctypes.POINTER(c_size_t)
]

def read_memory(h, addr, size):
    buf = create_string_buffer(size)
    if kernel.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p.pid
    return None

def safe_print(s):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', errors='replace').decode('ascii'))

def main():
    pid = find_process()
    if not pid:
        safe_print("NBA2K26.exe not running!")
        return
    
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        safe_print("Failed to open process!")
        return
    
    # Find team table by searching for "76ers"
    team_name_bytes = b'7\x006\x00e\x00r\x00s\x00\x00\x00'
    
    safe_print("Searching for team table...")
    
    # Search in a limited range first
    for base in range(0x10000000, 0x100000000, 0x10000):
        buf = read_memory(h, base, 0x10000)
        if buf:
            idx = buf.find(team_name_bytes)
            if idx >= 0:
                team_addr = base + idx
                # Team name is at offset 0x2E2 (738) from team base
                team_base = team_addr - 0x2E2
                safe_print(f"Found 76ers at 0x{team_addr:X}")
                safe_print(f"Team base: 0x{team_base:X}")
                
                # Dump team structure
                team_stride = 5672
                raw = read_memory(h, team_base, 256)
                if raw:
                    safe_print(f"\nTeam structure (first 256 bytes):")
                    for off in range(0, 256, 16):
                        chunk = raw[off:off+16]
                        hex_str = ' '.join(f'{b:02X}' for b in chunk)
                        if len(chunk) >= 8:
                            qword = struct.unpack('<Q', chunk[:8])[0]
                            marker = " <-- PTR" if 0x10000000 < qword < 0x300000000 else ""
                            safe_print(f"  [{off:03X}] {hex_str}{marker}")
                
                break
    
    # Also search for "Playbook" or "playbook" string
    safe_print(f"\nSearching for 'Playbook' string...")
    pb_bytes = b'P\x00l\x00a\x00y\x00b\x00o\x00o\x00k\x00'
    
    for base in range(0x10000000, 0x100000000, 0x10000):
        buf = read_memory(h, base, 0x10000)
        if buf:
            idx = buf.find(pb_bytes)
            if idx >= 0:
                safe_print(f"Found 'Playbook' at 0x{base + idx:X}")
                data = read_memory(h, base + idx - 50, 200)
                if data:
                    for off in range(0, min(len(data), 150), 16):
                        chunk = data[off:off+16]
                        hex_str = ' '.join(f'{b:02X}' for b in chunk)
                        try:
                            text = chunk.decode('utf-16-le', errors='ignore')
                            printable = ''.join(c if c.isprintable() else '.' for c in text)
                            safe_print(f"    [{off:03X}] {hex_str:<48} {printable}")
                        except:
                            safe_print(f"    [{off:03X}] {hex_str}")
                break

if __name__ == "__main__":
    main()
