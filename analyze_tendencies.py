import subprocess
import json
import sys

result = subprocess.run(
    [
        sys.executable, "-m", "nba2k26_generator.generator_cli",
        "--player", "Stephen Curry",
        "--season", "2025-26",
        "--json",
    ],
    capture_output=True,
    text=True,
    cwd=r"D:\project",
)

if result.returncode != 0:
    print("STDERR:", result.stderr)
    sys.exit(1)

output = json.loads(result.stdout)
profile = output["profile"]

tendency_groups = profile.get("tendencyGroups", {})

total = 0
zero_tendencies = []

for group_name, tendencies in tendency_groups.items():
    for t in tendencies:
        total += 1
        if t["value"] == 0:
            zero_tendencies.append({
                "group": group_name,
                "name": t["name"],
                "value": t["value"],
                "preCap": t["preCap"],
                "recommendedCap": t["recommendedCap"],
                "absoluteCap": t["absoluteCap"],
            })

print(f"Total tendencies: {total}")
print(f"Zero-value tendencies: {len(zero_tendencies)}")
print()

if zero_tendencies:
    print("=== ZERO-VALUE TENDENCIES ===")
    for z in zero_tendencies:
        print(f"  Group: {z['group']}")
        print(f"  Name:  {z['name']}")
        print(f"  Value: {z['value']}")
        print(f"  preCap: {z['preCap']}")
        print(f"  recommendedCap: {z['recommendedCap']}")
        print(f"  absoluteCap: {z['absoluteCap']}")
        print()

print("=== RAW TENDENCY RESULTS (from compute_tendencies) ===")
print(json.dumps(tendency_groups, indent=2))
