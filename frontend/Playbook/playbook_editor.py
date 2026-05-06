"""NBA 2K26 Playbook Editor - scans memory for all playbooks"""

import os, sys, struct, ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
from typing import List, Dict

def log_err(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Play catalog
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

# Win32
kern = WinDLL('kernel32', use_last_error=True)
OpenProcess = kern.OpenProcess
OpenProcess.restype = wintypes.HANDLE
ReadProcessMemory = kern.ReadProcessMemory
WriteProcessMemory = kern.WriteProcessMemory
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

def mem_write(h, addr, data):
    return WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data), byref(c_size_t(0))) != 0

class PlaybookEditor:
    def __init__(self):
        self.hproc = None
        self.pid = None
        
    def connect(self):
        self.pid = find_pid()
        if not self.pid:
            log_err("NBA2K26 not running")
            return False
        self.hproc = OpenProcess(0x1F0FFF, False, self.pid)
        return bool(self.hproc)
        
    def disconnect(self):
        if self.hproc:
            CloseHandle(self.hproc)
            self.hproc = None
    
    def scan(self):
        results = []
        if not self.hproc:
            return results
        
        print(f"Scanning... PID={self.pid}")
        
        # Focus on playbook area - find all candidates
        for base in range(0x24070000, 0x24080000, 0x10000):
            buf = create_string_buffer(0x10000)
            if not ReadProcessMemory(self.hproc, ctypes.c_void_p(base), buf, 0x10000, byref(c_size_t(0))):
                continue
            raw = buf.raw
            
            for i in range(0, 0x10000 - 400, 4):
                cnt = struct.unpack('<I', raw[i:i+4])[0]
                if 5 <= cnt <= 30:
                    addr = base + i
                    data = mem_read(self.hproc, addr, 4 + cnt * 4)
                    if data:
                        vc = struct.unpack('<I', data[:4])[0]
                        if vc == cnt:
                            plays = []
                            for j in range(cnt):
                                v = struct.unpack('<I', data[4+j*4:4+(j+1)*4])[0]
                                plays.append(v)
                            # Get valid entries
                            valid = [p for p in plays if 1 <= p <= 12506]
                            # Accept if we have some valid entries, even with zeros
                            if len(valid) >= 2:
                                results.append((addr, cnt, plays))
                                print(f"  {hex(addr)}: {cnt} plays, {len(valid)} valid = {[PLAY_CATALOG.get(p, str(p)) for p in valid[:5]]}")
        
        print(f"Found {len(results)} playbooks")
        return results
    
    def get_playbook(self):
        pbs = self.scan()
        return pbs[0][2] if pbs else []

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--scan', action='store_true')
    p.add_argument('--read', action='store_true')
    args = p.parse_args()
    
    pb = PlaybookEditor()
    if not pb.connect():
        sys.exit(1)
    
    print(f"Connected. {len(pb.scan() or [])} plays in catalog")
    
    if args.scan:
        pb.scan()
    elif args.read:
        plays = pb.get_playbook()
        if plays:
            print(f"Current playbook ({len(plays)} plays):")
            for i, p in enumerate(plays):
                print(f"  {i+1}: {p} = {PLAY_CATALOG.get(p, '?')}")
        else:
            print("No playbook found")
    
    pb.disconnect()