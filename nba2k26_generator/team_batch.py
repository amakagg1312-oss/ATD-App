"""Minimal batch team profile generator - avoids slow module-level imports.

Usage:
    python team_batch.py <players_json> <season> <project_root> <db_dir> <roles_dir>

Outputs one JSON object per line (NDJSON) to stdout:
    {"type": "progress", "completed": N, "total": M, "player": "..."}
    {"type": "player", "ok": true, "player": "...", "profile": {...}}
    {"type": "player", "ok": false, "player": "...", "error": "..."}
    {"type": "done", "total": N, "success": M, "failed": K}
"""

import json
import os
import re
import sys
import unicodedata
from urllib.parse import quote

# ── Arguments ──────────────────────────────────────────────────────────────
if len(sys.argv) < 6:
    print(json.dumps({"type": "error", "error": "Missing arguments"}), flush=True)
    sys.exit(1)

players = json.loads(sys.argv[1])
season = sys.argv[2].strip()
project_root = sys.argv[3]
db_dir = sys.argv[4]
roles_dir = sys.argv[5]
badges_txt = os.path.join(project_root, "Badges", "NBA 2K26 Badges.txt")

# ── Path setup ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(project_root, "nba2k26_generator"))


# ── Minimal helper functions (no external deps) ────────────────────────────
def sf(v, default=0.0):
    """Safe float conversion."""
    try:
        f = float(str(v or "").strip())
        return f if f == f else default
    except Exception:
        return default


def normalize_key(name):
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def season_year(label):
    m = re.match(r"^(\d{4})", str(label or "").strip())
    return int(m.group(1)) if m else -1


def first_non_empty(*values):
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() not in {"none", "nan", "na", "n/a"}:
            return s
    return ""


def repair_text(value):
    """Fix mojibake text encoding issues."""
    text = str(value or "")
    if not text:
        return ""

    def likely_mojibake(s):
        hints = ("\u00c3", "\u00c2", "\u00e2", "\u00c4", "\u00c5", "\u00d0", "\u00f0", "\u2021")
        return any(h in s for h in hints) or any(0x80 <= ord(ch) <= 0x9F for ch in s)

    def to_bytes(s):
        out = bytearray()
        for ch in s:
            code = ord(ch)
            if code <= 0xFF:
                out.append(code)
                continue
            try:
                raw = ch.encode("cp1252")
            except Exception:
                return None
            if len(raw) != 1:
                return None
            out.extend(raw)
        return bytes(out)

    fixed = text
    for _ in range(2):
        if not likely_mojibake(fixed):
            break
        raw = to_bytes(fixed)
        if not raw:
            break
        try:
            decoded = raw.decode("utf-8")
        except Exception:
            break
        if not decoded or decoded == fixed:
            break
        fixed = decoded
    return fixed or text


def normalize_name(name):
    """Normalize player name for matching."""
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def format_height(row):
    explicit = first_non_empty(row.get("height"), row.get("height_without_shoes"))
    if explicit:
        return explicit
    inches_raw = first_non_empty(row.get("player_info_ht_in_in"))
    if not inches_raw:
        return "NA"
    total = int(sf(inches_raw, 0.0))
    if total <= 0:
        return "NA"
    feet = total // 12
    inches = total % 12
    return f"{feet}'{inches}\""


def build_headshot_url(row):
    nba_id = first_non_empty(row.get("player_id"))
    if nba_id and str(nba_id).strip().isdigit():
        return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{str(nba_id).strip()}.png"
    espn_id = first_non_empty(row.get("espn_id"), row.get("espn_player_id"), row.get("player_info_espn_id"))
    if espn_id and str(espn_id).isdigit():
        return f"https://a.espncdn.com/i/headshots/nba/players/full/{espn_id}.png"
    return ""


def build_team_logo_url(row):
    tid = first_non_empty(row.get("team_id"))
    if tid and str(tid).strip().isdigit():
        return f"https://cdn.nba.com/logos/nba/{str(tid).strip()}/primary/L/logo.svg"
    return ""


