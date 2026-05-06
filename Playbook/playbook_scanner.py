#!/usr/bin/env python3
"""
NBA 2K26 Playbook Scanner
--------------------------
Replicates Cheat Engine value scanning against the live game process.
Used to find the exact memory address where the playbook assignment is stored.

TWO WORKFLOWS — pick whichever fits:

  WORKFLOW A  (fast — if playbook is in the team struct)
  ────────────────────────────────────────────────────────────────
  1. Game running, in Edit Roster screen with a team open.
  2. python playbook_scanner.py dump-team --team PHI --out before.bin
  3. In-game: change that team's playbook to something different.
  4. python playbook_scanner.py dump-team --team PHI --out after.bin
  5. python playbook_scanner.py diff-struct before.bin after.bin
     → Prints the exact byte offsets that changed.

  WORKFLOW B  (thorough — if playbook is stored outside the team struct)
  ────────────────────────────────────────────────────────────────
  1. Game running, note the team's current playbook name.
  2. python playbook_scanner.py snapshot --out snap1.bin
  3. In-game: change that team's playbook.
  4. python playbook_scanner.py snapshot --out snap2.bin
  5. python playbook_scanner.py diff-snap snap1.bin snap2.bin
     → Reports every address that changed, with team-struct context.

  WORKFLOW C  (CE-style value scan — when you know the playbook's numeric ID)
  ────────────────────────────────────────────────────────────────
  1. python playbook_scanner.py search --value 14 --out cands.json
  2. In-game: change the playbook.
  3. python playbook_scanner.py narrow --candidates cands.json --value <new_id>
     → Repeat narrow + change until only a handful of addresses remain.
  4. python playbook_scanner.py analyze --addr 0x2A818ABC
"""

import sys, os, struct, ctypes, json, argparse, time
from ctypes import wintypes
from pathlib import Path

# Force UTF-8 output so box-drawing characters don't crash on Windows cp1252 consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# Win32 API
# ─────────────────────────────────────────────────────────────────────────────

if sys.platform != "win32":
    print("ERROR: This tool only runs on Windows.")
    sys.exit(1)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_ALL_ACCESS    = 0x1F0FFF
TH32CS_SNAPPROCESS    = 0x00000002
TH32CS_SNAPMODULE     = 0x00000008
TH32CS_SNAPMODULE32   = 0x00000010
INVALID_HANDLE_VALUE  = ctypes.c_void_p(-1).value

MEM_COMMIT            = 0x1000
MEM_PRIVATE           = 0x20000
MEM_MAPPED            = 0x40000
PAGE_NOACCESS         = 0x01
PAGE_GUARD            = 0x100

# Pages we want to scan: readable + writable (game data lives here)
WRITABLE_MASKS = {0x04, 0x08, 0x20, 0x40}  # RW, WC, RWX, EWC


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


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress",       ctypes.c_void_p),
        ("AllocationBase",    ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize",        ctypes.c_size_t),
        ("State",             wintypes.DWORD),
        ("Protect",           wintypes.DWORD),
        ("Type",              wintypes.DWORD),
    ]


OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype  = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype  = wintypes.BOOL

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
]
ReadProcessMemory.restype = wintypes.BOOL

VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t,
]
VirtualQueryEx.restype = ctypes.c_size_t

CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
CreateToolhelp32Snapshot.restype  = wintypes.HANDLE

Process32FirstW = kernel32.Process32FirstW
Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
Process32FirstW.restype  = wintypes.BOOL

Process32NextW = kernel32.Process32NextW
Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
Process32NextW.restype  = wintypes.BOOL

Module32FirstW = kernel32.Module32FirstW
Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
Module32FirstW.restype  = wintypes.BOOL

Module32NextW = kernel32.Module32NextW
Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
Module32NextW.restype  = wintypes.BOOL

# ─────────────────────────────────────────────────────────────────────────────
# Known constants (from nba2k26_generator/2k26_offsets.json)
# ─────────────────────────────────────────────────────────────────────────────

