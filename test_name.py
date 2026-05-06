import csv, os, unicodedata, re

def normalize_name(name):
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()

def repair_text(value):
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

# Read the traditional CSV
csv_path = r'D:\project\NBA Site data\2024-25\player_traditional_2024-25_regular_season.csv'
with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row.get('PLAYER_NAME', '')
        if 'lebron' in name.lower():
            print(f'Raw name: {repr(name)}')
            repaired = repair_text(name)
            print(f'Repaired: {repr(repaired)}')
            normalized = normalize_name(repaired)
            print(f'Normalized: {repr(normalized)}')
            print(f'Target: {repr(normalize_name("LeBron James"))}')
            break