def find_action_photo(row, project_root):
    name = repair_text(row.get("player_name", "")).strip()
    if not name:
        return ""
    photos_dir = os.path.join(project_root, "Player Photos")
    if not os.path.isdir(photos_dir):
        return ""
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = os.path.join(photos_dir, name + ext)
        if os.path.isfile(candidate):
            return candidate

    def strip_accents(s):
        nfkd = unicodedata.normalize("NFKD", s)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    name_lower = strip_accents(name).lower()
    try:
        for f in os.listdir(photos_dir):
            stem, ext = os.path.splitext(f)
            if ext.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                if strip_accents(stem).lower() == name_lower:
                    return os.path.join(photos_dir, f)
    except Exception:
        pass
    return ""


def stat_snapshot(r):
    if not r:
        return {"pts": 0.0, "reb": 0.0, "ast": 0.0, "stl": 0.0, "blk": 0.0, "fgPct": 0.0, "fg3Pct": 0.0, "gp": 0}
    g = max(sf(r.get("per_game_g", r.get("advanced_g", r.get("totals_g", 0.0)))), 1.0)
    pts = sf(r.get("per_game_pts_per_game", r.get("per_game_pts", sf(r.get("totals_pts", 0.0)) / g)))
    reb = sf(r.get("per_game_reb_per_game", r.get("per_game_trb", sf(r.get("totals_trb", 0.0)) / g)))
    ast = sf(r.get("per_game_ast_per_game", r.get("per_game_ast", sf(r.get("totals_ast", 0.0)) / g)))
    stl = sf(r.get("per_game_stl_per_game", r.get("per_game_stl", sf(r.get("totals_stl", 0.0)) / g)))
    blk = sf(r.get("per_game_blk_per_game", r.get("per_game_blk", sf(r.get("totals_blk", 0.0)) / g)))
    fg_raw = first_non_empty(
        r.get("per_game_fg_percent"), r.get("per_game_fg_pct"), r.get("shooting_fg_percent"),
        r.get("shooting_fg_pct"), r.get("totals_fg_percent"), r.get("totals_fg_pct"),
        r.get("fg_percent"), r.get("fg_pct"),
    )
    fg = sf(fg_raw, None) if fg_raw else None
    if fg is None:
        fgm = sf(r.get("totals_fg", 0.0))
        fga = max(sf(r.get("totals_fga", 0.0)), 1.0)
        fg = fgm / fga
    fg3_raw = first_non_empty(
        r.get("per_game_x3p_percent"), r.get("per_game_fg3_pct"), r.get("shooting_fg_percent_from_x3p_range"),
        r.get("shooting_fg3_pct"), r.get("totals_x3p_percent"), r.get("totals_fg3_pct"),
        r.get("fg3_percent"), r.get("fg3_pct"),
    )
    fg3 = sf(fg3_raw, None) if fg3_raw else None
    if fg3 is None:
        fg3m = sf(r.get("totals_fg3", 0.0))
        fg3a = max(sf(r.get("totals_fg3a", 0.0)), 1.0)
        fg3 = fg3m / fg3a
    return {
        "pts": round(pts, 1), "reb": round(reb, 1), "ast": round(ast, 1),
        "stl": round(stl, 1), "blk": round(blk, 1),
        "fgPct": round(fg, 3), "fg3Pct": round(fg3, 3),
        "gp": int(sf(r.get("per_game_g", r.get("advanced_g", r.get("totals_g", 0.0))))),
    }


def preferred_row(rows):
    if not rows:
        return None
    for r in rows:
        if str(r.get("team_abbr", "")).upper() == "2TM":
            return r
    return max(rows, key=lambda r: sf(r.get("totals_mp", 0.0)))


# ── Load data and modules ──────────────────────────────────────────────────
print(json.dumps({"type": "progress", "status": "loading_data", "completed": 0, "total": len(players)}), flush=True)

# Import generator modules (this does the heavy lifting)
from generator_cli import (
    load_rows,
    compute_tendencies,
    compute_attribute_family_averages,
    compute_overall_rating,
    compute_badge_groups,
    ATTRIBUTE_FAMILIES,
    THREE_POINT_RULES,
    MID_POST_RULES,
    DRIBBLE_RULES,
    DEFENSE_RULES,
)
from generator_cli_ml import compute_attributes_ml