GAME_EXE       = "NBA2K26.exe"
TEAM_RVA       = 0x7E1E318   # RVA of pointer to team table (post-Jan 27 patch)
PLAYER_RVA     = 0x7E0DCC8   # RVA of pointer to player table
TEAM_STRIDE    = 5672        # bytes per team struct
MAX_TEAMS      = 40
TEAM_NAME_OFF  = 738         # WString offset for team name inside struct

# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
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
    if not ok or read_count.value == 0:
        return None
    return bytes(buf[:read_count.value])


def read_uint64(hproc, addr):
    d = mem_read(hproc, addr, 8)
    return struct.unpack("<Q", d)[0] if d and len(d) == 8 else None


def read_wstring(hproc, addr, max_chars=24):
    d = mem_read(hproc, addr, max_chars * 2)
    if not d:
        return ""
    s = d.decode("utf-16le", errors="ignore")
    end = s.find("\x00")
    return s[:end] if end != -1 else s


def attach(require_admin_msg=True):
    """Find NBA2K26.exe, return (hproc, module_base, pid) or print error and exit."""
    pid = find_pid(GAME_EXE)
    if not pid:
        print(f"ERROR: {GAME_EXE} is not running. Start the game and navigate to Edit Roster.")
        sys.exit(1)

    module_base = get_module_base(pid, GAME_EXE)
    if not module_base:
        print("ERROR: Could not get module base — run as Administrator.")
        sys.exit(1)

    hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hproc:
        err = ctypes.get_last_error()
        print(f"ERROR: OpenProcess failed (error {err}). Run as Administrator.")
        sys.exit(1)

    print(f"Attached to {GAME_EXE}  PID={pid}  module_base=0x{module_base:X}")
    return hproc, module_base, pid


def resolve_team_table(hproc, module_base):
    ptr_addr = module_base + TEAM_RVA
    table_base = read_uint64(hproc, ptr_addr)
    if not table_base or table_base == 0:
        print(f"ERROR: Team table pointer at 0x{ptr_addr:X} is NULL.")
        print("Navigate to Play Now → Edit Roster → pick a team first.")
        sys.exit(1)
    return table_base


def scan_teams(hproc, table_base):
    teams = []
    for i in range(MAX_TEAMS):
        t_addr = table_base + i * TEAM_STRIDE
        try:
            name = read_wstring(hproc, t_addr + TEAM_NAME_OFF, 24).strip()
        except Exception:
            name = ""
        if name:
            teams.append({"index": i, "name": name, "addr": t_addr})
    return teams


_ABBR_TO_NAME = {
    "ATL": "Hawks",   "BOS": "Celtics",  "BRK": "Nets",    "CHA": "Hornets",
    "CHI": "Bulls",   "CLE": "Cavaliers","DAL": "Mavericks","DEN": "Nuggets",
    "DET": "Pistons", "GSW": "Warriors", "HOU": "Rockets",  "IND": "Pacers",
    "LAC": "Clippers","LAL": "Lakers",   "MEM": "Grizzlies","MIA": "Heat",
    "MIL": "Bucks",   "MIN": "Timberwolves","NOP":"Pelicans","NYK":"Knicks",
    "OKC": "Thunder", "ORL": "Magic",    "PHI": "76ers",    "PHX": "Suns",
    "POR": "Trail Blazers","SAC":"Kings","SAS":"Spurs",     "TOR":"Raptors",
    "UTA": "Jazz",    "WAS": "Wizards",  "NJN": "Nets",     "NOH": "Pelicans",
    "SEA": "Thunder", "VAN": "Grizzlies","BUF": "Braves",
}

def find_team_by_name(teams, search):
    s = search.upper().strip()
    # Resolve abbreviation first
    resolved = _ABBR_TO_NAME.get(s, s)
    for t in teams:
        if resolved.upper() in t["name"].upper():
            return t
    # Fall back to direct partial match
    for t in teams:
        if s in t["name"].upper():
            return t
    return None

# ─────────────────────────────────────────────────────────────────────────────
# Memory region enumeration
# ─────────────────────────────────────────────────────────────────────────────

def _is_scannable(mbi):
    """Return True if this page should be included in a heap scan."""
    if mbi.State != MEM_COMMIT:
        return False
    if mbi.Protect & PAGE_NOACCESS:
        return False
    if mbi.Protect & PAGE_GUARD:
        return False
    # Must have write access (read-only image sections can't hold mutable game data)
    prot_base = mbi.Protect & 0xFF
    if prot_base not in WRITABLE_MASKS:
        return False
    return True


