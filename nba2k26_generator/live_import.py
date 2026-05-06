#!/usr/bin/env python3
"""
NBA 2K26 Live Memory Import
---------------------------
Reads a team/player JSON payload from stdin (or --input file) and writes all
generated attributes and tendencies directly into the running NBA2K26.exe
process in one shot.

Usage:
    python live_import.py [--offsets PATH_TO_2k26_offsets.json] [--input team.json]

Input JSON format (from lastTeamExportPayload):
    {
      "team": "LAL",
      "season": "2024-25",
      "entries": [
        {
          "name": "LeBron James",
          "profile": {
            "attributes": {"driving_layup": 95, "three_point_shot": 76, ...},
            "tendencyGroups": {
              "finishing": [{"key": "driving_layup", "name": "Driving Layup", "value": 60}, ...],
              ...
            }
          }
        }, ...
      ]
    }

Output: JSON to stdout with per-player import results.
"""

import sys
import os
import json
import re
import ctypes
import struct
import argparse
import unicodedata
from ctypes import wintypes
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Win32 API Setup
# ─────────────────────────────────────────────────────────────────────────────

if sys.platform != "win32":
    print(json.dumps({"ok": False, "error": "This tool only runs on Windows."}))
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

WriteProcessMemory            = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes   = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
]
WriteProcessMemory.restype    = wintypes.BOOL

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
# Constants sourced from 2k26_offsets.json schema
# ─────────────────────────────────────────────────────────────────────────────

GAME_EXE           = "NBA2K26.exe"
PLAYER_STRIDE      = 1176   # bytes per player record (playerSize in game_info)
MAX_PLAYERS        = 5500   # upper scan limit
NAME_MAX_CHARS     = 20     # max chars in first/last name WString fields
OFF_LAST_NAME      = 0      # byte offset of last name WString in record
OFF_FIRST_NAME     = 40     # byte offset of first name WString in record

RATING_MIN         = 25
RATING_MAX_DISPLAY = 99
RATING_MAX_TRUE    = 110

# ─────────────────────────────────────────────────────────────────────────────
# Attribute / Tendency name normalization aliases
#
# Maps generator output key  →  normalized offset JSON name
# so we can look up the right bitfield even when names differ.
# ─────────────────────────────────────────────────────────────────────────────