print(json.dumps({"type": "progress", "status": "loading_csv", "completed": 0, "total": len(players)}), flush=True)

# Load rows (handles subdirectories automatically)
rows = load_rows(db_dir)

# Build name index for fast lookups
name_index = {}
for r in rows:
    name = normalize_name(repair_text(r.get("player_name", "")))
    if name:
        name_index.setdefault(name, []).append(r)


def tendency_group(name):
    if name in THREE_POINT_RULES:
        return "Shooting"
    if name in MID_POST_RULES:
        return "Finishing"
    if name in DRIBBLE_RULES:
        return "Playmaking"
    if name in DEFENSE_RULES:
        return "Defense"
    lower = str(name).lower()
    if "dunk" in lower or "layup" in lower or "post" in lower:
        return "Finishing"
    if "pass" in lower or "iso" in lower or "pick" in lower or "dribble" in lower:
        return "Playmaking"
    if "three" in lower or "shot" in lower or "jumper" in lower:
        return "Shooting"
    if "defense" in lower or "contest" in lower or "steal" in lower or "block" in lower:
        return "Defense"
    return "General"


# ── Attribute and tendency group definitions ───────────────────────────────
attribute_group_order = [
    ("Finishing", ["Driving Layup", "Standing Dunk", "Driving Dunk", "Close Shot"]),
    ("Shooting", ["Mid-Range Shot", "Three-Point Shot", "Free Throw", "Shot IQ"]),
    ("Post Game", ["Post Hook", "Post Fade", "Post Control"]),
    ("Playmaking", ["Draw Foul", "Ball Handle", "Speed with Ball", "Hands", "Pass Accuracy", "Pass IQ", "Pass Vision"]),
    ("Mental", ["Offensive Consistency", "Defensive Consistency"]),
    ("Defense", ["Interior Defense", "Perimeter Defense", "Steal", "Block", "Help Defense IQ", "Pass Perception"]),
    ("Rebounding", ["Offensive Rebound", "Defensive Rebound"]),
    ("Physical", ["Speed", "Agility", "Strength", "Vertical", "Stamina"]),
    ("Meta", ["Intangibles", "Hustle", "Overall Durability", "Potential"]),
]

tendency_aliases = {
    "step_through_shot": ["step_through"], "shot_under_basket": ["shot_under"],
    "touches": ["touch"], "shot_mid_range": ["shot_mid"], "shot_three": ["shot_3"],
    "spot_up_shot_mid_range": ["spot_up_mid", "spot_up_shot_mid"], "spot_up_shot_three": ["spot_up_3"],
    "off_screen_shot_mid_range": ["off_screen_mid", "off_screen_shot_mid"], "off_screen_shot_three": ["off_screen_3"],
    "contested_jumper_mid_range": ["contested_mid"], "contested_jumper_three": ["contested_3"],
    "stepback_jumper_mid_range": ["step_back_mid"], "stepback_jumper_three": ["step_back_3"],
    "drive_pull_up_mid_range": ["dribble_pull_up_mid", "drive_pull_up_mid"],
    "drive_pull_up_three": ["dribble_pull_up_3", "drive_pull_up_3"],
    "driving_layup": ["drive"], "hop_step_layup": ["hop_step"], "euro_step_layup": ["eurostep"],
    "transition_pull_up_three": ["transition_pull_up_3"], "transition_spot_up": ["spot_vs_cut"],
    "driving_crossover": ["drive_crossover"], "driving_spin": ["drive_spin"],
    "driving_step_back": ["drive_step_back"], "driving_half_spin": ["drive_half_spin"],
    "driving_double_crossover": ["drive_double_crossover"], "driving_behind_the_back": ["drive_behind_back"],
    "driving_dribble_hesitation": ["drive_hesitation"], "driving_in_and_out": ["drive_in_out"],
    "attack_strong_on_drive": ["attack_strong_drive"], "setup_with_sizeup": ["set_up_size_up"],
    "setup_with_hesitation": ["set_up_hesitation"], "dish_to_open_man": ["dish"],
    "iso_vs_elite_defender": ["iso_vs_elite"], "iso_vs_good_defender": ["iso_vs_good"],
    "iso_vs_average_defender": ["iso_vs_average"], "iso_vs_poor_defender": ["iso_vs_poor"],
    "post_shimmy_shot": ["post_shimmy"], "post_aggressive_backdown": ["post_aggressive_back_down"],
    "post_step_back_shot": ["post_step_back"], "post_up_and_under": ["post_up_under", "post_up_&_under"],
    "post_drop_step": ["post_drop_step"], "post_hop_step": ["post_hop_shot"],
    "block_shot": ["block"], "on_ball_steal": ["on_ball_steal"],
}

