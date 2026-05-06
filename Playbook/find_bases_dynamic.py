"""
Dynamic resolver for player and team table bases after a patch.

What it does (read-only):
  - Attaches to the running NBA2K26.exe process.
  - Player base: searches memory for player table candidates by looking for
    a small set of expected player names inside the first N slots (default:
    Tyrese Maxey, Joel Embiid, Paul George within top 15). Candidates are
    ranked by how many expected names are found.
  - Team base: searches memory for the team table by looking for a run of
    known team names (UTF-16LE) spaced by the configured team stride and
    name offset; a few matches in order are enough to accept a candidate.
  - Stadium base: hunts for the stadium table using known arena names.
  - Staff base: hunts for the staff/coach table using known coach names.
  - Writes a report to Offsets/offsethunting/outputs/dynamic_bases.json and
    prints a summary.

Usage:
    python find_bases_dynamic.py
"""

from __future__ import annotations

import ctypes
import json
import sys
import time
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

try:
    import psutil
except ImportError:
    print("psutil is required. Install with: pip install psutil", file=sys.stderr)
    sys.exit(1)

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = OUTPUT_DIR / "dynamic_bases.json"

OFFSET_FILE_NAMES: Tuple[str, ...] = (
    "2k26_offsets.json",
    "2K26_Offsets.json",
    "2K26_offsets.json",
    "2k26_Offsets.json",
    "2k26_offsets.txt",
    "2K26_Offsets.txt",
)

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
READABLE_PROTECT = {
    0x02,  # PAGE_READONLY
    0x04,  # PAGE_READWRITE
    0x08,  # PAGE_WRITECOPY
    0x20,  # PAGE_EXECUTE_READ
    0x40,  # PAGE_EXECUTE_READWRITE
    0x80,  # PAGE_EXECUTE_WRITECOPY
}

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_ulong),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_ulong),
        ("Protect", ctypes.c_ulong),
        ("Type", ctypes.c_ulong),
    ]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_uint]
OpenProcess.restype = ctypes.c_void_p

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [ctypes.c_void_p]
CloseHandle.restype = ctypes.c_bool

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
ReadProcessMemory.restype = ctypes.c_bool

VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    ctypes.c_size_t,
]
VirtualQueryEx.restype = ctypes.c_size_t


def encode_wstring(text: str) -> bytes:
    return (text + "\x00").encode("utf-16le", errors="ignore")


def decode_wstring(data: bytes) -> str:
    try:
        text = data.decode("utf-16le", errors="ignore")
    except Exception:
        return ""
    return text.split("\x00", 1)[0].strip()


def read_wstring(handle: int, address: int, max_chars: int) -> str:
    buf = read_memory(handle, address, max(1, max_chars) * 2)
    if not buf:
        return ""
    return decode_wstring(buf)


def normalize_name(first: str, last: str) -> str:
    return " ".join(f"{first} {last}".split()).lower()


