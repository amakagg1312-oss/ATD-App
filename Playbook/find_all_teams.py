"""Find all 30 NBA team playbooks in game memory"""

import os, sys, struct, ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer

# Win32
kern = WinDLL('kernel32', use_last_error=True)
OpenProcess = kern.OpenProcess
OpenProcess.restype = wintypes.HANDLE
ReadProcessMemory = kern.ReadProcessMemory
CloseHandle = kern.CloseHandle

def find_pid():
    try:
        import psutil
        for p in psutil.process_iter():
            try:
                if 'NBA2K26' in p.name().upper() and 'FILE' not in p.name().upper():
                    return p.pid
            except:
                pass
    except:
        pass
    return None

def mem_read(h, addr, size):
    buf = create_string_buffer(size)
    return buf.raw if ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))) else None

# Load play catalog
PLAY_CATALOG = {}
def load_catalog():
    global PLAY_CATALOG
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game files', 'all_play_names.txt')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                if ': ' in line:
                    PLAY_CATALOG[i] = line.split(': ')[1].strip(" '")
    except:
        pass
load_catalog()

# All 30 NBA teams
TEAMS = [
    'ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW',
    'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
    'OKC', 'ORL', 'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS'
]

def find_all_playbooks():
    pid = find_pid()
    if not pid:
        print("NBA2K26 not running")
        return
    
    hproc = OpenProcess(0x1F0FFF, False, pid)
    if not hproc:
        print("Could not open process")
        return
    
    print(f"Scanning memory for all playbooks... PID={pid}")
    
    # Collect all valid playbook structures
    candidates = []
    
    for base in range(0x24070000, 0x24090000, 0x10000):
        buf = create_string_buffer(0x10000)
        if not ReadProcessMemory(hproc, ctypes.c_void_p(base), buf, 0x10000, byref(c_size_t(0))):
            continue
        raw = buf.raw
        
        for i in range(0, 0x10000 - 400, 4):
            cnt = struct.unpack('<I', raw[i:i+4])[0]
            if 5 <= cnt <= 100:
                addr = base + i
                data = mem_read(hproc, addr, 4 + cnt * 4)
                if data:
                    vc = struct.unpack('<I', data[:4])[0]
                    if vc == cnt:
                        plays = []
                        for j in range(cnt):
                            v = struct.unpack('<I', data[4+j*4:4+(j+1)*4])[0]
                            plays.append(v)
                        valid = [p for p in plays if 1 <= p <= 12506]
                        if len(valid) >= cnt * 0.5:  # At least 50% valid
                            candidates.append((addr, cnt, plays, valid))
    
    print(f"Found {len(candidates)} playbook candidates")
    
    # Group by unique play counts (teams have different playbook sizes)
    by_count = {}
    for addr, cnt, plays, valid in candidates:
        if cnt not in by_count:
            by_count[cnt] = []
        by_count[cnt].append((addr, cnt, plays, valid))
    
    print("\nPlaybooks by count:")
    for cnt in sorted(by_count.keys()):
        entries = by_count[cnt]
        print(f"  Count {cnt}: {len(entries)} candidates")
        for addr, _, _, valid in entries[:3]:
            names = [PLAY_CATALOG.get(p, str(p))[:25] for p in valid[:2]]
            print(f"    {hex(addr)}: {names}")
    
    # Try to match to teams
    print("\n\nAttempting to match teams...")
    
    # Known team playbook sizes (approximate)
    # Teams with unique sizes are easier to match
    team_playbooks = {}
    
    for addr, cnt, plays, valid in candidates:
        if len(valid) >= cnt * 0.7:  # At least 70% valid
            team_playbooks[hex(addr)] = {
                'count': cnt,
                'plays': valid[:10],
                'names': [PLAY_CATALOG.get(p, str(p))[:30] for p in valid[:3]]
            }
    
    print(f"\nFound {len(team_playbooks)} likely team playbooks:")
    for addr, info in sorted(team_playbooks.items()):
        print(f"  {addr}: {info['count']} plays - {info['names']}")
    
    CloseHandle(hproc)
    return team_playbooks

if __name__ == '__main__':
    find_all_playbooks()