def _nk(s: str) -> str:
    """Normalize a key: lowercase, replace non-alphanum with underscore."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", "_", s.lower())
    return s.strip("_")

# Attribute aliases: generator key → normalized offset name
ATTR_ALIASES: dict[str, str] = {
    # Generator uses "mid_range_shot", offset JSON has "Mid Range"
    "mid_range_shot":      "mid_range",
    # Generator uses "three_point_shot", offset JSON has "Three Point"
    "three_point_shot":    "three_point",
    # Generator uses "ball_handle", offset JSON has "Ball Control"
    "ball_handle":         "ball_control",
    # Generator uses "pass_accuracy", offset JSON has "Passing Accuracy"
    "pass_accuracy":       "passing_accuracy",
    # Generator uses "pass_iq", offset JSON has "Passing IQ"
    "pass_iq":             "passing_iq",
    # Generator uses "pass_vision", offset JSON has "Passing Vision"
    "pass_vision":         "passing_vision",
    # Generator uses "pass_perception", offset JSON has "Passing Perception"
    "pass_perception":     "passing_perception",
    # Overall Durability is a composite not a single offset field – skip it
    "overall_durability":  None,
}

# Badge name aliases: generator badge name (normalized) → normalized offset name
BADGE_ALIASES: dict[str, str] = {
    # Generator: "Ankle Assassin", offset JSON: "Ankle Breaker"
    "ankle_assassin": "ankle_breaker",
}

# Non-gameplay badges that exist in the offset JSON but should not be written
BADGE_SKIP: set[str] = {"marketability", "work_ethic"}

# Badge tier name → raw value (3-bit field: 0=None, 1=Bronze, 2=Silver, 3=Gold, 4=HOF)
BADGE_TIER_VALUES: dict[str, int] = {
    "none":         0,
    "bronze":       1,
    "silver":       2,
    "gold":         3,
    "hof":          4,
    "hall of fame": 4,
    "legend":       5,
}

# Tendency aliases: generator tendency key → normalized offset name
TEND_ALIASES: dict[str, str] = {
    # Generator "Driving Layup" (key "driving_layup") vs offset "Driving Layup Tendency"
    "driving_layup":               "driving_layup_tendency",
    # Generator "Standing Dunk" vs offset "Standing Dunk Tendency"
    "standing_dunk":               "standing_dunk_tendency",
    # Generator "Driving Dunk" vs offset "Driving Dunk Tendency"
    "driving_dunk":                "driving_dunk_tendency",
    # Generator "Putback" vs offset "Putback Dunk"
    "putback":                     "putback_dunk",
    # Generator "Alley-Oop" → normalized "alley_oop" matches offset "Alley Oop" ✓
    # Generator "Step Through Shot" vs offset "Step Through"
    "step_through_shot":           "step_through",
    # Generator "Shot" (core tendency) vs offset "Shot Tendency"
    "shot":                        "shot_tendency",
    # Generator "On-Ball Steal" → "on_ball_steal" vs offset "Steal Tendency"
    "on_ball_steal":               "steal_tendency",
    # Generator "Block Shot" vs offset "Block Tendency"
    "block_shot":                  "block_tendency",
    # Generator "Shoot From Post" vs offset "Post Shoot"
    "shoot_from_post":             "post_shoot",
    # Generator "Post Drop Step" vs offset "Post Dropstep"
    "post_drop_step":              "post_dropstep",
    # Generator "Post Step Back Shot" vs offset "Post Stepback Shot"
    "post_step_back_shot":         "post_stepback_shot",
    # Generator "Post Hop Step" stays "post_hop_step" – but offset is "Post Hop Step" ✓
    # Generator "No Setup Dribble" vs offset "No Setup Dribble Move"
    "no_setup_dribble":            "no_setup_dribble_move",
    # Dribble moves: generator uses "Driving X", offset uses "Dribble X"
    "driving_crossover":           "dribble_crossover",
    "driving_spin":                "dribble_spin",
    "driving_step_back":           "dribble_stepback",
    "driving_half_spin":           "dribble_half_spin",
    "driving_double_crossover":    "dribble_double_crossover",
    "driving_behind_the_back":     "dribble_behind_the_back",
    # Shot range names: generator uses "mid_range" suffix, offset uses shorter names
    "shot_mid_range":              "shot_mid",
    "spot_up_shot_mid_range":      "spot_up_shot_mid",
    "off_screen_shot_mid_range":   "off_screen_shot_mid",
    "contested_jumper_mid_range":  "contested_jumper_mid",
    "stepback_jumper_mid_range":   "step_back_jumper_mid",
    "drive_pull_up_mid_range":     "drive_pull_up_mid",
    # "Roll vs. Pop" → normalized "roll_vs_pop", offset "Roll Vs Pop" → "roll_vs_pop" ✓
    # ISO defenders
    "iso_vs_elite_defender":       "iso_vs_elite_defender",
    "iso_vs_good_defender":        "iso_vs_good_defender",
    "iso_vs_average_defender":     "iso_vs_average_defender",
    "iso_vs_poor_defender":        "iso_vs_poor_defender",
}

# ─────────────────────────────────────────────────────────────────────────────
# Rating conversion helpers
# ─────────────────────────────────────────────────────────────────────────────

def attr_to_raw(rating: float, length: int) -> int:
    """Convert a 25–99 attribute rating to its raw bitfield value."""
    max_raw = (1 << length) - 1
    r = max(RATING_MIN, min(RATING_MAX_DISPLAY, float(rating)))
    fraction = (r - RATING_MIN) / (RATING_MAX_TRUE - RATING_MIN)
    return max(0, min(int(round(fraction * max_raw)), max_raw))

def tend_to_raw(rating: float, length: int) -> int:
    """Convert a 0–100 tendency rating to its raw bitfield value (direct int)."""
    max_raw = (1 << length) - 1
    r = max(0.0, min(100.0, float(rating)))
    return max(0, min(int(round(r)), max_raw))

# ─────────────────────────────────────────────────────────────────────────────
# Process / memory helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_pid(exe_name: str) -> Optional[int]:
    """Return PID of a running process, or None."""
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

def get_module_base(pid: int, module_name: str) -> Optional[int]:
    """Return the base address of module_name loaded in process pid."""
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

def mem_read(hproc: wintypes.HANDLE, addr: int, n: int) -> bytes:
    """Read n bytes from addr in the target process."""
    buf = (ctypes.c_ubyte * n)()
    read_count = ctypes.c_size_t()
    ok = ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(read_count))
    if not ok or read_count.value != n:
        raise RuntimeError(f"ReadProcessMemory failed at 0x{addr:016X} ({n} bytes)")
    return bytes(buf)

def mem_write(hproc: wintypes.HANDLE, addr: int, data: bytes) -> None:
    """Write data to addr in the target process."""
    n = len(data)
    buf = (ctypes.c_ubyte * n).from_buffer_copy(data)
    written = ctypes.c_size_t()
    ok = WriteProcessMemory(hproc, ctypes.c_void_p(addr), buf, n, ctypes.byref(written))
    if not ok or written.value != n:
        raise RuntimeError(f"WriteProcessMemory failed at 0x{addr:016X} ({n} bytes)")

def read_uint64(hproc: wintypes.HANDLE, addr: int) -> int:
    return struct.unpack("<Q", mem_read(hproc, addr, 8))[0]

def read_wstring(hproc: wintypes.HANDLE, addr: int, max_chars: int) -> str:
    raw = mem_read(hproc, addr, max_chars * 2)
    s = raw.decode("utf-16le", errors="ignore")
    end = s.find("\x00")
    return s[:end] if end != -1 else s

def write_field_bits(
    hproc: wintypes.HANDLE,
    record_addr: int,
    offset: int,
    start_bit: int,
    length: int,
    raw_value: int,
) -> bool:
    """Read-modify-write a bitfield within a player record."""
    try:
        max_val = (1 << length) - 1
        raw_value = max(0, min(max_val, int(raw_value)))
        bits_needed = start_bit + length
        bytes_needed = (bits_needed + 7) // 8
        target_addr = record_addr + offset
        data = bytearray(mem_read(hproc, target_addr, bytes_needed))
        current = int.from_bytes(data, "little")
        mask = ((1 << length) - 1) << start_bit
        new_val = (current & ~mask) | ((raw_value << start_bit) & mask)
        if new_val == current:
            return True  # no change needed
        mem_write(hproc, target_addr, new_val.to_bytes(bytes_needed, "little"))
        return True
    except Exception:
        return False

# ─────────────────────────────────────────────────────────────────────────────
# Offset JSON loader
# ─────────────────────────────────────────────────────────────────────────────

def find_offset_json() -> Optional[Path]:
    """Search common locations for 2k26_offsets.json."""
    candidates = [
        Path(__file__).resolve().parent / "2k26_offsets.json",
        Path(__file__).resolve().parent.parent / "2k26_offsets.json",
        Path.home() / "Downloads" / "New folder" / "2k26_offsets.json",
        Path.home() / "Downloads" / "2k26_offsets.json",
        Path("2k26_offsets.json"),
        Path("2K26_Offsets.json"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

def load_offsets(path: Path) -> tuple[dict, dict, dict, int, int]:
    """
    Parse the offset JSON file.

    Returns:
        attr_map:  {normalized_name: {address, startBit, length}}
        tend_map:  {normalized_name: {address, startBit, length}}
        badge_map: {normalized_name: {address, startBit, length}}
        player_table_rva: RVA of the pointer to the player table base
        player_stride: bytes per player record
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    game_info = data.get("game_info", {})
    stride = int(game_info.get("playerSize", PLAYER_STRIDE))

    base_pointers = data.get("base_pointers", {})
    player_ptr = base_pointers.get("Player", {})
    player_rva = int(player_ptr.get("address", 0))

    attr_map: dict[str, dict] = {}
    tend_map: dict[str, dict] = {}
    badge_map: dict[str, dict] = {}

    for entry in data.get("offsets", []):
        name   = str(entry.get("name", ""))
        cat    = str(entry.get("category", "")).lower()
        addr   = int(entry.get("address", 0))
        length = int(entry.get("length", 8))
        sbit   = int(entry.get("startBit", 0))
        info   = {"address": addr, "startBit": sbit, "length": length}
        norm   = _nk(name)

        if cat == "attributes":
            attr_map[norm] = info
        elif cat == "tendencies":
            tend_map[norm] = info
        elif cat == "badges":
            badge_map[norm] = info

    return attr_map, tend_map, badge_map, player_rva, stride