def parse_int(value: object, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        if isinstance(value, int):
            return value
        text = str(value).strip().replace("_", "")
        if not text:
            return default
        base = 16 if text.lower().startswith("0x") else 10
        return int(text, base)
    except Exception:
        return default


def find_offsets_file() -> Path | None:
    here = Path(__file__).resolve()
    search_dirs = [here.parent, here.parent.parent, here.parent.parent.parent]
    seen = set()
    for base in search_dirs:
        if not isinstance(base, Path):
            continue
        if base in seen:
            continue
        seen.add(base)
        for name in OFFSET_FILE_NAMES:
            candidate = base / name
            if candidate.is_file():
                return candidate
    return None


def load_stride_and_name_offsets() -> dict:
    offsets_path = find_offsets_file()
    result = {
        "stride": None,
        "team_stride": None,
        "staff_stride": None,
        "stadium_stride": None,
        "first_offset": 0x28,
        "last_offset": 0x0,
        "player_name_length": 20,
        "team_name_offset": 738,  # 0x2E2
        "team_name_length": 24,
        "staff_first_offset": 0x50,  # 80
        "staff_last_offset": 0x78,   # 120
        "staff_name_length": 40,
        "stadium_name_offset": 0x0,
        "stadium_name_length": 33,
        "offsets_path": str(offsets_path) if offsets_path else "",
    }
    if not offsets_path:
        return result
    try:
        data = json.loads(offsets_path.read_text(encoding="utf-8"))
    except Exception:
        return result
    game_info = data.get("game_info") or {}
    result["stride"] = parse_int(game_info.get("playerSize"))
    result["team_stride"] = parse_int(game_info.get("teamSize"))
    result["staff_stride"] = parse_int(game_info.get("staffSize"))
    result["stadium_stride"] = parse_int(game_info.get("stadiumSize"))
    offsets = data.get("offsets")
    if isinstance(offsets, list):
        for entry in offsets:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("category", "")).lower() != "vitals":
                continue
            name = str(entry.get("name", "")).lower()
            if name == "first name":
                val = parse_int(entry.get("address"))
                if val is not None:
                    result["first_offset"] = val
                length = parse_int(entry.get("length"))
                if length:
                    result["player_name_length"] = max(result["player_name_length"], length)
            elif name == "last name":
                val = parse_int(entry.get("address"))
                if val is not None:
                    result["last_offset"] = val
                length = parse_int(entry.get("length"))
                if length:
                    result["player_name_length"] = max(result["player_name_length"], length)
            # Staff name offsets live in the Staff Vitals category.
            staff_cat = str(entry.get("category", "")).lower()
            if staff_cat == "staff vitals":
                if name == "first name":
                    val = parse_int(entry.get("address"))
                    if val is not None:
                        result["staff_first_offset"] = val
                    length = parse_int(entry.get("length"))
                    if length:
                        result["staff_name_length"] = max(result["staff_name_length"], length)
                elif name == "last name":
                    val = parse_int(entry.get("address"))
                    if val is not None:
                        result["staff_last_offset"] = val
                    length = parse_int(entry.get("length"))
                    if length:
                        result["staff_name_length"] = max(result["staff_name_length"], length)
    return result


