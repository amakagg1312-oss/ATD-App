import subprocess
import json
import sys

players = ["LeBron James", "Anthony Davis"]
season = "2024-25"
project_root = r"D:\project"
db_dir = r"D:\project\NBA Site data"
roles_dir = r"D:\project\Player Roles"

batch_script = r"D:\project\nba2k26_generator\team_batch.py"

result = subprocess.run(
    [r"D:\project\.venv\Scripts\python.exe", batch_script, json.dumps(players), season, project_root, db_dir, roles_dir],
    capture_output=True,
    text=True,
    timeout=300,
    cwd=project_root,
)

print("STDOUT:")
for line in result.stdout.strip().split("\n"):
    try:
        obj = json.loads(line)
        if obj.get("type") == "player" and obj.get("ok"):
            print(f"  Player: {obj['player']} - OVR: {obj['profile']['ovr']}")
        elif obj.get("type") == "player":
            print(f"  Player: {obj['player']} - ERROR: {obj.get('error')}")
        else:
            print(f"  {obj.get('type')}: {obj}")
    except:
        print(f"  RAW: {line[:100]}")

print("\nSTDERR:")
print(result.stderr[:500] if result.stderr else "(none)")
print(f"\nReturn code: {result.returncode}")
