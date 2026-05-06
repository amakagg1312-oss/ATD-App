import time
import subprocess
import json

start = time.time()
result = subprocess.run(
    ['python', 'gen_player_fast.py', 'Victor Wembanyama', '2024-25', 'D:\\project', 'D:\\project\\NBA Site data', 'D:\\project\\nba2k26_generator\\Roles'],
    capture_output=True, text=True, cwd=r'D:\project\nba2k26_generator'
)
elapsed = time.time() - start
print(f'Time: {elapsed:.2f}s')

if result.returncode == 0:
    data = json.loads(result.stdout)
    profile = data['profile']
    print(f'OVR: {profile["ovr"]}')
    print(f'Role: {profile["role"]}')
    print(f'Block: {profile["attributes"]["block"]}')
    print(f'Speed: {profile["attributes"]["speed"]}')
    print(f'Strength: {profile["attributes"]["strength"]}')
    print(f'Height: {profile["info"]["height"]}')
else:
    print(f'Error: {result.stderr[:500]}')