def enumerate_regions(hproc, min_addr=0x10000, max_addr=0x7FFFFFFFFFFF):
    """Yield (base_address, size) for all scannable committed writable pages."""
    mbi = MEMORY_BASIC_INFORMATION()
    addr = min_addr
    while addr < max_addr:
        ret = VirtualQueryEx(hproc, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi))
        if ret == 0:
            break
        if _is_scannable(mbi):
            yield mbi.BaseAddress, mbi.RegionSize
        next_addr = (mbi.BaseAddress or 0) + (mbi.RegionSize or 0x1000)
        if next_addr <= addr:
            break
        addr = next_addr

# ─────────────────────────────────────────────────────────────────────────────
# Snapshot format
# ─────────────────────────────────────────────────────────────────────────────
# File format (binary):
#   4 bytes: magic "2KSN"
#   8 bytes: timestamp (unix float64)
#   For each region:
#     8 bytes: base_address (uint64)
#     4 bytes: data_length (uint32)
#     N bytes: data

SNAP_MAGIC = b"2KSN"
MAX_REGION_SIZE = 64 * 1024 * 1024  # skip regions > 64 MB (huge allocations, not team data)


def take_snapshot(hproc, out_path, quiet=False):
    """Scan all writable heap pages, write to out_path."""
    out_path = Path(out_path)
    total_bytes = 0
    region_count = 0

    with open(out_path, "wb") as f:
        f.write(SNAP_MAGIC)
        f.write(struct.pack("<d", time.time()))

        for base, size in enumerate_regions(hproc):
            if size > MAX_REGION_SIZE:
                continue
            data = mem_read(hproc, base, size)
            if not data:
                continue
            f.write(struct.pack("<QI", base, len(data)))
            f.write(data)
            total_bytes += len(data)
            region_count += 1
            if not quiet and region_count % 100 == 0:
                print(f"  {region_count} regions, {total_bytes // (1024*1024)} MB read...", end="\r")

    if not quiet:
        print(f"\nSnapshot saved: {out_path}  ({region_count} regions, {total_bytes//(1024*1024)} MB)")
    return out_path


def load_snapshot(path):
    """Load snapshot file, return list of (base_address, data_bytes)."""
    path = Path(path)
    regions = []
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != SNAP_MAGIC:
            raise ValueError(f"Not a valid snapshot file: {path}")
        ts = struct.unpack("<d", f.read(8))[0]
        while True:
            hdr = f.read(12)
            if len(hdr) < 12:
                break
            base, length = struct.unpack("<QI", hdr)
            data = f.read(length)
            if len(data) < length:
                break
            regions.append((base, data))
    return regions, ts

# ─────────────────────────────────────────────────────────────────────────────
# Team struct context lookup
# ─────────────────────────────────────────────────────────────────────────────

_team_table_cache = None  # (table_base, teams) — cached after first lookup


def _get_team_context(hproc, module_base, addr):
    """
    Given a memory address, return a string describing its position relative
    to the known team table, or None if it's unrelated.
    """
    global _team_table_cache
    if _team_table_cache is None:
        try:
            table_base = resolve_team_table(hproc, module_base)
            teams = scan_teams(hproc, table_base)
            _team_table_cache = (table_base, teams)
        except SystemExit:
            _team_table_cache = (0, [])

    table_base, teams = _team_table_cache
    if not table_base:
        return None

    # Check if addr falls within any team struct
    for t in teams:
        if t["addr"] <= addr < t["addr"] + TEAM_STRIDE:
            offset = addr - t["addr"]
            return f"team[{t['index']}] '{t['name']}' +0x{offset:X} ({offset})"

    # Check proximity to table base
    span = len(teams) * TEAM_STRIDE if teams else 0
    if table_base <= addr < table_base + span:
        rel = addr - table_base
        team_idx = rel // TEAM_STRIDE
        within = rel % TEAM_STRIDE
        return f"near team[{team_idx}] +0x{within:X}"

    return None

# ─────────────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────────────

