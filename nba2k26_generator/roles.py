"""Role assignment system for NBA 2K26 using ML attributes + NBA stats.

Every player gets exactly 5 roles:
  1 Hierarchy role (T1/T2/T3/S1/S2/S3)
  1 Core role (ROL/CON/ISO/BEN/MIC/etc)
  3 playstyle roles (scoring, defense, drive, IQ, utility, specialist)

Elite players get a 6th Unicorn role that boosts attributes.
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple


# ── Role catalog parsed from Player Roles.txt ────────────────────────────

HIERARCHY_ROLES = ["T1", "T2", "T3", "S1", "S2", "S3"]

CORE_ROLES = [
    "ROL", "CON", "ISO", "BEN", "MIC", "DEV", "SPT", "CLO", "STBLY",
    "FILL", "VET", "ENG", "GLUE", "ROT", "EMG",
]

SCORING_ROLES = [
    "3L", "SHO", "SHH", "MOV", "MID", "SLH", "RR", "FIN", "PBF", "STB",
    "POP", "FAC", "LOB", "PNR", "ISO3", "PST", "CUT", "REL", "FLO", "ARC",
    "DUNK", "TIP", "FADE", "HOOK", "UPN", "BANK", "RUN", "COR", "WING",
    "PULL", "C&S", "TRAIL", "PUT", "LOBF", "STEP",
]

DRIVE_ROLES = [
    "BLW", "BUL", "CTL", "TRN", "HFL", "PHY", "GLD", "SPN", "HES", "STP",
    "EURO", "STR", "SNAK", "SPLT", "WRAP", "EXT", "ACRO", "REV", "ONE",
    "TWO", "BODY", "SHIFT", "BURST", "GRIND", "LEAN", "FWD", "BACK",
    "SIDE", "ANGLE", "CUTDRV",
]

DEFENSE_ROLES = [
    "LOCK", "POA", "BHW", "RIMD", "SWI", "GLS", "ANCH", "HELP", "INT",
    "CHS", "POSTD", "WEAK", "SCRN", "DISC", "DENY", "PRESS", "STUNT",
    "RECOV", "CONTEST", "VERT", "DROP", "HEDGE", "BLITZ", "ZONE", "TAG",
    "DIG", "ROT", "CLOSE", "HAND", "STRIP", "WALL", "BOXD", "BOARD",
    "BUMP", "MIRROR", "TRACK", "CUTD", "FOUL", "DISC2", "STAY",
]

IQ_ROLES = [
    "PSS", "CALM", "RHY", "FLOW", "READ", "SET", "ADJ", "SAFE", "RISK",
    "ORCH", "DELAY", "FAST", "SCAN", "TIM", "FEEL", "INST", "REACT",
    "PLAN", "CTRL", "BAL", "COMPOSE", "CLUTCHIQ", "PACE", "DISCIP",
    "AWARE", "VISION", "ANGLEIQ", "CLOCK", "SETUP", "CONTROL2",
]

UTILITY_ROLES = [
    "JAT", "TWB", "OGM", "SGR", "SGF", "L3P", "H3P", "SCR", "REB",
    "BOX", "HUST", "DIRT", "GLUE", "LINK", "SPC", "FILL2", "CLEAN",
    "CHASE", "CUT2", "MOVE", "STACK", "BAL2", "SUP", "HELP2", "ROT2",
]

SPECIALIST_ROLES = [
    "CLM", "PNH", "DHO", "SCO", "DEC", "GRAV", "ROLL", "SHORT", "KICK",
    "HAND2", "TIPD", "LOB2", "SCREENIQ", "PIN", "FLARE", "BACKCUT",
    "HAMMER", "GHOST", "RELOC", "DRAG", "STACKPNR", "SPAIN", "DELAYSET",
    "POSTHUB", "ELBOW",
]

UNICORN_ROLES = [
    "TDH", "PCE", "GRV+", "DSC", "MME", "SCE", "OFF+", "3LV+", "CLX", "VRE",
]

# Roles that contradict each other — only one can be assigned
ROLE_CONTRADICTIONS = [
    {"BUL", "PHY"},
    {"SHO", "H3P", "L3P"},
    {"JAT", "TWB"},
    {"SPT", "ISO"},
    {"SHO", "FIN"},
]

# Roles that are redundant — keep only the strongest
ROLE_REDUNDANCY_GROUPS = [
    {"BUL", "PHY"},
    {"SHO", "H3P", "L3P"},
    {"JAT", "TWB"},
]

# ── Attribute boost definitions per role ─────────────────────────────────
# Each role gives +N to specific attributes. Unicorn roles give bigger boosts.

ROLE_BOOSTS: Dict[str, Dict[str, int]] = {
    # HIERARCHY boosts
    "T1": {"Pass Vision": 2, "Ball Handle": 2, "Offensive Consistency": 1},
    "T2": {"Pass Vision": 1, "Ball Handle": 1, "Offensive Consistency": 1},
    "T3": {"Pass IQ": 1, "Offensive Consistency": 1},
    "S1": {"Shot IQ": 2, "Offensive Consistency": 1},
    "S2": {"Shot IQ": 1, "Offensive Consistency": 1},
    "S3": {"Offensive Consistency": 1},

    # CORE boosts
    "CON": {"Pass Vision": 2, "Pass IQ": 2, "Ball Handle": 1},
    "ISO": {"Ball Handle": 2, "Shot IQ": 1, "Offensive Consistency": 1},
    "MIC": {"Shot IQ": 1, "Offensive Consistency": 2},
    "CLO": {"Shot IQ": 2, "Offensive Consistency": 2, "ClutchIQ": 1},
    "ROL": {},
    "BEN": {},
    "DEV": {"Potential": 3},
    "SPT": {"Three-Point Shot": 1, "Shot IQ": 1},
    "STBLY": {"Offensive Consistency": 2, "Defensive Consistency": 1},
    "VET": {"Shot IQ": 1, "Pass IQ": 1, "Defensive Consistency": 1},
    "ENG": {"Hustle": 2, "Stamina": 1},
    "GLUE": {"Defensive Consistency": 1, "Hustle": 1, "Offensive Consistency": 1},
    "ROT": {"Stamina": 1},
    "FILL": {},
    "EMG": {},

    # SCORING boosts
    "3L": {"Mid-Range Shot": 1, "Three-Point Shot": 1, "Driving Layup": 1},
    "SHO": {"Three-Point Shot": 2, "Free Throw": 1},
    "SHH": {"Three-Point Shot": 1, "Shot IQ": 1},
    "MOV": {"Three-Point Shot": 1, "Speed with Ball": 1},
    "MID": {"Mid-Range Shot": 2, "Shot IQ": 1},
    "SLH": {"Driving Dunk": 1, "Driving Layup": 1, "Speed with Ball": 1},
    "RR": {"Standing Dunk": 1, "Speed": 1},
    "FIN": {"Driving Layup": 1, "Close Shot": 1},
    "PST": {"Post Control": 2, "Post Hook": 1},
    "PNR": {"Standing Dunk": 1, "Close Shot": 1},
    "CUT": {"Close Shot": 1, "Speed": 1},
    "FLO": {"Driving Layup": 1, "Ball Handle": 1},
    "ARC": {"Three-Point Shot": 2},
    "DUNK": {"Driving Dunk": 2, "Vertical": 1},
    "FADE": {"Post Fade": 2, "Mid-Range Shot": 1},
    "HOOK": {"Post Hook": 2},
    "PULL": {"Mid-Range Shot": 1, "Three-Point Shot": 1, "Ball Handle": 1},
    "C&S": {"Three-Point Shot": 1, "Shot IQ": 1},
    "STEP": {"Mid-Range Shot": 1, "Three-Point Shot": 1, "Ball Handle": 1},
    "STB": {"Three-Point Shot": 1, "Close Shot": 1},
    "POP": {"Mid-Range Shot": 1, "Three-Point Shot": 1},
    "FAC": {"Mid-Range Shot": 1, "Post Control": 1},
    "LOB": {"Vertical": 1, "Close Shot": 1},
    "ISO3": {"Three-Point Shot": 1, "Ball Handle": 1},
    "REL": {"Three-Point Shot": 1},
    "TIP": {"Offensive Rebound": 1, "Close Shot": 1},
    "UPN": {"Post Control": 1, "Close Shot": 1},
    "BANK": {"Mid-Range Shot": 1, "Close Shot": 1},
    "RUN": {"Driving Layup": 1, "Speed": 1},
    "COR": {"Three-Point Shot": 1},
    "WING": {"Mid-Range Shot": 1, "Three-Point Shot": 1},
    "TRAIL": {"Three-Point Shot": 1},
    "PUT": {"Offensive Rebound": 1, "Close Shot": 1},
    "LOBF": {"Vertical": 1, "Close Shot": 1},
    "PBF": {"Offensive Rebound": 1, "Close Shot": 1},

    # DRIVE boosts
    "BLW": {"Speed with Ball": 2, "Driving Layup": 1},
    "BUL": {"Strength": 2, "Driving Layup": 1},
    "CTL": {"Ball Handle": 1, "Speed with Ball": 1},
    "TRN": {"Speed": 1, "Driving Layup": 1},
    "HFL": {"Driving Dunk": 1, "Vertical": 1},
    "PHY": {"Strength": 1, "Driving Layup": 1},
    "GLD": {"Speed with Ball": 1, "Driving Layup": 1},
    "SPN": {"Ball Handle": 1, "Driving Layup": 1},
    "HES": {"Ball Handle": 1, "Speed with Ball": 1},
    "STP": {"Ball Handle": 1},
    "EURO": {"Driving Layup": 1, "Ball Handle": 1},
    "STR": {"Speed": 1, "Driving Layup": 1},
    "SNAK": {"Ball Handle": 1, "Pass Vision": 1},
    "SPLT": {"Ball Handle": 1, "Speed with Ball": 1},
    "WRAP": {"Driving Layup": 1, "Ball Handle": 1},
    "EXT": {"Driving Layup": 1},
    "ACRO": {"Driving Layup": 1, "Vertical": 1},
    "REV": {"Driving Layup": 1, "Ball Handle": 1},
    "ONE": {"Driving Layup": 1, "Vertical": 1},
    "TWO": {"Driving Layup": 1, "Strength": 1},
    "BODY": {"Driving Layup": 1, "Strength": 1},
    "SHIFT": {"Ball Handle": 1, "Speed with Ball": 1},
    "BURST": {"Speed": 1, "Driving Layup": 1},
    "GRIND": {"Strength": 1, "Stamina": 1},
    "LEAN": {"Driving Layup": 1},
    "FWD": {"Speed": 1},
    "BACK": {"Ball Handle": 1},
    "SIDE": {"Ball Handle": 1},
    "ANGLE": {"Ball Handle": 1, "Driving Layup": 1},
    "CUTDRV": {"Speed": 1, "Close Shot": 1},

    # DEFENSE boosts
    "LOCK": {"Perimeter Defense": 2, "Steal": 1},
    "POA": {"Perimeter Defense": 2, "Steal": 1},
    "BHW": {"Steal": 2, "Pass Perception": 1},
    "RIMD": {"Interior Defense": 1, "Block": 1},
    "SWI": {"Perimeter Defense": 1, "Interior Defense": 1},
    "GLS": {"Defensive Rebound": 2, "Strength": 1},
    "ANCH": {"Interior Defense": 2, "Block": 2},
    "HELP": {"Help Defense IQ": 2, "Interior Defense": 1},
    "INT": {"Pass Perception": 2, "Steal": 1},
    "CHS": {"Speed": 1, "Perimeter Defense": 1},
    "POSTD": {"Interior Defense": 1, "Strength": 1},
    "WEAK": {"Block": 1, "Help Defense IQ": 1},
    "SCRN": {"Perimeter Defense": 1, "Strength": 1},
    "DISC": {"Help Defense IQ": 1, "Defensive Consistency": 1},
    "DENY": {"Perimeter Defense": 1, "Steal": 1},
    "PRESS": {"Perimeter Defense": 1, "Steal": 1},
    "STUNT": {"Help Defense IQ": 1},
    "RECOV": {"Speed": 1, "Perimeter Defense": 1},
    "CONTEST": {"Interior Defense": 1, "Block": 1},
    "VERT": {"Block": 1, "Vertical": 1},
    "DROP": {"Interior Defense": 1, "Block": 1},
    "HEDGE": {"Interior Defense": 1, "Perimeter Defense": 1},
    "BLITZ": {"Perimeter Defense": 1, "Steal": 1},
    "ZONE": {"Help Defense IQ": 2, "Pass Perception": 1},
    "TAG": {"Help Defense IQ": 1},
    "DIG": {"Steal": 1, "Pass Perception": 1},
    "ROT": {"Help Defense IQ": 1, "Defensive Consistency": 1},
    "CLOSE": {"Perimeter Defense": 1, "Speed": 1},
    "HAND": {"Steal": 1, "Pass Perception": 1},
    "STRIP": {"Steal": 2},
    "WALL": {"Interior Defense": 1, "Strength": 1},
    "BOXD": {"Defensive Rebound": 1, "Strength": 1},
    "BOARD": {"Defensive Rebound": 2, "Offensive Rebound": 1},
    "BUMP": {"Strength": 1, "Interior Defense": 1},
    "MIRROR": {"Perimeter Defense": 1, "Speed": 1},
    "TRACK": {"Perimeter Defense": 1},
    "CUTD": {"Help Defense IQ": 1},
    "FOUL": {"Defensive Consistency": 1},
    "DISC2": {"Defensive Consistency": 2},
    "STAY": {"Defensive Consistency": 1},

    # IQ boosts
    "PSS": {"Pass Vision": 2, "Pass Accuracy": 1},
    "CALM": {"Pass IQ": 1, "Offensive Consistency": 1},
    "RHY": {"Offensive Consistency": 1},
    "FLOW": {"Pass IQ": 1, "Offensive Consistency": 1},
    "READ": {"Pass Vision": 1, "Shot IQ": 1},
    "SET": {"Offensive Consistency": 1},
    "ADJ": {"Shot IQ": 1, "Pass IQ": 1},
    "SAFE": {"Pass IQ": 1},
    "RISK": {"Pass Vision": 1, "Ball Handle": 1},
    "ORCH": {"Pass Vision": 2, "Pass IQ": 1},
    "DELAY": {"Pass IQ": 1},
    "FAST": {"Speed with Ball": 1, "Pass IQ": 1},
    "SCAN": {"Pass Vision": 1, "Pass IQ": 1},
    "TIM": {"Offensive Consistency": 1},
    "FEEL": {"Pass IQ": 1},
    "INST": {"Pass Perception": 1, "Steal": 1},
    "REACT": {"Perimeter Defense": 1, "Steal": 1},
    "PLAN": {"Pass IQ": 1},
    "CTRL": {"Ball Handle": 1, "Pass IQ": 1},
    "BAL": {"Offensive Consistency": 1, "Defensive Consistency": 1},
    "COMPOSE": {"Shot IQ": 1, "Offensive Consistency": 1},
    "CLUTCHIQ": {"Shot IQ": 2, "Offensive Consistency": 1},
    "PACE": {"Pass IQ": 1, "Ball Handle": 1},
    "DISCIP": {"Offensive Consistency": 1, "Defensive Consistency": 1},
    "AWARE": {"Pass IQ": 1, "Shot IQ": 1},
    "VISION": {"Pass Vision": 2, "Pass IQ": 1},
    "ANGLEIQ": {"Pass Vision": 1, "Pass Accuracy": 1},
    "CLOCK": {"Pass IQ": 1},
    "SETUP": {"Pass Vision": 1, "Ball Handle": 1},
    "CONTROL2": {"Ball Handle": 1, "Pass IQ": 1},

    # UTILITY boosts
    "JAT": {"Offensive Consistency": 1, "Defensive Consistency": 1},
    "TWB": {"Perimeter Defense": 1, "Shot IQ": 1},
    "OGM": {"Speed": 1, "Stamina": 1},
    "SGR": {"Ball Handle": 1},
    "SGF": {"Perimeter Defense": 1},
    "L3P": {"Three-Point Shot": 1},
    "H3P": {"Three-Point Shot": 1},
    "SCR": {"Strength": 1},
    "REB": {"Defensive Rebound": 1, "Offensive Rebound": 1},
    "BOX": {"Defensive Rebound": 1, "Strength": 1},
    "HUST": {"Hustle": 2},
    "DIRT": {"Hustle": 2, "Strength": 1},
    "LINK": {"Pass IQ": 1},
    "SPC": {"Three-Point Shot": 1},
    "FILL2": {},
    "CLEAN": {"Close Shot": 1},
    "CHASE": {"Speed": 1, "Hustle": 1},
    "CUT2": {"Close Shot": 1, "Speed": 1},
    "MOVE": {"Speed": 1, "Stamina": 1},
    "STACK": {},
    "BAL2": {"Offensive Consistency": 1, "Defensive Consistency": 1},
    "SUP": {},
    "HELP2": {"Help Defense IQ": 1},
    "ROT2": {"Stamina": 1},

    # SPECIALIST boosts
    "CLM": {"Shot IQ": 2, "Offensive Consistency": 2},
    "PNH": {"Ball Handle": 1, "Pass Vision": 1},
    "DHO": {"Pass Accuracy": 1, "Ball Handle": 1},
    "SCO": {"Pass Vision": 1, "Shot IQ": 1},
    "DEC": {"Three-Point Shot": 1},
    "GRAV": {"Three-Point Shot": 2, "Shot IQ": 1},
    "ROLL": {"Close Shot": 1, "Vertical": 1},
    "SHORT": {"Pass Vision": 1, "Close Shot": 1},
    "KICK": {"Pass Accuracy": 1, "Ball Handle": 1},
    "HAND2": {"Steal": 1, "Pass Perception": 1},
    "TIPD": {"Block": 1, "Vertical": 1},
    "LOB2": {"Vertical": 1, "Close Shot": 1},
    "SCREENIQ": {"Strength": 1, "Pass IQ": 1},
    "PIN": {"Three-Point Shot": 1, "Shot IQ": 1},
    "FLARE": {"Three-Point Shot": 1},
    "BACKCUT": {"Close Shot": 1, "Speed": 1},
    "HAMMER": {"Three-Point Shot": 1},
    "GHOST": {"Ball Handle": 1},
    "RELOC": {"Three-Point Shot": 1},
    "DRAG": {"Close Shot": 1},
    "STACKPNR": {"Close Shot": 1, "Vertical": 1},
    "SPAIN": {"Three-Point Shot": 1, "Pass IQ": 1},
    "DELAYSET": {"Pass IQ": 1},
    "POSTHUB": {"Post Control": 1, "Pass Vision": 1},
    "ELBOW": {"Mid-Range Shot": 1, "Pass Vision": 1},

    # UNICORN boosts (bigger — these define elite players)
    "TDH": {"Pass Vision": 3, "Ball Handle": 2, "Defensive Rebound": 2, "Offensive Consistency": 2},
    "PCE": {"Pass IQ": 3, "Ball Handle": 2, "Offensive Consistency": 2},
    "GRV+": {"Three-Point Shot": 3, "Shot IQ": 2, "Offensive Consistency": 2},
    "DSC": {"Interior Defense": 3, "Block": 2, "Help Defense IQ": 2},
    "MME": {"Ball Handle": 2, "Mid-Range Shot": 2, "Strength": 2, "Offensive Consistency": 1},
    "SCE": {"Ball Handle": 2, "Shot IQ": 2, "Offensive Consistency": 3},
    "OFF+": {"Pass Vision": 2, "Shot IQ": 2, "Ball Handle": 2, "Offensive Consistency": 2},
    "3LV+": {"Three-Point Shot": 2, "Mid-Range Shot": 2, "Driving Layup": 2},
    "CLX": {"Shot IQ": 3, "Offensive Consistency": 3, "Ball Handle": 1},
    "VRE": {"Offensive Consistency": 2, "Defensive Consistency": 2, "Stamina": 2},
}


def load_role_catalog(path: str) -> Dict[str, List[str]]:
    """Load role catalog from Player Roles.txt."""
    if not path or not os.path.exists(path):
        return {}

    sections: Dict[str, List[str]] = {}
    current_section = ""

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            # Section headers start with emoji
            if any(line.startswith(e) for e in ("\U0001f9e0", "\U0001f3ae", "\U0001f3af",
                                                  "\U0001f3c3", "\U0001f6e1", "\U0001f9e9",
                                                  "\U0001f984")):
                section_title = re.sub(r"^\W+", "", line).strip()
                section_title = re.sub(r"\s*\(\d+\)\s*$", "", section_title).strip()
                current_section = section_title
                sections.setdefault(current_section, [])
                continue
            if "=" in line and current_section:
                code = line.split("=", 1)[0].strip()
                if code:
                    sections[current_section].append(code)

    return sections


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _remap(v: float, in_lo: float, in_hi: float, out_lo: float = 0.0, out_hi: float = 1.0) -> float:
    if in_hi == in_lo:
        return out_lo
    return _clamp(out_lo + (v - in_lo) / (in_hi - in_lo) * (out_hi - out_lo), out_lo, out_hi)


def _na(attrs: Dict[str, int], name: str) -> float:
    """Normalize attribute (25-99) to 0-100."""
    return _clamp(_remap(float(attrs.get(name, 25)), 25.0, 99.0, 0.0, 100.0), 0.0, 100.0)


def _sg(stats: Dict[str, float], key: str, default: float = 0.0) -> float:
    try:
        return float(stats.get(key, default))
    except (ValueError, TypeError):
        return default


def _n(value: float, lo: float, hi: float) -> float:
    return _remap(value, lo, hi, 0.0, 1.0)


def _pick_hierarchy(stats: Dict[str, float], attrs: Dict[str, int], position: str) -> str:
    """Pick 1 hierarchy role based on usage, passing, and scoring load."""
    usg = _sg(stats, "f_usg", 0.0)
    ast_pct = _sg(stats, "f_ast_pct", 0.0)
    pts = _sg(stats, "f_pg_pts", 0.0)
    fga = _sg(stats, "f_pg_fga", 0.0)
    ast = _sg(stats, "f_pg_ast", 0.0)
    usage = _n(usg, 12.0, 35.0)
    passing = _n(ast_pct, 5.0, 42.0)

    is_big = any(p in position.upper() for p in ("C", "PF"))
    is_guard = any(p in position.upper() for p in ("PG", "SG"))

    # T-tier = playmaking-led creation
    if passing >= 0.70 and usage >= 0.55:
        return "T1"
    if passing >= 0.55 and usage >= 0.45:
        return "T2"
    if passing >= 0.45 and usage >= 0.40:
        return "T3"

    # S-tier = score-first
    if usage >= 0.55 and (fga >= 18.0 or pts >= 25.0):
        return "S1"
    if usage >= 0.45 and (fga >= 14.0 or pts >= 18.0):
        return "S2"
    if usage >= 0.35 or (pts >= 10.0 and fga >= 8.0):
        return "S3"

    # Low-usage pass-first connector
    if passing >= 0.40 and ast >= 4.0:
        return "T3"

    return "S3"


def _pick_core(stats: Dict[str, float], attrs: Dict[str, int], position: str) -> str:
    """Pick 1 core role based on workload, IQ, and usage profile."""
    usg = _sg(stats, "f_usg", 0.0)
    ast_pct = _sg(stats, "f_ast_pct", 0.0)
    ts_pct = _sg(stats, "f_ts_pct", 0.0)
    tov_pct = _sg(stats, "f_tov_pct", 0.0)
    minutes = _sg(stats, "f_pg_pts", 0.0)  # proxy — use actual totals if available
    fg3a = _sg(stats, "f_pg_fg3a", 0.0)
    fg3_pct = _sg(stats, "f_fg3_pct", 0.0)
    assisted2 = _sg(stats, "f_pg_fgm", 0.0)  # approximate

    usage = _n(usg, 12.0, 35.0)
    passing = _n(ast_pct, 5.0, 42.0)
    iq = _n(ts_pct, 0.48, 0.68) * 0.45 + _n(1.0 - _clamp(_n(tov_pct, 8.0, 20.0), 0.0, 1.0), 0.0, 1.0) * 0.35 + passing * 0.20

    is_big = any(p in position.upper() for p in ("C", "PF"))
    is_guard = any(p in position.upper() for p in ("PG", "SG"))

    # High-usage isolation players
    if usage >= 0.65 and _sg(stats, "f_isolation_poss_pct", 0.0) >= 0.10:
        return "ISO"

    # Conductor — elite passers
    if passing >= 0.55 and usage >= 0.40:
        return "CON"

    # Closer — high usage + high IQ
    if usage >= 0.55 and iq >= 0.55:
        return "CLO"

    # Spot-up only — high 3PT, low creation
    if fg3a >= 5.0 and fg3_pct >= 0.36 and usage <= 0.35:
        return "SPT"

    # Microwave — high usage, low minutes
    if usage >= 0.45 and _n(minutes, 350.0, 3000.0) <= 0.45:
        return "MIC"

    # Stability — veteran with high IQ
    if iq >= 0.55 and usage >= 0.30 and usage <= 0.55:
        return "STBLY"

    # Glue guy — moderate defense + IQ
    if _na(attrs, "Defensive Consistency") >= 45 and iq >= 0.45 and usage <= 0.42:
        return "GLUE"

    # Default
    if usage >= 0.30:
        return "ROL"
    return "ROT"


def _pick_scoring(stats: Dict[str, float], attrs: Dict[str, int], position: str) -> str:
    """Pick 1 scoring style role based on shot diet."""
    fg3a = _sg(stats, "f_pg_fg3a", 0.0)
    fg3_pct = _sg(stats, "f_fg3_pct", 0.0)
    fga = _sg(stats, "f_pg_fga", 0.0)
    fg_pct = _sg(stats, "f_fg_pct", 0.0)
    pts = _sg(stats, "f_pg_pts", 0.0)
    usg = _sg(stats, "f_usg", 0.0)
    paint_touches = _sg(stats, "f_paint_touch_pg", 0.0)
    drives = _sg(stats, "f_drives_pg", 0.0)

    is_big = any(p in position.upper() for p in ("C", "PF"))
    is_guard = any(p in position.upper() for p in ("PG", "SG"))

    # Post scorer — bigs with paint touches + post skill
    if is_big and paint_touches >= 4.0 and _na(attrs, "Post Control") >= 50:
        return "PST"

    # Slasher — high drives + dunk/layup ability (check before pull-up)
    if drives >= 8.0 and _na(attrs, "Driving Dunk") >= 55:
        return "SLH"
    if drives >= 6.0 and _na(attrs, "Driving Layup") >= 60 and fg3a < 4.0:
        return "SLH"

    # Catch-and-shoot specialist — high CS attempts, low creation
    cs_fg3a = _sg(stats, "f_cs_fg3a_pg", 0.0)
    if cs_fg3a >= 3.0 and fg3_pct >= 0.36 and _sg(stats, "f_usg", 0.0) <= 0.25:
        return "C&S"

    # 3-point volume + efficiency — must be primarily a shooter, not a slasher
    if fg3a >= 8.0 and fg3_pct >= 0.38 and drives < 6.0:
        return "SHO"
    if fg3a >= 5.0 and fg3_pct >= 0.38 and drives < 5.0:
        return "SHO"
    if fg3a >= 4.0 and fg3_pct >= 0.36 and drives < 4.0:
        return "3L"

    # Pull-up shooter — needs meaningful pull-up volume, not just any creator
    pu_fg3a = _sg(stats, "f_pu_fg3a_pg", 0.0)
    if pu_fg3a >= 3.0 and fg3_pct >= 0.34 and drives < 7.0:
        return "PULL"

    # Mid-range specialist
    mid_attr = _na(attrs, "Mid-Range Shot")
    if mid_attr >= 60 and fg3a < 4.0:
        return "MID"

    # Rim runner
    if is_big and _na(attrs, "Standing Dunk") >= 60:
        return "RR"

    # Finisher
    if drives >= 6.0 and _na(attrs, "Driving Layup") >= 55:
        return "FIN"

    # Fallback
    if fg3a >= 2.0:
        return "3L"
    return "FIN"


def _pick_defense(stats: Dict[str, float], attrs: Dict[str, int], position: str) -> str:
    """Pick 1 defense role based on stl/blk/position profile."""
    stl = _sg(stats, "f_pg_stl", 0.0)
    blk = _sg(stats, "f_pg_blk", 0.0)
    reb = _sg(stats, "f_pg_reb", 0.0)
    deflections = _sg(stats, "f_deflections_pg", 0.0)
    contested = _sg(stats, "f_contested_pg", 0.0)
    boxouts = _sg(stats, "f_boxouts_pg", 0.0)

    is_big = any(p in position.upper() for p in ("C", "PF"))
    is_guard = any(p in position.upper() for p in ("PG", "SG"))

    block_attr = _na(attrs, "Block")
    perim_attr = _na(attrs, "Perimeter Defense")

    # Rim protector — bigs with meaningful BLK + rebounding
    if is_big and blk >= 1.2 and block_attr >= 55:
        if reb >= 8.0:
            return "ANCH"
        return "RIMD"

    # Lockdown perimeter — high STL + contested + good perimeter D attr
    if not is_big and stl >= 1.2 and contested >= 3.0:
        if _na(attrs, "Perimeter Defense") >= 65:
            return "LOCK"
        return "POA"

    # Ball hawk — high deflections + steals
    if stl >= 1.0 and deflections >= 2.0:
        return "BHW"

    # Switchable — decent across the board
    if (stl >= 0.8 or blk >= 0.8) and _na(attrs, "Perimeter Defense") >= 50:
        return "SWI"

    # Glass cleaner — high rebounds + boxouts
    if reb >= 8.0 and boxouts >= 2.0:
        return "GLS"

    # Help defender — high contested shots
    if contested >= 3.0:
        return "HELP"

    # Shot contester
    if contested >= 2.0:
        return "CONTEST"

    # Interceptor
    if deflections >= 1.5 and stl >= 0.8:
        return "INT"

    # Fallback
    return "DISC"


def _pick_fifth(stats: Dict[str, float], attrs: Dict[str, int], position: str,
                used_roles: set) -> str:
    """Pick the 5th role from drive/IQ/utility/specialist sections."""
    drives = _sg(stats, "f_drives_pg", 0.0)
    ast = _sg(stats, "f_pg_ast", 0.0)
    usg = _sg(stats, "f_usg", 0.0)
    fg3a = _sg(stats, "f_pg_fg3a", 0.0)
    paint_touches = _sg(stats, "f_paint_touch_pg", 0.0)
    touches = _sg(stats, "f_touches_pg", 0.0)

    is_big = any(p in position.upper() for p in ("C", "PF"))
    is_guard = any(p in position.upper() for p in ("PG", "SG"))

    usage = _n(usg, 12.0, 35.0)
    passing = _n(_sg(stats, "f_ast_pct", 0.0), 5.0, 42.0)

    # Drive/attack roles
    if drives >= 10.0 and usage >= 0.50 and "BLW" not in used_roles:
        return "BLW"
    if drives >= 8.0 and _na(attrs, "Strength") >= 60 and "PHY" not in used_roles:
        return "PHY"
    if drives >= 6.0 and "CTL" not in used_roles:
        return "CTL"

    # IQ roles
    if ast >= 7.0 and passing >= 0.55 and "VISION" not in used_roles:
        return "VISION"
    if ast >= 5.0 and _sg(stats, "f_tov_pct", 15.0) <= 12.0 and "CALM" not in used_roles:
        return "CALM"
    if usage >= 0.50 and _sg(stats, "f_ts_pct", 0.55) >= 0.58 and "COMPOSE" not in used_roles:
        return "COMPOSE"

    # Specialist roles
    if ast >= 5.0 and touches >= 60.0 and "PNH" not in used_roles:
        return "PNH"
    if usage >= 0.55 and _sg(stats, "f_ts_pct", 0.55) >= 0.58 and "CLM" not in used_roles:
        return "CLM"
    if usage >= 0.45 and passing >= 0.40 and "SCO" not in used_roles:
        return "SCO"
    if fg3a >= 7.0 and _sg(stats, "f_fg3_pct", 0.35) >= 0.38 and usage >= 0.40 and "GRAV" not in used_roles:
        return "GRAV"
    if fg3a >= 4.0 and _sg(stats, "f_cs_fg3a_pg", 0.0) >= 3.0 and "C&S" not in used_roles:
        return "C&S"

    # Utility roles
    if _na(attrs, "Hustle") >= 55 and "HUST" not in used_roles:
        return "HUST"
    if _na(attrs, "Defensive Rebound") >= 55 and _na(attrs, "Offensive Rebound") >= 50 and "REB" not in used_roles:
        return "REB"
    if _na(attrs, "Speed") >= 60 and _na(attrs, "Stamina") >= 60 and "OGM" not in used_roles:
        return "OGM"

    # Fallback
    if "DISCIP" not in used_roles:
        return "DISCIP"
    if "ROT" not in used_roles:
        return "ROT"
    return "ROL"


def _pick_unicorn(stats: Dict[str, float], attrs: Dict[str, int], position: str) -> Optional[str]:
    """Pick a unicorn role for elite players. Returns None if player doesn't qualify."""
    usg = _sg(stats, "f_usg", 0.0)
    ast_pct = _sg(stats, "f_ast_pct", 0.0)
    ts_pct = _sg(stats, "f_ts_pct", 0.0)
    fg3a = _sg(stats, "f_pg_fg3a", 0.0)
    fg3_pct = _sg(stats, "f_fg3_pct", 0.0)
    pts = _sg(stats, "f_pg_pts", 0.0)
    ast = _sg(stats, "f_pg_ast", 0.0)
    reb = _sg(stats, "f_pg_reb", 0.0)
    stl = _sg(stats, "f_pg_stl", 0.0)
    blk = _sg(stats, "f_pg_blk", 0.0)
    drives = _sg(stats, "f_drives_pg", 0.0)

    usage = _n(usg, 12.0, 35.0)
    passing = _n(ast_pct, 5.0, 42.0)
    shooting = _n(fg3_pct, 0.30, 0.45) * 0.40 + _n(fg3a, 0.5, 10.0) * 0.35 + _n(ts_pct, 0.48, 0.68) * 0.25
    defense = _n(stl, 0.3, 3.0) * 0.35 + _n(blk, 0.2, 4.0) * 0.35 + _n(reb, 2.0, 14.0) * 0.30
    iq = _n(ts_pct, 0.48, 0.68) * 0.45 + _n(1.0 - _clamp(_n(_sg(stats, "f_tov_pct", 15.0), 8.0, 20.0), 0.0, 1.0), 0.0, 1.0) * 0.35 + passing * 0.20

    is_big = any(p in position.upper() for p in ("C", "PF"))

    # Score each unicorn type
    scores = {
        "TDH": 0.48 * passing + 0.22 * usage + 0.15 * _n(reb, 4.0, 14.0),
        "PCE": 0.42 * iq + 0.28 * passing + 0.18 * usage,
        "GRV+": 0.56 * shooting + 0.24 * _n(fg3a, 2.0, 10.0) + 0.20 * usage,
        "DSC": 0.66 * defense + 0.20 * _n(blk, 0.2, 4.0) + 0.14 * (1.0 if is_big else 0.0),
        "MME": 0.38 * usage + 0.34 * _n(drives, 2.0, 16.0) + 0.16 * _na(attrs, "Mid-Range Shot") / 100.0 + 0.12 * passing,
        "SCE": 0.42 * usage + 0.36 * _n(usg, 20.0, 36.0) + 0.22 * shooting,
        "OFF+": 0.38 * usage + 0.30 * iq + 0.20 * passing + 0.12 * shooting,
        "3LV+": 0.40 * shooting + 0.30 * _na(attrs, "Mid-Range Shot") / 100.0 + 0.30 * _n(_sg(stats, "f_pg_fgm", 0.0), 3.0, 12.0),
        "CLX": 0.42 * usage + 0.34 * iq + 0.24 * _n(_sg(stats, "f_ft_pct", 0.75), 0.58, 0.93),
        "VRE": 0.34 * usage + 0.22 * passing + 0.22 * shooting + 0.22 * defense,
    }

    # Minimum thresholds — only truly elite players qualify
    thresholds = {
        "TDH": 0.62,
        "PCE": 0.60,
        "GRV+": 0.58,
        "DSC": 0.58,
        "MME": 0.58,
        "SCE": 0.60,
        "OFF+": 0.56,
        "3LV+": 0.58,
        "CLX": 0.58,
        "VRE": 0.52,
    }

    # Eligibility gates
    if pts < 15.0 and ast < 4.0 and reb < 5.0:
        return None

    best_code = None
    best_score = -1.0
    for code, score in scores.items():
        threshold = thresholds.get(code, 0.56)
        if score >= threshold and score > best_score:
            best_score = score
            best_code = code

    return best_code