tendency_group_order = [
    ("finishing", ["Step Through Shot", "Shot Under Basket", "Shot Close", "Use Glass", "Driving Layup", "Standing Dunk",
                   "Driving Dunk", "Flashy Dunk", "Alley-Oop", "Putback", "Crash", "Spin Layup", "Hop Step Layup",
                   "Euro Step Layup", "Floater"]),
    ("sub_zone", ["Shot Close Left", "Shot Close Middle", "Shot Close Right", "Shot Mid Left", "Shot Mid Left-Center",
                  "Shot Mid Center", "Shot Mid Right-Center", "Shot Mid Right", "Shot Three Left",
                  "Shot Three Left-Center", "Shot Three Center", "Shot Three Right-Center", "Shot Three Right"]),
    ("shooting", ["Shot Mid-Range", "Spot Up Shot Mid-Range", "Off Screen Shot Mid-Range", "Shot Three",
                  "Spot Up Shot Three", "Off Screen Shot Three", "Contested Jumper Three", "Contested Jumper Mid-Range",
                  "Stepback Jumper Three", "Stepback Jumper Mid-Range", "Spin Jumper", "Transition Pull Up Three",
                  "Drive Pull Up Three", "Drive Pull Up Mid-Range"]),
    ("triple_threat", ["Triple Threat Pump Fake", "Triple Threat Jab Step", "Triple Threat Idle", "Triple Threat Shoot"]),
    ("dribble_setup", ["Setup With Sizeup", "Setup With Hesitation", "No Setup Dribble"]),
    ("driving", ["Drive", "Spot Up Drive", "Off Screen Drive", "Drive Right", "Attack Strong On Drive"]),
    ("dribble_moves", ["Driving Crossover", "Driving Spin", "Driving Step Back", "Driving Half Spin",
                       "Driving Double Crossover", "Driving Behind The Back", "Driving Dribble Hesitation",
                       "Driving In And Out", "No Driving Dribble Move"]),
    ("passing", ["Dish To Open Man", "Flashy Pass", "Alley-Oop Pass"]),
    ("post", ["Post Up", "Post Shimmy Shot", "Post Face Up", "Post Back Down", "Post Aggressive Backdown",
              "Shoot From Post", "Post Hook Left", "Post Hook Right", "Post Fade Left", "Post Fade Right",
              "Post Up And Under", "Post Hop Shot", "Post Step Back Shot", "Post Drive", "Post Spin",
              "Post Drop Step", "Post Hop Step"]),
    ("core", ["Shot", "Touches", "Play Discipline"]),
    ("playstyle", ["Roll vs. Pop", "Transition Spot Up"]),
    ("isolation", ["Iso vs. Elite Defender", "Iso vs. Good Defender", "Iso vs. Average Defender", "Iso vs. Poor Defender"]),
    ("defense", ["Pass Interception", "Take Charge", "On-Ball Steal", "Contest Shot", "Block Shot"]),
    ("physical", ["Foul", "Hard Foul"]),
]


def resolve_tendency(name, tendency_by_name, tendency_by_norm):
    t = tendency_by_name.get(name)
    if t:
        return t
    norm = normalize_key(name)
    t = tendency_by_norm.get(norm)
    if t:
        return t
    for alias in tendency_aliases.get(norm, []):
        t = tendency_by_norm.get(alias)
        if t:
            return t
    return None


