import subprocess
import json
import sys
import time

server_script = r"D:\project\nba2k26_generator\team_server.py"
python_path = r"D:\project\.venv\Scripts\python.exe"

print(f"[{time.time():.0f}] Starting server...")
proc = subprocess.Popen(
    [python_path, "-u", server_script],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd=r"D:\project",
)

# Wait for ready signal
print(f"[{time.time():.0f}] Waiting for ready...")
while True:
    line = proc.stdout.readline()
    if not line:
        print(f"[{time.time():.0f}] Server died")
        break
    print(f"[{time.time():.0f}] Server says: {line.strip()}")
    try:
        msg = json.loads(line)
        if msg.get("type") == "status" and msg.get("status") == "ready":
            print(f"[{time.time():.0f}] Server is ready!")
            break
    except:
        pass

# Send generate request
print(f"[{time.time():.0f}] Sending generate request...")
req = {
    "action": "generate",
    "players": ["LeBron James"],
    "season": "2024-25",
    "db_dir": r"D:\project\NBA Site data",
    "roles_dir": r"D:\project\Player Roles",
    "project_root": r"D:\project",
}
proc.stdin.write(json.dumps(req) + "\n")
proc.stdin.flush()

# Read responses
print(f"[{time.time():.0f}] Reading responses...")
while True:
    line = proc.stdout.readline()
    if not line:
        print(f"[{time.time():.0f}] Server closed")
        break
    print(f"[{time.time():.0f}] Response: {line.strip()[:200]}")
    try:
        msg = json.loads(line)
        if msg.get("type") == "done":
            print(f"[{time.time():.0f}] DONE!")
            break
    except:
        pass

proc.kill()
