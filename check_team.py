import json
with open(r"D:\project\nba2k26_generator\2k26_offsets.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Player size: {data['game_info']['playerSize']}")
print(f"Team size: {data['game_info']['teamSize']}")
print(f"Staff size: {data['game_info']['staffSize']}")
print(f"Stadium size: {data['game_info']['stadiumSize']}")
print()

# Check team base pointer
print(f"Team base pointer: {data['base_pointers']['Team']}")
print()

# Search for team-related offsets
for offset in data["offsets"]:
    name = offset.get("name", "")
    if any(kw in name.lower() for kw in ["team", "roster", "coach", "playbook", "offense", "defense", "strategy", "formation", "set"]):
        hex_val = offset.get("hex", "N/A")
        start = offset.get("startBit", "N/A")
        print(f"{offset['category']:20} {name:40} addr={offset['address']:>5} ({hex_val}) len={offset['length']} startBit={start}")