def cmd_dump_team(args):
    """Dump a team's 5672-byte struct to a binary file."""
    hproc, module_base, _ = attach()
    try:
        table_base = resolve_team_table(hproc, module_base)
        teams = scan_teams(hproc, table_base)
        if not teams:
            print("ERROR: No teams found. Are you in Edit Roster mode?")
            sys.exit(1)

        print(f"Found {len(teams)} teams:")
        for t in teams:
            print(f"  [{t['index']:2d}] {t['name']}  0x{t['addr']:X}")

        if not args.team:
            print("\nSpecify --team <name or partial name>")
            sys.exit(0)

        team = find_team_by_name(teams, args.team)
        if not team:
            print(f"ERROR: Team '{args.team}' not found.")
            sys.exit(1)

        data = mem_read(hproc, team["addr"], TEAM_STRIDE)
        if not data:
            print("ERROR: Could not read team struct.")
            sys.exit(1)

        out = Path(args.out) if args.out else Path(f"team_{args.team.replace(' ','_')}.bin")
        out.write_bytes(data)
        print(f"\nDumped '{team['name']}' ({TEAM_STRIDE} bytes) → {out}")

        # Show non-zero regions as a quick preview
        print("\nNon-zero data regions in struct (potential fields):")
        i = 0
        while i < len(data):
            if data[i] != 0:
                start = i
                while i < len(data) and (data[i] != 0 or i < start + 4):
                    i += 1
                chunk = data[start:i]
                if len(chunk) >= 2:
                    hex_str = " ".join(f"{b:02X}" for b in chunk[:32])
                    print(f"  +0x{start:04X} ({start:4d}): {hex_str}")
            else:
                i += 1
    finally:
        CloseHandle(hproc)


def cmd_diff_struct(args):
    """Diff two team struct .bin files, show changed offsets."""
    data1 = Path(args.file1).read_bytes()
    data2 = Path(args.file2).read_bytes()

    if len(data1) != len(data2):
        print(f"WARNING: Files differ in size ({len(data1)} vs {len(data2)})")

    min_len = min(len(data1), len(data2))
    diffs = [(i, data1[i], data2[i]) for i in range(min_len) if data1[i] != data2[i]]

    if not diffs:
        print("Files are IDENTICAL — no bytes changed.")
        print("Make sure you dumped BEFORE and AFTER changing the playbook in-game.")
        return

    print(f"{len(diffs)} byte(s) differ between the two dumps:\n")

    # Group into contiguous blocks
    blocks = []
    if diffs:
        block = [diffs[0]]
        for d in diffs[1:]:
            if d[0] == block[-1][0] + 1:
                block.append(d)
            else:
                blocks.append(block)
                block = [d]
        blocks.append(block)

    for blk in blocks:
        start_off = blk[0][0]
        end_off   = blk[-1][0]
        print(f"  Offset +0x{start_off:04X} ({start_off}) — +0x{end_off:04X} ({end_off})  [{len(blk)} byte(s)]")

        # Interpret as various types for the first 4 bytes
        vals_before = bytes(b[1] for b in blk[:8])
        vals_after  = bytes(b[2] for b in blk[:8])

        if len(vals_before) >= 1:
            print(f"    uint8  : {vals_before[0]} → {vals_after[0]}")
        if len(vals_before) >= 2:
            print(f"    uint16 : {struct.unpack('<H', vals_before[:2].ljust(2,b'\\x00'))[0]} → {struct.unpack('<H', vals_after[:2].ljust(2,b'\\x00'))[0]}")
        if len(vals_before) >= 4:
            b4 = vals_before[:4].ljust(4, b"\x00")
            a4 = vals_after[:4].ljust(4, b"\x00")
            print(f"    uint32 : {struct.unpack('<I', b4)[0]} → {struct.unpack('<I', a4)[0]}")
            print(f"    int32  : {struct.unpack('<i', b4)[0]} → {struct.unpack('<i', a4)[0]}")
        print()

    # Summarize for the user
    print("─" * 60)
    print("KEY OFFSETS (add these to 2k26_offsets.json):")
    for blk in blocks:
        off = blk[0][0]
        before_bytes = bytes(b[1] for b in blk[:4]).ljust(4, b"\x00")
        after_bytes  = bytes(b[2] for b in blk[:4]).ljust(4, b"\x00")
        before_val   = struct.unpack("<I", before_bytes)[0]
        after_val    = struct.unpack("<I", after_bytes)[0]
        print(f"  team_struct + 0x{off:04X}  (decimal: {off})  {before_val} → {after_val}")