def assign_roles(
    attrs: Dict[str, int],
    stats: Dict[str, float],
    position: str = "SG",
) -> Tuple[List[str], Optional[str]]:
    """Assign exactly 5 roles + optional 6th unicorn role.

    Returns:
        (roles, unicorn_role) where roles has exactly 5 codes
        and unicorn_role is either a code or None.
    """
    # Apply outlier corrections BEFORE role assignment
    # Catches elite statistical anomalies that ML models regress toward mean
    attrs = _apply_outlier_corrections(attrs, stats, position)

    used = set()

    # 1. Hierarchy role
    hier = _pick_hierarchy(stats, attrs, position)
    roles = [hier]
    used.add(hier)

    # 2. Core role
    core = _pick_core(stats, attrs, position)
    if core not in used:
        roles.append(core)
        used.add(core)
    else:
        # Fallback if core duplicates hierarchy
        roles.append("ROL")
        used.add("ROL")

    # 3. Scoring role
    scoring = _pick_scoring(stats, attrs, position)
    if scoring not in used:
        roles.append(scoring)
        used.add(scoring)
    else:
        roles.append("FIN")
        used.add("FIN")

    # 4. Defense role
    defense = _pick_defense(stats, attrs, position)
    if defense not in used:
        roles.append(defense)
        used.add(defense)
    else:
        roles.append("HELP")
        used.add("HELP")

    # 5. Fifth role (drive/IQ/utility/specialist)
    fifth = _pick_fifth(stats, attrs, position, used)
    if fifth not in used:
        roles.append(fifth)
    else:
        # Fallback chain
        for fb in ["DISCIP", "ROT", "HUST", "GLUE", "CTL"]:
            if fb not in used:
                roles.append(fb)
                break
        else:
            roles.append("ROL")

    # Ensure exactly 5
    roles = roles[:5]

    # Apply contradiction/redundancy cleanup
    roles = _apply_contradictions(roles)

    # Pad back to 5 if contradictions removed any
    fallbacks = ["DISCIP", "ROT", "HUST", "GLUE", "CTL", "ROL", "STBLY"]
    for fb in fallbacks:
        if len(roles) >= 5:
            break
        if fb not in roles:
            roles.append(fb)
    roles = roles[:5]

    # 6. Unicorn role (only for elite players)
    unicorn = _pick_unicorn(stats, attrs, position)
    if unicorn and unicorn in roles:
        unicorn = None  # Don't double-count

    return roles, unicorn, attrs