# ── Process each player ────────────────────────────────────────────────────
success_count = 0
fail_count = 0

for idx, player_name in enumerate(players):
    print(json.dumps({
        "type": "progress",
        "status": "generating",
        "completed": idx,
        "total": len(players),
        "player": player_name,
    }), flush=True)

    try:
        # Find player row
        target_name = normalize_name(player_name)
        target_season = season.strip().lower()

        season_matches = []
        for r in name_index.get(target_name, []):
            if str(r.get("season_label", "")).strip().lower() == target_season:
                season_matches.append(r)

        row = preferred_row(season_matches)

        # Fallback to previous season for 2025-26
        if row is None and season_year(target_season) == 2025:
            fallback_rows = []
            for r in name_index.get(target_name, []):
                if season_year(r.get("season_label", "")) == 2024:
                    fallback_rows.append(r)
            row = preferred_row(fallback_rows)

        if row is None:
            raise ValueError(f"No data found for '{player_name}' in season '{season}'")

        # Get player info
        player_name_clean = normalize_name(repair_text(row.get("player_name", "")))
        current_year = season_year(row.get("season_label", ""))

        # Find previous season row
        all_player_rows = name_index.get(player_name_clean, [])
        prev_rows = [r for r in all_player_rows if season_year(r.get("season_label", "")) == current_year - 1]
        prev_row = preferred_row(prev_rows)

        # Use previous season stats for source if 2025-26
        source_row = row
        if current_year == 2025 and prev_row is not None:
            source_row = prev_row

        # Compute stats
        current_snapshot = stat_snapshot(row)
        previous_snapshot = stat_snapshot(prev_row)

        career_rows = [r for r in all_player_rows if season_year(r.get("season_label", "")) <= current_year]
        career_total_g = 0.0
        career_acc = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "stl": 0.0, "blk": 0.0, "fgPct": 0.0, "fg3Pct": 0.0}
        for cr in career_rows:
            s = stat_snapshot(cr)
            g = max(float(s.get("gp", 0)), 1.0)
            career_total_g += g
            for k in career_acc:
                career_acc[k] += float(s.get(k, 0.0)) * g
        career_snapshot = {
            k: round((career_acc[k] / career_total_g) if career_total_g > 0 else 0.0, 3 if "Pct" in k else 1)
            for k in career_acc
        }
        career_snapshot["gp"] = int(round(career_total_g))

        # Compute tendencies, attributes, badges
        tendency_results = compute_tendencies(source_row)
        source_row["season_label"] = season  # Force season for committee correction
        ml_result = compute_attributes_ml(source_row, tendency_results, roles_dir, rows)

        attrs = ml_result.get("attributes", {})
        roles = ml_result.get("roles", [])
        ovr = ml_result.get("ovr", 75)

        family_scores = compute_attribute_family_averages(attrs)
        family_scores = {k: int(v) for k, v in family_scores.items()}

        badge_groups = compute_badge_groups(source_row, attrs, tendency_results, family_scores, ovr, badges_txt)

        # Strengths/weaknesses
        sorted_attrs = sorted(attrs.items(), key=lambda kv: kv[1], reverse=True)
        strengths = [k for k, _ in sorted_attrs[:6]]
        weaknesses = [k for k, _ in sorted(attrs.items(), key=lambda kv: kv[1])[:6]]

        # Build attribute groups
        attribute_groups = {}
        for family_name, names in attribute_group_order:
            attribute_groups[family_name] = [
                {"key": normalize_key(n), "name": n, "value": int(attrs.get(n, 0))}
                for n in names if n in attrs
            ]

        # Build tendency groups
        tendency_by_name = {t.name: t for t in tendency_results}
        tendency_by_norm = {normalize_key(t.name): t for t in tendency_results}

        tendency_groups = {}
        for group_name, names in tendency_group_order:
            grp_rows = []
            for n in names:
                t = resolve_tendency(n, tendency_by_name, tendency_by_norm)
                grp_rows.append({
                    "key": normalize_key(n),
                    "name": n,
                    "value": int(t.final) if t else 0,
                    "preCap": float(t.pre_cap) if t else 0.0,
                    "recommendedCap": int(t.recommended_cap) if t else 0,
                    "absoluteCap": int(t.absolute_cap) if t else 0,
                })
            tendency_groups[group_name] = grp_rows

        top_tendencies = sorted(tendency_results, key=lambda x: x.final, reverse=True)
        play_style = [t.name for t in top_tendencies[:3]]

        # Draft info
        draft_year_raw = first_non_empty(row.get("draft_year"), row.get("draft_season"))
        draft_round_raw = first_non_empty(row.get("draft_round"), "")
        draft_number_raw = first_non_empty(row.get("draft_number"), "")
        if draft_year_raw and str(draft_year_raw).strip().lower() not in ("undrafted", "", "none", "nan"):
            draft_str = str(draft_year_raw).strip()
            if draft_round_raw and str(draft_round_raw).strip().lower() not in ("undrafted", "", "none", "nan"):
                draft_str += f" R{draft_round_raw}"
            if draft_number_raw and str(draft_number_raw).strip().lower() not in ("undrafted", "", "none", "nan"):
                draft_str += f" Pick {draft_number_raw}"
            draft_year_num = int(sf(draft_year_raw, current_year))
        else:
            draft_str = "Undrafted" if str(draft_year_raw).strip().lower() == "undrafted" else "NA"
            draft_year_num = current_year
        years_pro = max(0, current_year - draft_year_num) if current_year > 0 else 0

        # Build URLs and info
        height_display = first_non_empty(row.get("height"), "") or format_height(row)
        weight_val = first_non_empty(row.get("weight"), row.get("weight_lbs"), row.get("player_info_wt")) or "NA"
        school_val = first_non_empty(row.get("college"), row.get("school"), row.get("draft_college"),
                                     row.get("player_info_colleges")) or "NA"
        country_val = first_non_empty(row.get("country"), "") or ""

        photo_url = build_headshot_url(row)
        team_logo_url = build_team_logo_url(row)

        action_photo_path = find_action_photo(row, project_root)
        action_photo_url = ""
        if action_photo_path:
            action_photo_url = "player-photo://" + quote(os.path.basename(action_photo_path), safe="")

        nba_pid = str(row.get("player_id", "")).strip()

        # Build payload
        payload = {
            "info": {
                "name": repair_text(row.get("player_name", "")),
                "team": str(row.get("team_abbr", "")),
                "position": str(row.get("position", row.get("pos", ""))),
                "season": str(row.get("season_label", "")),
                "age": float(row.get("age", 0) or 0),
                "height": height_display,
                "weight": weight_val,
                "yearsPro": int(sf(row.get("experience", years_pro))),
                "draft": draft_str,
                "school": school_val,
                "country": country_val,
                "photoUrl": photo_url,
                "teamLogoUrl": team_logo_url,
                "actionPhotoUrl": action_photo_url,
                "nbaPlayerId": nba_pid,
            },
            "ovr": ovr,
            "role": roles[0] if roles else "Core",
            "archetype": roles[0] if roles else "Core",
            "archetypes": roles,
            "usage": roles,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "familyScores": family_scores,
            "attributes": {normalize_key(k): int(v) for k, v in attrs.items()},
            "attributeGroups": attribute_groups,
            "tendencyGroups": tendency_groups,
            "badgeGroups": badge_groups,
            "playStylePriorities": play_style,
            "statBlocks": {"current": current_snapshot, "previous": previous_snapshot, "career": career_snapshot},
        }

        print(json.dumps({"type": "player", "ok": True, "player": player_name, "profile": payload}), flush=True)
        success_count += 1

    except Exception as e:
        print(json.dumps({"type": "player", "ok": False, "player": player_name, "error": str(e)}), flush=True)
        fail_count += 1

print(json.dumps({"type": "done", "total": len(players), "success": success_count, "failed": fail_count}), flush=True)
