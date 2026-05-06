"""NBA 2K26 Playbook Editor"""

import os, sys, struct, ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
from typing import List, Dict

def log_err(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

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

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

kernel = WinDLL('kernel32')
OpenProcess = kernel.OpenProcess
OpenProcess.restype = ctypes.c_void_p
OpenProcess.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_int]
CloseHandle = kernel.CloseHandle
ReadProcessMemory = kernel.ReadProcessMemory
ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, c_size_t, ctypes.POINTER(c_size_t)]

def find_process():
    try:
        import psutil
        for p in psutil.process_iter():
            if 'NBA2K26' in p.name():
                return p.pid
    except:
        pass
    return None

def mem_read(handle, addr, size):
    buf = create_string_buffer(size)
    if ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

def mem_write(handle, addr, data):
    written = c_size_t(0)
    return WriteProcessMemory(handle, ctypes.c_void_p(addr), data, len(data), byref(written))

class PlaybookEditor:
    def __init__(self):
        self.pid = None
        self.hproc = None
    
    def connect(self):
        self.pid = find_process()
        if not self.pid:
            log_err("NBA2K26 not running")
            return False
        self.hproc = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, self.pid)
        if not self.hproc:
            log_err("Cannot open process")
            return False
        print(f"Connected. PID={self.pid}")
        return True
    
    def disconnect(self):
        if self.hproc:
            CloseHandle(self.hproc)
    
    def scan(self):
        results = []
        for base in range(0x27000000, 0x28000000, 0x100000):
            raw = mem_read(self.hproc, base, 0x100000)
            if not raw:
                continue
            for i in range(0, len(raw) - 0x200, 4):
                team_id = struct.unpack('<I', raw[i:i+4])[0]
                if 0 <= team_id <= 30:
                    po = 0x130
                    if i + po + 4 <= len(raw):
                        cnt = struct.unpack('<I', raw[i+po:i+po+4])[0]
                        if 3 <= cnt <= 100:
                            addr = base + i + po
                            data = mem_read(self.hproc, addr, 4 + cnt * 4)
                            if data:
                                plays = []
                                for j in range(cnt):
                                    v = struct.unpack('<I', data[4+j*4:4+(j+1)*4])[0]
                                    if 1 <= v <= 12506:
                                        plays.append(v)
                                if len(plays) >= 2:
                                    results.append((addr, cnt, plays))
        print(f"Found {len(results)} playbooks")
        return results
    
    def get_playbook(self):
        pbs = self.scan()
        return pbs[0][2] if pbs else []
    
    def _read_plays_at(self, addr):
        data = mem_read(self.hproc, addr, 4)
        if not data:
            return []
        cnt = struct.unpack('<I', data[:4])[0]
        data = mem_read(self.hproc, addr, 4 + cnt * 4)
        if not data:
            return []
        plays = []
        for j in range(cnt):
            v = struct.unpack('<I', data[4+j*4:4+(j+1)*4])[0]
            if 1 <= v <= 12506:
                plays.append(v)
        return plays
    
    def find_large_playbook_addr(self):
        if not self.hproc:
            return None
        for base in range(0x27000000, 0x28000000, 0x100000):
            raw = mem_read(self.hproc, base, 0x100000)
            if not raw:
                continue
            for i in range(0, len(raw) - 0x200, 4):
                team_id = struct.unpack('<I', raw[i:i+4])[0]
                if 0 <= team_id <= 30:
                    po = 0x130
                    if i + po + 4 <= len(raw):
                        cnt = struct.unpack('<I', raw[i+po:i+po+4])[0]
                        if 3 <= cnt <= 100:
                            return base + i + po
        return None
    
    def find_large_playbook(self):
        addr = self.find_large_playbook_addr()
        if addr:
            return self._read_plays_at(addr)
        return []
    
    def add_plays(self, play_ids):
        if not self.hproc:
            return False, "No process"
        addr = self.find_large_playbook_addr()
        if not addr:
            return False, "No playbook"
        
        data = mem_read(self.hproc, addr, 4)
        if not data:
            return False, "Cannot read"
        
        count = struct.unpack('<I', data[:4])[0]
        
        if count + len(play_ids) > 100:
            return False, "Too many"
        
        WriteProcessMemory = kernel.WriteProcessMemory
        WriteProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(c_size_t)]
        
        new_count = count + len(play_ids)
        WriteProcessMemory(self.hproc, ctypes.c_void_p(addr), struct.pack('<I', new_count), 4, byref(c_size_t(0)))
        
        for i, pid in enumerate(play_ids):
            offset = 4 + (count + i) * 4
            WriteProcessMemory(self.hproc, ctypes.c_void_p(addr + offset), struct.pack('<I', pid), 4, byref(c_size_t(0)))
        
        return True, f"Added {len(play_ids)} (now {new_count})"
    
    def set_plays(self, play_ids):
        if not self.hproc:
            return False, "No process"
        addr = self.find_large_playbook_addr()
        if not addr:
            return False, "No playbook"
        
        WriteProcessMemory = kernel.WriteProcessMemory
        WriteProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(c_size_t)]
        
        count = len(play_ids)
        WriteProcessMemory(self.hproc, ctypes.c_void_p(addr), struct.pack('<I', count), 4, byref(c_size_t(0)))
        
        for i, pid in enumerate(play_ids):
            offset = 4 + i * 4
            WriteProcessMemory(self.hproc, ctypes.c_void_p(addr + offset), struct.pack('<I', pid), 4, byref(c_size_t(0)))
        
        return True, f"Set {count} plays"

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--team', default='')
    p.add_argument('--scan', action='store_true')
    p.add_argument('--read', action='store_true')
    p.add_argument('--large', action='store_true')
    p.add_argument('--list', action='store_true')
    p.add_argument('--add', nargs='+', type=int)
    p.add_argument('--set', nargs='+', type=int)
    args = p.parse_args()
    
    if args.list:
        for idx, name in sorted(PLAY_CATALOG.items()):
            print(f"{idx}: {name}")
        sys.exit(0)
    
    pb = PlaybookEditor()
    if not pb.connect():
        sys.exit(1)
    
    if args.scan:
        pb.scan()
    elif args.large:
        plays = pb.find_large_playbook()
        if plays:
            print(f"Large playbook ({len(plays)} plays):")
            for i, p in enumerate(plays):
                print(f"  {i+1}: {p} = {PLAY_CATALOG.get(p, '?')}")
        else:
            print("No large playbook")
    elif args.add:
        ok, msg = pb.add_plays(args.add)
        print(msg)
    elif args.set:
        ok, msg = pb.set_plays(args.set)
        print(msg)
    elif args.read:
        plays = pb.get_playbook()
        if plays:
            print(f"Playbook ({len(plays)} plays):")
            for i, p in enumerate(plays):
                print(f"  {i+1}: {p} = {PLAY_CATALOG.get(p, '?')}")
        else:
            print("No playbook")
    else:
        plays = pb.find_large_playbook()
        if not plays:
            plays = pb.get_playbook()
        if plays:
            print(f"Playbook ({len(plays)} plays):")
            for i, p in enumerate(plays):
                print(f"  {i+1}: {p} = {PLAY_CATALOG.get(p, '?')}")
        else:
            print("No playbook")
    
    pb.disconnect()