def _apply_outlier_corrections(
    attrs: Dict[str, int],
    stats: Dict[str, float],
    position: str,
) -> Dict[str, int]:
    """Correct ML predictions for statistical outliers.

    ML models regress extreme players toward the mean. This function
    detects elite statistical anomalies and bumps attributes directly.
    """
    corrected = dict(attrs)

    ast_pct = _sg(stats, "f_ast_pct", 0.0)
    usg = _sg(stats, "f_usg", 0.0)
    pts = _sg(stats, "f_pg_pts", 0.0)
    ast = _sg(stats, "f_pg_ast", 0.0)
    reb = _sg(stats, "f_pg_reb", 0.0)
    fg3a = _sg(stats, "f_pg_fg3a", 0.0)
    fg3_pct = _sg(stats, "f_fg3_pct", 0.0)
    stl = _sg(stats, "f_pg_stl", 0.0)
    blk = _sg(stats, "f_pg_blk", 0.0)
    drives = _sg(stats, "f_drives_pg", 0.0)
    touches = _sg(stats, "f_touches_pg", 0.0)
    pot_ast = _sg(stats, "f_pot_ast_pg", 0.0)

    is_big = any(p in position.upper() for p in ("C", "PF"))
    is_guard = any(p in position.upper() for p in ("PG", "SG"))

    # Elite passing big (Jokic archetype) — AST% > 35 for a center/PF
    if is_big and ast_pct >= 35.0:
        pass_bonus = min(20, int((ast_pct - 30.0) * 1.2))
        corrected["Pass Vision"] = min(95, corrected.get("Pass Vision", 25) + pass_bonus)
        corrected["Pass IQ"] = min(95, corrected.get("Pass IQ", 25) + pass_bonus)
        corrected["Pass Accuracy"] = min(95, corrected.get("Pass Accuracy", 25) + pass_bonus)

    # Elite passing guard/wing (LeBron/Harden/Doncic) — AST% > 30 with high usage
    elif (not is_big) and ast_pct >= 30.0 and usg >= 25.0:
        pass_bonus = min(12, int((ast_pct - 30.0) * 0.8))
        corrected["Pass Vision"] = min(95, corrected.get("Pass Vision", 25) + pass_bonus)
        corrected["Pass IQ"] = min(95, corrected.get("Pass IQ", 25) + max(2, pass_bonus - 2))
        corrected["Pass Accuracy"] = min(95, corrected.get("Pass Accuracy", 25) + max(2, pass_bonus - 3))

    # Elite shot creator (Curry/Lillard) — high FG3A + efficiency + usage
    if fg3a >= 10.0 and fg3_pct >= 0.38 and usg >= 28.0:
        corrected["Three-Point Shot"] = min(95, corrected.get("Three-Point Shot", 25) + 5)
        corrected["Shot IQ"] = min(95, corrected.get("Shot IQ", 25) + 3)

    # Elite rim protector (Gobert/Wembanyama) — BLK > 3.0
    if blk >= 3.0:
        corrected["Block"] = min(95, corrected.get("Block", 25) + 8)
        corrected["Interior Defense"] = min(95, corrected.get("Interior Defense", 25) + 5)

    # Elite perimeter stopper — STL > 2.5
    if stl >= 2.5:
        corrected["Steal"] = min(95, corrected.get("Steal", 25) + 5)
        corrected["Perimeter Defense"] = min(95, corrected.get("Perimeter Defense", 25) + 3)

    # Elite slasher — drives > 15 with high efficiency
    if drives >= 15.0 and usg >= 25.0:
        corrected["Driving Layup"] = min(95, corrected.get("Driving Layup", 25) + 4)
        corrected["Ball Handle"] = min(95, corrected.get("Ball Handle", 25) + 3)

    return corrected


