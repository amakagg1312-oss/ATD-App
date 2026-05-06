#!/usr/bin/env python3
"""
NBA 2K26 Team Dumper
--------------------
Connects to running NBA2K26.exe, finds a specific team by abbreviation,
and dumps its full team struct (5672 bytes) to a binary file.

Usage:
    python team_dumper.py --team MIL
    python team_dumper.py --team LAL --output bucks_dump.bin
    python team_dumper.py --list
"""

import sys
import os
import json
import struct
import ctypes
import argparse
from ctypes import wintypes
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Win32 API Setup (same as live_import.py)
# ─────────────────────────────────────────────────────────────────────────────

if sys.platform != "win32":
    print("This tool only runs on Windows.")
    sys.exit(1)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_ALL_ACCESS       = 0x1F0FFF
TH32CS_SNAPPROCESS       = 0x00000002
TH32CS_SNAPMODULE        = 0x00000008
TH32CS_SNAPMODULE32      = 0x00000010
INVALID_HANDLE_VALUE     = ctypes.c_void_p(-1).value

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize",              wintypes.DWORD),
        ("cntUsage",            wintypes.DWORD),
        ("th32ProcessID",       wintypes.DWORD),
        ("th32DefaultHeapID",   ctypes.c_size_t),
        ("th32ModuleID",        wintypes.DWORD),
        ("cntThreads",          wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase",      wintypes.LONG),
        ("dwFlags",             wintypes.DWORD),
        ("szExeFile",           ctypes.c_wchar * 260),
    ]

class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize",        wintypes.DWORD),
        ("th32ModuleID",  wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage",  wintypes.DWORD),
        ("ProccntUsage",  wintypes.DWORD),
        ("modBaseAddr",   ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize",   wintypes.DWORD),
        ("hModule",       wintypes.HMODULE),
        ("szModule",      ctypes.c_wchar * 256),
        ("szExePath",     ctypes.c_wchar * 260),
    ]

OpenProcess               = kernel32.OpenProcess
OpenProcess.argtypes      = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype       = wintypes.HANDLE

CloseHandle               = kernel32.CloseHandle
CloseHandle.argtypes      = [wintypes.HANDLE]
CloseHandle.restype       = wintypes.BOOL

ReadProcessMemory             = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes    = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
]
ReadProcessMemory.restype     = wintypes.BOOL

CreateToolhelp32Snapshot      = kernel32.CreateToolhelp32Snapshot
CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
CreateToolhelp32Snapshot.restype  = wintypes.HANDLE

Process32FirstW               = kernel32.Process32FirstW
Process32FirstW.argtypes      = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
Process32FirstW.restype       = wintypes.BOOL

Process32NextW                = kernel32.Process32NextW
Process32NextW.argtypes       = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
Process32NextW.restype        = wintypes.BOOL

Module32FirstW                = kernel32.Module32FirstW
Module32FirstW.argtypes       = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
Module32FirstW.restype        = wintypes.BOOL

Module32NextW                 = kernel32.Module32NextW
Module32NextW.argtypes        = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
Module32NextW.restype         = wintypes.BOOL

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

GAME_EXE      = "NBA2K26.exe"
TEAM_STRIDE   = 5672   # bytes per team record
MAX_TEAMS     = 40     # max teams to scan

# ─────────────────────────────────────────────────────────────────────────────
# Process / memory helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_pid(exe_name):
    target = exe_name.lower()
    snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE_VALUE:
        return None
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    pid = None
    try:
        if Process32FirstW(snap, ctypes.byref(entry)):
            while True:
                if entry.szExeFile.lower() == target:
                    pid = entry.th32ProcessID
                    break
                if not Process32NextW(snap, ctypes.byref(entry)):
                    break
    finally:
        CloseHandle(snap)
    return pid

