import subprocess
import json
import sys

players = ["LeBron James"]
season = "2025-26"
project_root = r"D:\project"
db_dir = r"D:\project\NBA Site data"
roles_dir = r"D:\project\Player Roles"

batch_script = r"D:\project\nba2k26_generator\generator_batch.py"

result = subprocess.run(
    [sys.executable, batch_script, json.dumps(players), season, project_root, db_dir, roles_dir],
    capture_output=True,
    text=True,
    timeout=120,
    cwd=project_root,
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")