def _apply_contradictions(roles: List[str]) -> List[str]:
    """Remove contradictory/redundant roles, keeping the first."""
    cleaned = []
    for role in roles:
        if role not in cleaned:
            cleaned.append(role)

    for group in ROLE_REDUNDANCY_GROUPS:
        seen = [r for r in cleaned if r in group]
        if len(seen) > 1:
            keeper = seen[0]
            cleaned = [r for r in cleaned if r not in group or r == keeper]

    for pair in ROLE_CONTRADICTIONS:
        seen = [r for r in cleaned if r in pair]
        if len(seen) > 1:
            keeper = seen[0]
            cleaned = [r for r in cleaned if r not in pair or r == keeper]

    return cleaned


def apply_role_boosts(
    attrs: Dict[str, int],
    roles: List[str],
    unicorn_role: Optional[str] = None,
) -> Dict[str, int]:
    """Apply attribute boosts from roles to the ML-predicted attributes.

    Each role adds its defined boosts. Unicorn role adds bigger boosts.
    Final values are clamped to 25-99.
    """
    boosted = dict(attrs)

    for role in roles:
        boost = ROLE_BOOSTS.get(role, {})
        for attr_name, delta in boost.items():
            if attr_name in boosted:
                boosted[attr_name] = min(95, boosted[attr_name] + delta)

    # Unicorn boosts are larger
    if unicorn_role:
        boost = ROLE_BOOSTS.get(unicorn_role, {})
        for attr_name, delta in boost.items():
            if attr_name in boosted:
                boosted[attr_name] = min(95, boosted[attr_name] + delta)

    return boosted
