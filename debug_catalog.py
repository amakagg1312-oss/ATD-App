"""Debug badge catalog parsing."""
import sys, os, re
sys.path.insert(0, '.')

badges_txt_path = 'Badges/NBA 2K26 Badges.txt'
current_section = "Off-Ball"
pending_badge_name = ""
sections = {"Finishing": [], "Shooting": [], "Playmaking": [], "Defense": [], "Post": [], "Off-Ball": []}
seen_names = set()

def clean_badge_name(raw_name):
    name = str(raw_name or "").strip()
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
    return name

with open(badges_txt_path, "r", encoding="utf-8", errors="ignore") as f:
    for i, raw_line in enumerate(f, 1):
        line = str(raw_line or "").strip()
        if not line:
            continue
        upper = line.upper()
        lower = line.lower()
        
        # Check section triggers
        triggered = None
        if "FINISHING" in upper:
            triggered = "Finishing"
        if "SHOOTING" in upper:
            triggered = "Shooting"
        if "PLAYMAKING" in upper:
            triggered = "Playmaking"
        if "DEFENSE" in upper or "REBOUNDING" in upper:
            triggered = "Defense"
        if "POST / BIG MAN" in upper:
            triggered = "Post"
        if "OFF-BALL" in upper:
            triggered = "Off-Ball"
        if "NON-STANDARD" in upper:
            triggered = "NON-STANDARD"
        
        if triggered:
            print(f"  LINE {i}: '{line}' -> SECTION TRIGGER: {triggered}")
            if triggered == "NON-STANDARD":
                current_section = "Off-Ball"
            else:
                current_section = triggered
            pending_badge_name = ""
            continue
            
        if lower.startswith("these are not official"):
            continue
        if "->" in line or "→" in line:
            if pending_badge_name:
                desc = line.replace("->", "").replace("→", "").strip()
                cleaned_name = clean_badge_name(pending_badge_name)
                if cleaned_name and cleaned_name.lower() not in seen_names:
                    sections.setdefault(current_section, []).append({"name": cleaned_name, "description": desc})
                    seen_names.add(cleaned_name.lower())
                    print(f"  LINE {i}: Added '{cleaned_name}' to '{current_section}'")
                pending_badge_name = ""
            continue
        if line.startswith("🏀") or line.startswith("🎯") or line.startswith("🛡️") or line.startswith("⚠️"):
            continue
        if "work ethic" in lower or "marketability" in lower:
            continue
        if line.endswith(":") and ("badge" in lower or "official" in lower):
            continue
        pending_badge_name = line

print("\n=== CATALOG ===")
for s, bl in sections.items():
    print(f"{s} ({len(bl)}): {[b['name'] for b in bl]}")