def cmd_snapshot(args):
    """Take a full memory snapshot of all writable pages."""
    hproc, module_base, _ = attach()
    try:
        out = Path(args.out) if args.out else Path("snapshot.bin")
        print(f"Scanning all writable memory pages...")
        take_snapshot(hproc, out)
    finally:
        CloseHandle(hproc)


def cmd_diff_snap(args):
    """Diff two full memory snapshots, report changed addresses."""
    print(f"Loading {args.snap1}...")
    regions1, ts1 = load_snapshot(args.snap1)
    print(f"  {len(regions1)} regions  (taken {time.strftime('%H:%M:%S', time.localtime(ts1))})")

    print(f"Loading {args.snap2}...")
    regions2, ts2 = load_snapshot(args.snap2)
    print(f"  {len(regions2)} regions  (taken {time.strftime('%H:%M:%S', time.localtime(ts2))})\n")

    # Build lookup: base_addr → data
    map2 = {base: data for base, data in regions2}

    # Attach to get team context (optional — may fail if game not running)
    hproc, module_base = None, None
    try:
        pid = find_pid(GAME_EXE)
        if pid:
            module_base = get_module_base(pid, GAME_EXE)
            hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    except Exception:
        pass

    changed_addrs = []
    total_changed_bytes = 0

    for base, data1 in regions1:
        if base not in map2:
            continue
        data2 = map2[base]
        min_len = min(len(data1), len(data2))
        i = 0
        while i < min_len - 3:
            if data1[i:i+4] != data2[i:i+4]:
                v1 = struct.unpack("<I", data1[i:i+4])[0]
                v2 = struct.unpack("<I", data2[i:i+4])[0]
                changed_addrs.append((base + i, v1, v2))
                total_changed_bytes += 4
                i += 4  # skip to next aligned uint32
            else:
                i += 4

    print(f"Total changed uint32 values: {len(changed_addrs)}")
    if not changed_addrs:
        print("No changes detected. Did you change the playbook between snapshots?")
        return

    # Sort and show, with team struct context
    changed_addrs.sort(key=lambda x: x[0])

    print(f"\n{'Address':<20} {'Before':>10} {'After':>10}  Context")
    print("─" * 70)
    for addr, v1, v2 in changed_addrs[:200]:  # cap at 200 lines
        ctx = ""
        if hproc and module_base:
            ctx = _get_team_context(hproc, module_base, addr) or ""
        print(f"  0x{addr:016X}  {v1:>10}  {v2:>10}  {ctx}")

    if len(changed_addrs) > 200:
        print(f"  ... and {len(changed_addrs)-200} more")

    # Highlight any that look like small playbook-ID-sized values (1–100)
    small_changes = [(a, v1, v2) for a, v1, v2 in changed_addrs if 0 < v1 <= 150 and 0 < v2 <= 150]
    if small_changes:
        print(f"\n{'─'*70}")
        print(f"SMALL VALUE CHANGES (likely playbook IDs):")
        for addr, v1, v2 in small_changes:
            ctx = ""
            if hproc and module_base:
                ctx = _get_team_context(hproc, module_base, addr) or ""
            print(f"  0x{addr:016X}  {v1} → {v2}  {ctx}")

    if hproc:
        CloseHandle(hproc)

    # Save results to JSON
    out_json = Path("diff_results.json")
    with open(out_json, "w") as f:
        json.dump({
            "snap1": str(args.snap1),
            "snap2": str(args.snap2),
            "total_changed": len(changed_addrs),
            "changes": [{"addr": hex(a), "before": v1, "after": v2} for a, v1, v2 in changed_addrs],
        }, f, indent=2)
    print(f"\nFull results saved to: {out_json}")