def get_module_base(pid, module_name):
    target = module_name.lower()
    flags = TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32
    snap = CreateToolhelp32Snapshot(flags, pid)
    if snap == INVALID_HANDLE_VALUE:
        return None
    me32 = MODULEENTRY32W()
    me32.dwSize = ctypes.sizeof(MODULEENTRY32W)
    base = None
    try:
        if Module32FirstW(snap, ctypes.byref(me32)):
            while True:
                if me32.szModule.lower() == target:
                    base = ctypes.cast(me32.modBaseAddr, ctypes.c_void_p).value
                    break
                if not Module32NextW(snap, ctypes.byref(me32)):
                    break
    finally:
        CloseHandle(snap)
    return base

def mem_read(hproc, addr, n):
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t()
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        raise RuntimeError(f"ReadProcessMemory failed at 0x{addr:016X} ({n} bytes)")
    return bytes(buf)

def read_uint64(hproc, addr):
    return struct.unpack("<Q", mem_read(hproc, addr, 8))[0]

def read_wstring(hproc, addr, max_chars):
    raw = mem_read(hproc, addr, max_chars * 2)
    s = raw.decode("utf-16le", errors="ignore")
    end = s.find("\x00")
    return s[:end] if end != -1 else s

def read_ansi_string(hproc, addr, max_chars):
    raw = mem_read(hproc, addr, max_chars)
    end = raw.find(b"\x00")
    return raw[:end].decode("ascii", errors="ignore") if end != -1 else raw.decode("ascii", errors="ignore")

# ─────────────────────────────────────────────────────────────────────────────
# Offset JSON loader
# ─────────────────────────────────────────────────────────────────────────────

