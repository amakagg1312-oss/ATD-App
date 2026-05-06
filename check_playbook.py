import json
with open(r"D:\project\nba2k26_generator\2k26_offsets.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Search for playbook-related offsets
categories = set()
for offset in data["offsets"]:
    cat = offset["category"]
    categories.add(cat)
    if "playbook" in offset["name"].lower() or "play" in offset["name"].lower() or "offense" in offset["name"].lower() or "defense" in offset["name"].lower() or "strategy" in offset["name"].lower():
        print(f"{offset['category']:20} {offset['name']:40} addr={offset['address']:>5} ({offset['hex']}) len={offset['length']} startBit={offset.get('startBit', 'N/A')}")

print(f"\nAll categories: {sorted(categories)}")
