"""Get the memory maps of the NBA2K26 process and look for the executable region."""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import psutil

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p
    return None

def main():
    proc = find_process()
    if not proc:
        print("NBA2K26.exe not running!")
        return
    
    print(f"PID: {proc.pid}")
    print("Memory maps:")
    try:
        maps = proc.memory_maps()
        for m in maps:
            if 'NBA2K26.exe' in m.path:
                print(f"  {m.addr} {m.perms} {m.size} {m.path}")
    except Exception as e:
        print(f"Error getting memory maps: {e}")
    
    # Also, let's try to read the executable's memory from the first region that is the executable
    # We'll look for a region with 'X' in permissions (executable) and that contains the string 'NBA2K26'
    try:
        maps = proc.memory_maps()
        for m in maps:
            if 'NBA2K26.exe' in m.path and 'x' in m.perms:
                print(f"\nFound executable region: {m.addr} {m.perms} {m.size} {m.path}")
                # We'll try to read a small portion of this region to see if we can find the string
                # But note: we don't have a way to read arbitrary memory in this script without ctypes.
                # We'll just note the address.
                break
    except Exception as e:
        print(f"Error getting memory maps: {e}")

if __name__ == "__main__":
    main()