def find_process_pid(exe_name: str = "nba2k26.exe") -> int | None:
    exe_lower = exe_name.lower()
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name == exe_lower:
                return int(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def iter_memory_regions(handle: int, start: int, end: int) -> Iterator[Tuple[int, int, int]]:
    mbi = MEMORY_BASIC_INFORMATION()
    current = start
    while current < end:
        result = VirtualQueryEx(handle, ctypes.c_void_p(current), ctypes.byref(mbi), ctypes.sizeof(mbi))
        if not result:
            current += 0x1000
            continue
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if size <= 0:
            current += 0x1000
            continue
        region_end = base + size
        state = int(mbi.State)
        raw_protect = int(mbi.Protect)
        base_protect = raw_protect & 0xFF
        if state == MEM_COMMIT and base_protect in READABLE_PROTECT and not (raw_protect & PAGE_GUARD):
            yield base, min(size, end - base), raw_protect
        current = max(region_end, current + 0x1000)


def read_memory(handle: int, address: int, size: int) -> bytes | None:
    if size <= 0:
        return None
    buffer = (ctypes.c_char * size)()
    read = ctypes.c_size_t(0)
    ok = ReadProcessMemory(handle, ctypes.c_void_p(address), buffer, size, ctypes.byref(read))
    if not ok or read.value == 0:
        return None
    return bytes(buffer[: read.value])


def find_all(data: bytes, pattern: bytes) -> Iterable[int]:
    start = 0
    while True:
        idx = data.find(pattern, start)
        if idx == -1:
            break
        yield idx
        start = idx + 2  # step by 2 bytes to stay UTF-16 aligned


def scan_player_names(
    handle: int,
    stride: int,
    first_offset: int,
    last_offset: int,
    name_length: int,
    targets: list[Tuple[str, str]],
    *,
    window: int,
    min_matches: int,
) -> tuple[list[dict], list[int]]:
    hits: list[dict] = []
    base_candidates: list[int] = []
    if not targets:
        return hits, base_candidates
    patterns = [
        (encode_wstring(last), encode_wstring(first), first, last)
        for first, last in targets
    ]
    expected = {normalize_name(first, last) for first, last in targets}
    window = max(1, int(window))
    min_matches = max(1, min(int(min_matches), len(expected)))
    seen_bases: set[int] = set()

    # Scan full user space (up to 0x7FFFFFFFFFFF)
    low, high = 0, 0x7FFFFFFFFFFF
    for region_base, region_size, _ in iter_memory_regions(handle, low, high):
        try:
            buf = read_memory(handle, region_base, region_size)
        except Exception:
            buf = None
        if not buf:
            continue
        for last_bytes, first_bytes, first, last in patterns:
            start = 0
            while True:
                idx = buf.find(last_bytes, start)
                if idx == -1:
                    break
                candidate = region_base + idx - last_offset
                first_start = candidate + first_offset
                block = read_memory(handle, first_start, len(first_bytes))
                if not block or not block.startswith(first_bytes):
                    start = idx + 2
                    continue
                hits.append({"target": f"{first} {last}", "address": candidate})
                for slot in range(window):
                    base = candidate - slot * stride
                    if base < 0:
                        break
                    if base in seen_bases:
                        continue
                    matched: set[str] = set()
                    match_count = 0
                    for i in range(window):
                        last_name = read_wstring(handle, base + i * stride + last_offset, name_length)
                        if not last_name:
                            continue
                        first_name = read_wstring(handle, base + i * stride + first_offset, name_length)
                        full = normalize_name(first_name, last_name)
                        if full in expected and full not in matched:
                            matched.add(full)
                            match_count += 1
                            if match_count >= len(expected):
                                break
                    if match_count >= min_matches:
                        base_candidates.extend([base] * match_count)
                    seen_bases.add(base)
                start = idx + 2
    return hits, base_candidates


def find_team_table(
    handle: int,
    team_stride: int,
    name_offset: int,
    name_length: int,
    expected_names: list[str],
    search_low: int = 0,
    search_high: int = 0x7FFFFFFFFFFF,
) -> list[int]:
    if not expected_names:
        return []
    first_pat = encode_wstring(expected_names[0])
    candidates: list[int] = []
    for region_base, region_size, _ in iter_memory_regions(handle, search_low, search_high):
        buf = read_memory(handle, region_base, region_size)
        if not buf:
            continue
        start = 0
        while True:
            idx = buf.find(first_pat, start)
            if idx == -1:
                break
            table_base = region_base + idx - name_offset
            ok = True
            for i, name in enumerate(expected_names[1:], start=1):
                addr = table_base + i * team_stride + name_offset
                chunk = read_memory(handle, addr, name_length * 2)
                if not chunk:
                    ok = False
                    break
                val = chunk.decode("utf-16le", errors="ignore").split("\x00", 1)[0].strip().lower()
                if not val or val != name.lower():
                    ok = False
                    break
            if ok:
                candidates.append(table_base)
            start = idx + 2
    return candidates


def summarize_candidates(values: list[int]) -> list[tuple[int, int]]:
    from collections import Counter

    counts = Counter(values)
    return counts.most_common(5)


def main() -> None:
    cfg = load_stride_and_name_offsets()
    stride = cfg["stride"] or 1176
    team_stride = cfg["team_stride"] or 5672
    staff_stride = cfg["staff_stride"] or 432
    stadium_stride = cfg["stadium_stride"] or 4792
    first_offset = cfg["first_offset"]
    last_offset = cfg["last_offset"]
    player_name_length = cfg["player_name_length"]
    team_name_offset = cfg["team_name_offset"]
    team_name_length = cfg["team_name_length"]
    staff_first_offset = cfg["staff_first_offset"]
    staff_last_offset = cfg["staff_last_offset"]
    staff_name_length = cfg["staff_name_length"]
    stadium_name_offset = cfg["stadium_name_offset"]
    stadium_name_length = cfg["stadium_name_length"]

    pid = find_process_pid()
    if not pid:
        print("NBA2K26.exe not running. Launch the game and retry.")
        return

    handle = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        print("Failed to open NBA2K26.exe for reading.")
        return

    start_time = time.time()
    try:
        # Player base hunt
        targets = [("Tyrese", "Maxey"), ("Joel", "Embiid"), ("Paul", "George")]
        player_window = 15
        player_min_matches = 3
        player_hits, player_base_votes = scan_player_names(
            handle,
            stride,
            first_offset,
            last_offset,
            player_name_length,
            targets,
            window=player_window,
            min_matches=player_min_matches,
        )
        top_player = summarize_candidates(player_base_votes)

        # Team base hunt
        expected_teams = [
            "76ers",
            "Bucks",
            "Bulls",
            "Cavaliers",
            "Celtics",
            "Clippers",
            "Grizzlies",
            "Hawks",
            "Heat",
            "Hornets",
        ]
        team_candidates = find_team_table(
            handle, team_stride, team_name_offset, team_name_length, expected_teams
        )
        top_team = summarize_candidates(team_candidates)

        # Stadium base hunt
        expected_stadiums = [
            "Xfinity Mobile Arena",
            "Fiserv Forum",
            "United Center",
        ]
        stadium_candidates = find_team_table(
            handle, stadium_stride, stadium_name_offset, stadium_name_length, expected_stadiums
        )
        top_stadium = summarize_candidates(stadium_candidates)

        # Staff base hunt
        staff_targets = [("Nick", "Nurse"), ("Doc", "Rivers")]
        staff_window = 12
        staff_min_matches = 1
        staff_hits, staff_base_votes = scan_player_names(
            handle,
            staff_stride,
            staff_first_offset,
            staff_last_offset,
            staff_name_length,
            staff_targets,
            window=staff_window,
            min_matches=staff_min_matches,
        )
        top_staff = summarize_candidates(staff_base_votes)
    finally:
        CloseHandle(handle)

    elapsed = time.time() - start_time
    output = {
        "meta": {
            "pid": pid,
            "elapsed_sec": round(elapsed, 3),
            "stride": stride,
            "team_stride": team_stride,
            "staff_stride": staff_stride,
            "stadium_stride": stadium_stride,
            "first_offset": first_offset,
            "last_offset": last_offset,
            "player_name_length": player_name_length,
            "player_window": player_window,
            "player_min_matches": player_min_matches,
            "player_targets": [f"{f} {l}" for f, l in targets],
            "team_name_offset": team_name_offset,
            "team_name_length": team_name_length,
            "staff_first_offset": staff_first_offset,
            "staff_last_offset": staff_last_offset,
            "staff_name_length": staff_name_length,
            "staff_window": staff_window,
            "staff_min_matches": staff_min_matches,
            "staff_targets": [f"{f} {l}" for f, l in staff_targets],
            "stadium_name_offset": stadium_name_offset,
            "stadium_name_length": stadium_name_length,
            "stadium_targets": expected_stadiums,
            "offsets_file": cfg["offsets_path"],
        },
        "player_hits": [
            {"target": h["target"], "address": f"0x{int(h['address']):X}"} for h in player_hits
        ],
        "player_candidates": [
            {"address": f"0x{addr:X}", "votes": votes} for addr, votes in top_player
        ],
        "team_candidates": [{"address": f"0x{addr:X}", "votes": votes} for addr, votes in top_team],
        "stadium_candidates": [{"address": f"0x{addr:X}", "votes": votes} for addr, votes in top_stadium],
        "staff_hits": [
            {"target": h["target"], "address": f"0x{int(h['address']):X}"} for h in staff_hits
        ],
        "staff_candidates": [{"address": f"0x{addr:X}", "votes": votes} for addr, votes in top_staff],
    }
    OUTPUT_JSON.write_text(json.dumps(output, indent=2))

    print(f"Done in {elapsed:.2f}s")
    if top_player:
        addr, votes = top_player[0]
        print(f"Player base candidate: 0x{addr:X} ({votes} votes)")
    else:
        print("Player base: no candidates found")
    if top_team:
        addr, votes = top_team[0]
        print(f"Team base candidate: 0x{addr:X} ({votes} votes)")
    else:
        print("Team base: no candidates found")
    if top_stadium:
        addr, votes = top_stadium[0]
        print(f"Stadium base candidate: 0x{addr:X} ({votes} votes)")
    else:
        print("Stadium base: no candidates found")
    if top_staff:
        addr, votes = top_staff[0]
        print(f"Staff base candidate: 0x{addr:X} ({votes} votes)")
    else:
        print("Staff base: no candidates found")
    print(f"Wrote {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
