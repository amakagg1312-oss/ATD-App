import subprocess
import json
import time

python_path = r"D:\project\.venv\Scripts\python.exe"
script = r"D:\project\nba2k26_generator\team_batch.py"
project_root = r"D:\project"
db_dir = r"D:\project\NBA Site data"
roles_dir = r"D:\project\Player Roles"

players = ["LeBron James", "Anthony Davis"]
season = "2024-25"

print(f"[{time.time():.0f}] Starting team_batch.py with {len(players)} players...")
proc = subprocess.Popen(
    [python_path, "-u", script, json.dumps(players), season, project_root, db_dir, roles_dir],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd=project_root,
)

start = time.time()
while True:
    line = proc.stdout.readline()
    if not line:
        break
    elapsed = time.time() - start
    try:
        msg = json.loads(line.strip())
        if msg.get("type") == "progress":
            print(f"[{elapsed:.0f}s] Progress: {msg.get('status')} {msg.get('completed')}/{msg.get('total')}")
        elif msg.get("type") == "player":
            print(f"[{elapsed:.0f}s] Player: {msg.get('player')} - {'OK' if msg.get('ok') else 'FAIL: ' + msg.get('error', '')}")
        elif msg.get("type") == "done":
            print(f"[{elapsed:.0f}s] DONE: {msg.get('success')} success, {msg.get('failed')} failed")
            break
        else:
            print(f"[{elapsed:.0f}s] {msg}")
    except:
        print(f"[{elapsed:.0f}s] (non-json) {line.strip()[:100]}")

proc.wait()
print(f"Exit code: {proc.returncode}")