def find_offset_json():
    candidates = [
        Path(__file__).resolve().parent.parent / "nba2k26_generator" / "2k26_offsets.json",
        Path(__file__).resolve().parent / "2k26_offsets.json",
        Path("2k26_offsets.json"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

def load_offsets(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    game_info = data.get("game_info", {})
    team_stride = int(game_info.get("teamSize", TEAM_STRIDE))
    
    base_pointers = data.get("base_pointers", {})
    team_ptr = base_pointers.get("Team", {})
    team_rva = int(team_ptr.get("address", 0))
    
    return team_rva, team_stride

# ─────────────────────────────────────────────────────────────────────────────
# Team scanning
# ─────────────────────────────────────────────────────────────────────────────

def scan_teams(hproc, table_base, stride, max_scan=MAX_TEAMS):
    """
    Scan team records and return list of {index, name, abbr, addr}.
    Team name is likely at offset 738 (Team Vitals -> Team Name, len=24 WString).
    """
    teams = []
    TEAM_NAME_OFF = 738  # From offsets.json: Team Name at addr 738
    TEAM_NAME_LEN = 24
    
    for i in range(max_scan):
        t_addr = table_base + i * stride
        try:
            name = read_wstring(hproc, t_addr + TEAM_NAME_OFF, TEAM_NAME_LEN).strip()
        except Exception:
            continue
        
        if not name:
            continue
        
        # Try to find abbreviation (might be at a different offset)
        # Common offsets: 0x0-0x10 for short codes
        abbr = ""
        for off in [0, 4, 8, 12, 16]:
            try:
                candidate = read_ansi_string(hproc, t_addr + off, 4)
                if candidate.isalpha() and len(candidate) == 3:
                    abbr = candidate
                    break
            except Exception:
                pass
        
        teams.append({
            "index": i,
            "name": name,
            "abbr": abbr,
            "addr": t_addr,
        })
    
    return teams

def find_team(teams, search_term):
    """Find team by name or abbreviation."""
    target = search_term.upper().strip()
    
    # 1. Exact abbreviation match
    for t in teams:
        if t["abbr"].upper() == target:
            return t
    
    # 2. Name contains search term
    for t in teams:
        if target in t["name"].upper():
            return t
    
    # 3. Partial match
    for t in teams:
        if target in t["name"].upper().replace(" ", "") or target in t["abbr"].upper().replace(" ", ""):
            return t
    
    return None

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NBA 2K26 Team Dumper")
    parser.add_argument("--team", default=None, help="Team abbreviation or name (e.g., MIL, Lakers)")
    parser.add_argument("--output", default=None, help="Output file path (default: team_<abbr>_<timestamp>.bin)")
    parser.add_argument("--list", action="store_true", help="List all teams found in memory")
    parser.add_argument("--offsets", default=None, help="Path to 2k26_offsets.json")
    args = parser.parse_args()
    
    # Load offsets
    offset_path = Path(args.offsets) if args.offsets else find_offset_json()
    if not offset_path or not offset_path.exists():
        print(f"ERROR: Could not locate 2k26_offsets.json")
        sys.exit(1)
    
    team_rva, team_stride = load_offsets(offset_path)
    print(f"Loaded offsets: team_rva=0x{team_rva:X}, team_stride={team_stride}")
    
    # Attach to game
    pid = find_pid(GAME_EXE)
    if pid is None:
        print(f"ERROR: {GAME_EXE} is not running. Start the game first.")
        sys.exit(1)
    print(f"Found {GAME_EXE} PID: {pid}")
    
    module_base = get_module_base(pid, GAME_EXE)
    if module_base is None:
        print("ERROR: Could not resolve game module base address.")
        sys.exit(1)
    print(f"Module base: 0x{module_base:X}")
    
    hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hproc:
        err = ctypes.get_last_error()
        print(f"ERROR: OpenProcess failed (error {err}). Run as Administrator.")
        sys.exit(1)
    
    try:
        # Resolve team table base
        ptr_addr = module_base + team_rva
        try:
            table_base = read_uint64(hproc, ptr_addr)
        except Exception as exc:
            print(f"ERROR: Could not read team pointer at 0x{ptr_addr:X}: {exc}")
            sys.exit(1)
        
        if table_base == 0:
            print("ERROR: Team table pointer is NULL. Navigate to a roster edit screen.")
            sys.exit(1)
        
        print(f"Team table base: 0x{table_base:X}")
        
        # Scan teams
        teams = scan_teams(hproc, table_base, team_stride)
        if not teams:
            print("ERROR: No teams found. Make sure you're in a roster edit screen.")
            sys.exit(1)
        
        print(f"\nFound {len(teams)} teams:")
        for t in teams:
            print(f"  [{t['index']:2d}] {t['abbr']:4s} {t['name']} (addr=0x{t['addr']:X})")
        
        if args.list:
            return
        
        if not args.team:
            print("\nERROR: Specify --team <abbr or name>")
            sys.exit(1)
        
        # Find target team
        team = find_team(teams, args.team)
        if team is None:
            print(f"\nERROR: Team '{args.team}' not found")
            sys.exit(1)
        
        print(f"\nFound team: {team['abbr']} {team['name']}")
        print(f"  Address: 0x{team['addr']:X}")
        print(f"  Index: {team['index']}")
        
        # Dump team struct
        team_data = mem_read(hproc, team["addr"], team_stride)
        
        # Generate output filename
        if args.output:
            output_path = Path(args.output)
        else:
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(__file__).resolve().parent / f"team_{team['abbr']}_{ts}.bin"
        
        output_path.write_bytes(team_data)
        print(f"\nDumped {len(team_data)} bytes to: {output_path}")
        print(f"  File size: {len(team_data)} bytes (expected: {team_stride})")
        
        # Show first 64 bytes in hex for verification
        print(f"\nFirst 64 bytes (hex):")
        for i in range(0, 64, 16):
            hex_part = ' '.join(f'{b:02X}' for b in team_data[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in team_data[i:i+16])
            print(f"  {i:04X}: {hex_part:<48} {ascii_part}")
        
    finally:
        CloseHandle(hproc)

if __name__ == "__main__":
    main()