# ─────────────────────────────────────────────────────────────────────────────
# Player scanning and name matching
# ─────────────────────────────────────────────────────────────────────────────

def _norm_name(s: str) -> str:
    """Normalize a player name for matching: strip accents, lowercase, collapse spaces."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace(".", "")
    return " ".join(s.lower().split())

# Generational suffixes that may appear in generator output but be absent in game records
_SUFFIXES = re.compile(
    r"\s+(jr\.?|sr\.?|ii|iii|iv|vi|v|viii|vii)$",
    re.IGNORECASE,
)

def _strip_suffix(name: str) -> str:
    """Remove a trailing generational suffix from a normalized name."""
    return _SUFFIXES.sub("", name).strip()

def resolve_player_table_base(
    hproc: wintypes.HANDLE,
    module_base: int,
    player_rva: int,
) -> tuple[Optional[int], Optional[str]]:
    """
    Resolve the player table base address.
    Returns (table_base, None) on success, or (None, reason_string) on failure.
    """
    ptr_addr = module_base + player_rva
    try:
        table_base = read_uint64(hproc, ptr_addr)
    except Exception as exc:
        return None, (
            f"Could not read pointer at 0x{ptr_addr:X} (module=0x{module_base:X} + rva=0x{player_rva:X}): {exc}. "
            "This usually means the offsets are stale after a game patch — update 2k26_offsets.json."
        )

    if table_base == 0:
        return None, (
            f"Player table pointer at 0x{ptr_addr:X} is NULL. "
            "The game is running but the roster isn't loaded yet — "
            "navigate into a roster edit screen (Play Now → Edit Roster → pick a team)."
        )

    # Probe the first 30 slots for at least one plausible player name.
    PROBE_LIMIT = 30
    read_errors = 0
    for i in range(PROBE_LIMIT):
        slot_addr = table_base + i * PLAYER_STRIDE
        try:
            last  = read_wstring(hproc, slot_addr + OFF_LAST_NAME,  NAME_MAX_CHARS).strip()
            first = read_wstring(hproc, slot_addr + OFF_FIRST_NAME, NAME_MAX_CHARS).strip()
        except Exception:
            read_errors += 1
            continue
        combined = (first + last).strip()
        if not combined:
            continue
        if any(ch.isalpha() or ch in "'-. " for ch in combined):
            return table_base, None

    if read_errors == PROBE_LIMIT:
        return None, (
            f"Player table pointer resolved to 0x{table_base:X} but all {PROBE_LIMIT} slot reads failed. "
            "The offset RVA is likely wrong for this game version — update 2k26_offsets.json."
        )
    return None, (
        f"Player table pointer resolved to 0x{table_base:X} but no recognisable player names "
        f"found in first {PROBE_LIMIT} slots (stride={PLAYER_STRIDE}). "
        "The game may not be in a roster edit screen, or the playerSize offset is stale."
    )

def scan_players(
    hproc: wintypes.HANDLE,
    table_base: int,
    stride: int,
    max_scan: int = MAX_PLAYERS,
) -> list[dict]:
    """
    Scan all player records and return list of {index, first, last, norm_full, addr}.
    Stops early after 20 consecutive blank records.
    """
    players: list[dict] = []
    blank_streak = 0
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'-. ")

    for i in range(max_scan):
        p_addr = table_base + i * stride
        try:
            last  = read_wstring(hproc, p_addr + OFF_LAST_NAME, NAME_MAX_CHARS).strip()
            first = read_wstring(hproc, p_addr + OFF_FIRST_NAME, NAME_MAX_CHARS).strip()
        except Exception:
            blank_streak += 1
            if blank_streak >= 20:
                break
            continue

        if not first and not last:
            blank_streak += 1
            if blank_streak >= 20:
                break
            continue

        blank_streak = 0
        # Skip records with mostly garbage characters
        full = f"{first} {last}".strip()
        if full and sum(ch not in allowed for ch in full) > len(full) * 0.4:
            continue

        players.append({
            "index": i,
            "first": first,
            "last":  last,
            "norm":  _norm_name(f"{first} {last}"),
            "addr":  p_addr,
        })

    return players

def find_player_record(
    name: str,
    player_list: list[dict],
) -> Optional[dict]:
    """
    Find the first player record whose normalized full name matches.
    Falls back to suffix-stripped and partial last-name matching.
    """
    target = _norm_name(name)

    # 1. Exact full-name match
    for p in player_list:
        if p["norm"] == target:
            return p

    # Build suffix-stripped versions for both target and game records
    target_stripped = _strip_suffix(target)

    # 2. Match with suffix stripping on both sides
    for p in player_list:
        p_stripped = _strip_suffix(p["norm"])
        if p_stripped == target_stripped:
            return p
        if p_stripped == target:
            return p
        if p["norm"] == target_stripped:
            return p

    # 3. Split "First Last" and try first+last individually (with and without suffix)
    for tgt in (target, target_stripped):
        parts = tgt.split()
        if len(parts) >= 2:
            first_t = parts[0]
            last_t  = " ".join(parts[1:])
            for p in player_list:
                p_first = _norm_name(p["first"])
                p_last  = _strip_suffix(_norm_name(p["last"]))
                if p_last == last_t and p_first == first_t:
                    return p

    # 4. Last-name only fallback (with suffix stripping on both sides)
    for tgt in (target, target_stripped):
        parts = tgt.split()
        if len(parts) >= 2:
            last_t = " ".join(parts[1:])
            for p in player_list:
                if _strip_suffix(_norm_name(p["last"])) == last_t:
                    return p

    return None

# ─────────────────────────────────────────────────────────────────────────────
# Core import logic
# ─────────────────────────────────────────────────────────────────────────────

def import_player(
    hproc: wintypes.HANDLE,
    record_addr: int,
    profile: dict,
    attr_map: dict,
    tend_map: dict,
    badge_map: dict,
) -> tuple[int, int, list[str]]:
    """
    Write all attributes, tendencies, and badges from profile into memory at record_addr.

    Returns:
        written:  number of fields successfully written
        skipped:  number of fields skipped (no matching offset)
        warnings: list of warning strings
    """
    written  = 0
    skipped  = 0
    warnings: list[str] = []

    # ── Attributes ──────────────────────────────────────────────────────────
    raw_attrs: dict[str, int] = profile.get("attributes", {})
    for gen_key, value in raw_attrs.items():
        # Resolve to offset map key
        lookup_key = ATTR_ALIASES.get(gen_key)
        if lookup_key is None and gen_key in ATTR_ALIASES:
            # Explicitly mapped to None means skip
            skipped += 1
            continue
        if lookup_key is None:
            lookup_key = gen_key

        info = attr_map.get(lookup_key)
        if info is None:
            skipped += 1
            continue

        raw = attr_to_raw(float(value), info["length"])
        ok  = write_field_bits(
            hproc, record_addr,
            info["address"], info["startBit"], info["length"], raw,
        )
        if ok:
            written += 1
        else:
            warnings.append(f"attr write failed: {gen_key}")

    # ── Tendencies ───────────────────────────────────────────────────────────
    tendency_groups: dict = profile.get("tendencyGroups", {})
    for group_items in tendency_groups.values():
        for item in (group_items or []):
            gen_key = _nk(str(item.get("key") or item.get("name") or ""))
            value   = int(item.get("value", 0))

            # Resolve to offset map key
            lookup_key = TEND_ALIASES.get(gen_key, gen_key)
            if lookup_key is None:
                skipped += 1
                continue

            info = tend_map.get(lookup_key)
            if info is None:
                skipped += 1
                continue

            raw = tend_to_raw(float(value), info["length"])
            ok  = write_field_bits(
                hproc, record_addr,
                info["address"], info["startBit"], info["length"], raw,
            )
            if ok:
                written += 1
            else:
                warnings.append(f"tend write failed: {gen_key}")

    # ── Badges ───────────────────────────────────────────────────────────────
    # Step 1: zero every known badge in the record so previous tiers are cleared
    for norm_name, info in badge_map.items():
        if norm_name in BADGE_SKIP:
            continue
        write_field_bits(
            hproc, record_addr,
            info["address"], info["startBit"], info["length"], 0,
        )

    # Step 2: write the tier values the generator assigned
    badge_groups: dict = profile.get("badgeGroups", {})
    for group_items in badge_groups.values():
        for item in (group_items or []):
            gen_key  = _nk(str(item.get("name") or item.get("key") or ""))
            tier_str = str(item.get("value") or "").strip().lower()

            if not gen_key or not tier_str or tier_str == "none":
                skipped += 1
                continue

            if gen_key in BADGE_SKIP:
                skipped += 1
                continue

            raw_tier = BADGE_TIER_VALUES.get(tier_str, 0)
            if raw_tier == 0:
                skipped += 1
                continue

            # Resolve badge name to offset map key
            lookup_key = BADGE_ALIASES.get(gen_key, gen_key)
            info = badge_map.get(lookup_key)
            if info is None:
                skipped += 1
                continue

            ok = write_field_bits(
                hproc, record_addr,
                info["address"], info["startBit"], info["length"], raw_tier,
            )
            if ok:
                written += 1
            else:
                warnings.append(f"badge write failed: {gen_key}")

    return written, skipped, warnings

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def diagnose_player_table(hproc, module_base: int, player_rva: int) -> None:
    """
    Scan the game module to find the new player table RVA after a patch.
    Uses a strict multi-record validator to avoid false positives from
    C++ runtime assertion strings embedded in the executable.
    """
    ptr_addr = module_base + player_rva
    print(f"  known ptr_addr : 0x{ptr_addr:X}  (module=0x{module_base:X} + rva=0x{player_rva:X})", file=sys.stderr)
    try:
        old_val = read_uint64(hproc, ptr_addr)
        print(f"  stale pointer  : 0x{old_val:X}", file=sys.stderr)
    except Exception:
        pass

    # ── Name validity filter ──────────────────────────────────────────────────
    # Player names: all ASCII alpha + hyphen/apostrophe/period, 2-20 chars,
    # no spaces, and not a common C++ runtime / engine debug token.
    _DEBUG_WORDS = {
        "overflow", "underflow", "detected", "value", "min", "max",
        "index", "pick", "years", "left", "over", "error", "assert",
        "failed", "invalid", "null", "true", "false", "size", "count",
        "type", "none", "zero", "one", "two", "new", "old", "set",
        "get", "add", "del", "put", "out", "end", "begin", "start",
    }
    _NAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'-.")

    def _is_name(s: str) -> bool:
        if not (2 <= len(s) <= 20):
            return False
        if not all(c in _NAME_CHARS for c in s):
            return False           # spaces, digits, etc. → not a player name
        low = s.lower()
        if low in _DEBUG_WORDS:
            return False
        if any(w in low for w in _DEBUG_WORDS):
            return False
        if not any(c.isupper() for c in s):
            return False           # player names always have at least one capital
        return True

    def _read_wstr(base: int, offset: int, max_chars: int = 22) -> str:
        try:
            raw = mem_read(hproc, base + offset, max_chars * 2)
            s = raw.decode("utf-16le", errors="ignore")
            end = s.find("\x00")
            return s[:end] if end != -1 else s
        except Exception:
            return ""

    # ── Multi-record validator ────────────────────────────────────────────────
    # Check that at least MIN_MATCH of the first CHECK_SLOTS stride-aligned
    # slots each have a plausible last-name + first-name pair.
    # Try several (last_off, first_off) guesses.
    CHECK_SLOTS = 15
    MIN_MATCH   = 4
    NAME_GUESSES = [
        (0, 40),   # original offsets
        (0, 32),
        (0, 48),
        (8, 48),
        (8, 56),
        (16, 56),
        (16, 64),
        (0, 64),
        (32, 72),
        (40, 80),
    ]

    def _validate_table(base: int) -> Optional[tuple[int, int]]:
        """Return (last_off, first_off) if base looks like a player table, else None."""
        for last_off, first_off in NAME_GUESSES:
            matched = 0
            for slot in range(CHECK_SLOTS):
                slot_addr = base + slot * PLAYER_STRIDE
                last  = _read_wstr(slot_addr, last_off)
                first = _read_wstr(slot_addr, first_off)
                if _is_name(last) and _is_name(first):
                    matched += 1
            if matched >= MIN_MATCH:
                return (last_off, first_off)
        return None

    # ── Scan entire reachable module in 64 KB chunks ──────────────────────────
    # NBA2K26.exe is ~150 MB; scan up to 256 MB from module base.
    CHUNK      = 0x10000      # 64 KB
    MAX_OFFSET = 0x10000000   # 256 MB ceiling
    total_ptrs = 0
    total_checked = 0
    hits: list[dict] = []

    print(f"  scanning up to 256 MB of module for heap pointers...", file=sys.stderr)

    for chunk_off in range(0, MAX_OFFSET, CHUNK):
        if len(hits) >= 5:
            break
        try:
            data = mem_read(hproc, module_base + chunk_off, CHUNK)
        except Exception:
            continue
        for i in range(0, len(data) - 7, 8):
            val = int.from_bytes(data[i:i + 8], "little")
            if not (0x100000000 < val < 0x7FF000000000):
                continue
            total_ptrs += 1
            if total_ptrs % 50000 == 0:
                print(f"    ...{total_ptrs} pointers scanned, {len(hits)} confirmed so far", file=sys.stderr)

            # Direct check
            total_checked += 1
            offsets = _validate_table(val)
            if offsets:
                hits.append({
                    "new_player_rva_hex": hex(chunk_off + i),
                    "new_player_rva_dec": chunk_off + i,
                    "ptr_val": hex(val),
                    "chain": [],
                    "last_name_offset": offsets[0],
                    "first_name_offset": offsets[1],
                    "sample_names": [
                        _read_wstr(val + s * PLAYER_STRIDE, offsets[0]) + " " +
                        _read_wstr(val + s * PLAYER_STRIDE, offsets[1])
                        for s in range(6)
                        if _is_name(_read_wstr(val + s * PLAYER_STRIDE, offsets[0]))
                    ][:5],
                })
                if len(hits) >= 5:
                    break
                continue

            # One-level deep (manager → player array)
            try:
                sub_data = mem_read(hproc, val, 128)
            except Exception:
                continue
            for sub_off in range(0, 128, 8):
                sub = int.from_bytes(sub_data[sub_off:sub_off + 8], "little")
                if not (0x100000000 < sub < 0x7FF000000000):
                    continue
                offsets = _validate_table(sub)
                if offsets:
                    hits.append({
                        "new_player_rva_hex": hex(chunk_off + i),
                        "new_player_rva_dec": chunk_off + i,
                        "ptr_val": hex(val),
                        "chain": [sub_off],
                        "last_name_offset": offsets[0],
                        "first_name_offset": offsets[1],
                        "sample_names": [
                            _read_wstr(sub + s * PLAYER_STRIDE, offsets[0]) + " " +
                            _read_wstr(sub + s * PLAYER_STRIDE, offsets[1])
                            for s in range(6)
                            if _is_name(_read_wstr(sub + s * PLAYER_STRIDE, offsets[0]))
                        ][:5],
                    })
                    break

    print(f"  scan complete: {total_ptrs} total pointers, {total_checked} validated, {len(hits)} hits", file=sys.stderr)

    result = {
        "ok": True,
        "known_player_rva": hex(player_rva),
        "hits": hits,
        "instructions": (
            "For each hit: set 2k26_offsets.json 'Player.address' = new_player_rva_dec. "
            "If chain is non-empty add chain entries. "
            "Also update OFF_LAST_NAME / OFF_FIRST_NAME constants in live_import.py "
            "if last_name_offset / first_name_offset differ from current values (0 / 40)."
        ),
    }
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="NBA 2K26 Live Memory Import")
    parser.add_argument("--offsets", default=None,
                        help="Path to 2k26_offsets.json (auto-detected if omitted)")
    parser.add_argument("--input",   default=None,
                        help="Input JSON file (reads from stdin if omitted)")
    parser.add_argument("--diagnose", action="store_true",
                        help="Dump raw memory near player table pointer to help re-calibrate offsets after a patch")
    args = parser.parse_args()

    # ── Load offset JSON ─────────────────────────────────────────────────────
    offset_path = Path(args.offsets) if args.offsets else find_offset_json()
    if not offset_path or not offset_path.exists():
        print(json.dumps({
            "ok": False,
            "error": "Could not locate 2k26_offsets.json. Use --offsets to specify its path.",
        }))
        sys.exit(1)

    try:
        attr_map, tend_map, badge_map, player_rva, stride = load_offsets(offset_path)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"Failed to load offsets: {exc}"}))
        sys.exit(1)

    # ── Attach to game ───────────────────────────────────────────────────────
    pid = find_pid(GAME_EXE)
    if pid is None:
        print(json.dumps({
            "ok": False,
            "error": f"{GAME_EXE} is not running. Start the game first.",
        }))
        sys.exit(1)

    module_base = get_module_base(pid, GAME_EXE)
    if module_base is None:
        print(json.dumps({
            "ok": False,
            "error": "Could not resolve game module base address.",
        }))
        sys.exit(1)

    hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hproc:
        err = ctypes.get_last_error()
        print(json.dumps({
            "ok": False,
            "error": (
                f"OpenProcess failed (error {err}). "
                "Run the application as Administrator and ensure the game is in an editable state."
            ),
        }))
        sys.exit(1)

    try:
        # ── Diagnose mode: dump raw memory to help find correct offsets ──────
        if args.diagnose:
            diagnose_player_table(hproc, module_base, player_rva)
            sys.exit(0)

        # ── Read input payload ───────────────────────────────────────────────
        try:
            if args.input:
                with open(args.input, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            else:
                payload = json.load(sys.stdin)
        except Exception as exc:
            print(json.dumps({"ok": False, "error": f"Failed to read input: {exc}"}))
            sys.exit(1)

        entries = payload.get("entries", [])
        if not entries:
            print(json.dumps({"ok": False, "error": "No player entries in input."}))
            sys.exit(1)

        # ── Resolve player table ─────────────────────────────────────────────
        table_base, resolve_error = resolve_player_table_base(hproc, module_base, player_rva)
        if table_base is None:
            print(json.dumps({
                "ok": False,
                "error": resolve_error or "Could not resolve player table.",
            }))
            sys.exit(1)

        # ── Scan all players ─────────────────────────────────────────────────
        player_list = scan_players(hproc, table_base, stride)
        if not player_list:
            print(json.dumps({
                "ok": False,
                "error": "Player table scan returned no players.",
            }))
            sys.exit(1)

        # ── Process each entry ───────────────────────────────────────────────
        results: list[dict] = []
        total_written = 0

        for entry in entries:
            name    = str(entry.get("name", "")).strip()
            profile = entry.get("profile", {})

            if not name:
                results.append({"name": "(blank)", "ok": False, "error": "Missing player name"})
                continue

            record = find_player_record(name, player_list)
            if record is None:
                results.append({
                    "name": name,
                    "ok":   False,
                    "error": f"Player not found in roster (scanned {len(player_list)} players)",
                })
                continue

            written, skipped, warns = import_player(
                hproc, record["addr"], profile, attr_map, tend_map, badge_map
            )
            total_written += written
            results.append({
                "name":        name,
                "ok":          True,
                "matched":     f"{record['first']} {record['last']}",
                "index":       record["index"],
                "written":     written,
                "skipped":     skipped,
                "warnings":    warns,
            })

        print(json.dumps({
            "ok":           True,
            "totalPlayers": len(entries),
            "totalWritten": total_written,
            "results":      results,
        }))

    finally:
        CloseHandle(hproc)


if __name__ == "__main__":
    main()