def cmd_search(args):
    """Scan all writable memory for a specific uint32 value (CE 'First Scan')."""
    value   = args.value
    size    = getattr(args, "size", 4)

    hproc, module_base, _ = attach()
    try:
        print(f"Scanning all writable memory for uint{size*8} value = {value}...")
        pack_fmt = {1: "<B", 2: "<H", 4: "<I"}[size]
        target   = struct.pack(pack_fmt, value)

        candidates = []
        total_bytes = 0
        region_count = 0

        for base, reg_size in enumerate_regions(hproc):
            if reg_size > MAX_REGION_SIZE:
                continue
            data = mem_read(hproc, base, reg_size)
            if not data:
                continue
            total_bytes += len(data)
            region_count += 1

            i = 0
            while i <= len(data) - size:
                if data[i:i+size] == target:
                    addr = base + i
                    ctx = _get_team_context(hproc, module_base, addr) or ""
                    candidates.append({"addr": hex(addr), "context": ctx})
                i += size

            if region_count % 200 == 0:
                print(f"  {region_count} regions scanned ({total_bytes//(1024*1024)} MB), {len(candidates)} matches...", end="\r")

        print(f"\nScan complete: {len(candidates)} address(es) hold value {value}")

        # Show candidates with context first
        with_ctx = [c for c in candidates if c["context"]]
        without_ctx = [c for c in candidates if not c["context"]]

        if with_ctx:
            print(f"\nAddresses within known structs ({len(with_ctx)}):")
            for c in with_ctx:
                print(f"  {c['addr']}  ← {c['context']}")

        print(f"\nAll other addresses: {len(without_ctx)}")
        for c in without_ctx[:50]:
            print(f"  {c['addr']}")
        if len(without_ctx) > 50:
            print(f"  ... and {len(without_ctx)-50} more (see candidates.json)")

        # Save all to JSON
        out = Path(args.out) if args.out else Path("candidates.json")
        with open(out, "w") as f:
            json.dump({"value": value, "size": size, "candidates": candidates}, f, indent=2)
        print(f"\nAll {len(candidates)} candidates saved to: {out}")
        print("Next: change the playbook in-game, then run:")
        print(f"  python playbook_scanner.py narrow --candidates {out} --value <new_playbook_id>")

    finally:
        CloseHandle(hproc)


def cmd_narrow(args):
    """Re-read previous candidates and keep only those matching a new value (CE 'Next Scan')."""
    cands_path = Path(args.candidates)
    with open(cands_path) as f:
        data = json.load(f)

    old_candidates = data["candidates"]
    old_value      = data.get("value")
    size           = data.get("size", 4)
    new_value      = args.value

    pack_fmt = {1: "<B", 2: "<H", 4: "<I"}[size]
    target   = struct.pack(pack_fmt, new_value)

    hproc, module_base, _ = attach()
    try:
        print(f"Narrowing {len(old_candidates)} candidates from {old_value} → checking for {new_value}...")
        survivors = []
        for c in old_candidates:
            addr = int(c["addr"], 16)
            d = mem_read(hproc, addr, size)
            if d and d == target:
                ctx = _get_team_context(hproc, module_base, addr) or c.get("context", "")
                survivors.append({"addr": hex(addr), "context": ctx})

        print(f"\n{len(survivors)} address(es) still hold {new_value}:")
        for s in survivors:
            ctx_str = f"  ← {s['context']}" if s["context"] else ""
            print(f"  {s['addr']}{ctx_str}")

        # Save narrowed list
        out = cands_path  # overwrite with narrowed set
        with open(out, "w") as f:
            json.dump({"value": new_value, "size": size, "candidates": survivors}, f, indent=2)
        print(f"\nNarrowed candidates saved to: {out}")
        if len(survivors) > 3:
            print("Still too many? Change the playbook again and narrow once more.")
        elif len(survivors) <= 3:
            print("Likely found it! Run:")
            for s in survivors:
                print(f"  python playbook_scanner.py analyze --addr {s['addr']}")

    finally:
        CloseHandle(hproc)


