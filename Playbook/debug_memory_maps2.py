"""Examine the structure of memory_maps() output."""

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
    try:
        maps = proc.memory_maps()
        print(f"Number of memory maps: {len(maps)}")
        if maps:
            first = maps[0]
            print(f"First memory map object type: {type(first)}")
            print(f"First memory map object: {first}")
            # Try to see what attributes it has
            print(f"Dir of first object: [attr for attr in dir(first) if not attr.startswith('_')]")
            # Actually, let's just print the dir
            attrs = [attr for attr in dir(first) if not attr.startswith('_')]
            print(f"Attributes: {attrs}")
            # If it's a namedtuple or similar, we can try to access by index
            try:
                print(f"Trying to access by index: {first[0]}, {first[1]}")
            except:
                print("Not indexable")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
