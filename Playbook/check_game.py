import subprocess
result = subprocess.run(['tasklist'], capture_output=True, text=True)
for line in result.stdout.split('\n'):
    if '2K' in line or 'NBA' in line:
        print(line.strip())