def cmd_analyze(args):
    """
    Read memory around a given address and show its context within
    the team struct + neighboring values. Helps confirm it's the playbook field.
    """
    addr = int(args.addr, 16)
    context_bytes = getattr(args, "context", 64)

    hproc, module_base, _ = attach()
    try:
        print(f"Analyzing address 0x{addr:X}...\n")

        # Team context
        ctx = _get_team_context(hproc, module_base, addr)
        if ctx:
            print(f"  Location: {ctx}")
        else:
            print(f"  Location: not within any known team struct")

        # Read surrounding bytes
        read_start = max(0, addr - context_bytes)
        read_size  = context_bytes * 2 + 4
        data = mem_read(hproc, read_start, read_size)

        if not data:
            print(f"  ERROR: Could not read memory at 0x{read_start:X}")
            return

        print(f"\n  Hex dump ({context_bytes} bytes before/after):")
        for i in range(0, len(data), 16):
            chunk      = data[i:i+16]
            row_addr   = read_start + i
            hex_part   = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            marker     = " ◄◄◄" if read_start + i <= addr < read_start + i + 16 else ""
            print(f"    0x{row_addr:X}  {hex_part:<48}  {ascii_part}{marker}")

        # Interpret uint32 values around the target
        offset_in_buf = addr - read_start
        print(f"\n  Interpretations at 0x{addr:X}:")
        for sz, fmt, name in [(1, "<B", "uint8"), (2, "<H", "uint16"), (4, "<I", "uint32"), (4, "<i", "int32")]:
            if offset_in_buf + sz <= len(data):
                val = struct.unpack(fmt, data[offset_in_buf:offset_in_buf+sz])[0]
                print(f"    {name:<8}: {val}")

        # Follow pointer if it looks like a heap pointer
        if offset_in_buf + 8 <= len(data):
            ptr = struct.unpack("<Q", data[offset_in_buf:offset_in_buf+8])[0]
            if 0x100000000 < ptr < 0x7FF000000000:
                print(f"\n  Looks like a pointer: 0x{ptr:X}")
                pointed = mem_read(hproc, ptr, 64)
                if pointed:
                    hex_p = " ".join(f"{b:02X}" for b in pointed[:32])
                    print(f"  Data at pointer: {hex_p}")

        # Check nearby uint32 values for small-integer patterns (playbook candidates)
        print(f"\n  Nearby uint32 values (possible playbook-range fields):")
        for delta in range(-32, 33, 4):
            off = offset_in_buf + delta
            if 0 <= off <= len(data) - 4:
                v = struct.unpack("<I", data[off:off+4])[0]
                if 0 < v <= 300:  # likely game-data range
                    marker = " ◄◄◄ (target offset)" if delta == 0 else ""
                    print(f"    +{delta:+4d}: {v}{marker}")

    finally:
        CloseHandle(hproc)


def cmd_dump_all_teams(args):
    """Dump the full team table region and show all non-zero fields for every team."""
    hproc, module_base, _ = attach()
    try:
        table_base = resolve_team_table(hproc, module_base)
        teams = scan_teams(hproc, table_base)
        if not teams:
            print("No teams found.")
            return

        print(f"{'Idx':<5} {'Name':<25} {'Addr':<18}  uint32 values @ key offsets")
        print("─" * 90)

        # Known interesting offsets from prior research
        probe_offsets = [0x0, 0x4, 0x8, 0x10, 0x130, 0x200, 0x2E0, 0x33C, 0x340, 0x348,
                         0x350, 0x400, 0x500, 0x600, 0x700, 0x800, 0x900, 0xA00, 0xB00]

        for t in teams:
            data = mem_read(hproc, t["addr"], TEAM_STRIDE)
            if not data:
                continue
            vals = {}
            for off in probe_offsets:
                if off + 4 <= len(data):
                    v = struct.unpack("<I", data[off:off+4])[0]
                    if v != 0:
                        vals[f"0x{off:X}"] = v

            val_str = "  ".join(f"{k}={v}" for k, v in vals.items())
            print(f"  {t['index']:<3} {t['name']:<25} 0x{t['addr']:X}  {val_str[:60]}")

    finally:
        CloseHandle(hproc)


def cmd_scan_team_pointers(args):
    """
    For a given team, follow every pointer in its struct and dump the
    pointed-to data. Playbook info might live in a sub-struct, not directly
    in the 5672-byte team struct.
    """
    hproc, module_base, _ = attach()
    try:
        table_base = resolve_team_table(hproc, module_base)
        teams = scan_teams(hproc, table_base)

        team = find_team_by_name(teams, args.team) if args.team else (teams[0] if teams else None)
        if not team:
            print(f"Team '{args.team}' not found.")
            return

        print(f"Scanning pointers in struct for: {team['name']}  (0x{team['addr']:X})")
        data = mem_read(hproc, team["addr"], TEAM_STRIDE)
        if not data:
            print("Could not read team struct.")
            return

        print(f"\nPointers found in team struct (0x{team['addr']:X}):")
        print(f"{'Struct Offset':<16} {'Pointer Target':<20} {'Bytes at Target (first 32)'}")
        print("─" * 90)

        for i in range(0, TEAM_STRIDE - 7, 8):
            val = struct.unpack_from("<Q", data, i)[0]
            if 0x100000000 < val < 0x7FF000000000:
                target_data = mem_read(hproc, val, 128)
                if target_data:
                    hex_part   = " ".join(f"{b:02X}" for b in target_data[:32])
                    ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in target_data[:16])

                    # Check if target looks like it contains small integers (play IDs?)
                    uint32s = [struct.unpack_from("<I", target_data, j)[0] for j in range(0, min(64, len(target_data))-3, 4)]
                    small   = [v for v in uint32s if 0 < v <= 500]
                    hint    = f"  ← {len(small)} small ints: {small[:6]}" if len(small) >= 3 else ""

                    print(f"  +0x{i:04X} ({i:4d})  → 0x{val:016X}  {hex_part[:48]}{hint}")

    finally:
        CloseHandle(hproc)

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="NBA 2K26 Playbook Scanner — finds the playbook memory address",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # dump-team
    p = sub.add_parser("dump-team", help="Dump a team struct to .bin file")
    p.add_argument("--team", default=None, help="Team name or partial name (e.g. PHI, Lakers)")
    p.add_argument("--out", default=None, help="Output .bin file")

    # diff-struct
    p = sub.add_parser("diff-struct", help="Diff two team struct dumps")
    p.add_argument("file1", help="Before-change dump")
    p.add_argument("file2", help="After-change dump")

    # snapshot
    p = sub.add_parser("snapshot", help="Snapshot all writable process memory")
    p.add_argument("--out", default="snapshot.bin", help="Output file")

    # diff-snap
    p = sub.add_parser("diff-snap", help="Diff two full memory snapshots")
    p.add_argument("snap1", help="Snapshot before playbook change")
    p.add_argument("snap2", help="Snapshot after playbook change")

    # search (CE-style first scan)
    p = sub.add_parser("search", help="Search all memory for a specific value")
    p.add_argument("--value", type=int, required=True, help="Value to search for")
    p.add_argument("--size", type=int, choices=[1, 2, 4], default=4, help="Value size in bytes")
    p.add_argument("--out", default="candidates.json")

    # narrow (CE-style next scan)
    p = sub.add_parser("narrow", help="Narrow CE-style candidates to a new value")
    p.add_argument("--candidates", required=True, help="candidates.json from search/narrow")
    p.add_argument("--value", type=int, required=True, help="New value to match")

    # analyze
    p = sub.add_parser("analyze", help="Inspect memory at a specific address")
    p.add_argument("--addr", required=True, help="Hex address, e.g. 0x2A818ABC")
    p.add_argument("--context", type=int, default=64, help="Bytes before/after to show")

    # dump-all-teams (probe all teams at key offsets)
    p = sub.add_parser("dump-all-teams", help="Show values at key offsets for all teams")

    # scan-pointers (follow pointers in a team struct)
    p = sub.add_parser("scan-pointers", help="Follow all pointers in a team struct")
    p.add_argument("--team", default=None, help="Team name (default: first team)")

    args = parser.parse_args()

    dispatch = {
        "dump-team":      cmd_dump_team,
        "diff-struct":    cmd_diff_struct,
        "snapshot":       cmd_snapshot,
        "diff-snap":      cmd_diff_snap,
        "search":         cmd_search,
        "narrow":         cmd_narrow,
        "analyze":        cmd_analyze,
        "dump-all-teams": cmd_dump_all_teams,
        "scan-pointers":  cmd_scan_team_pointers,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
