"""Search for play names using shorter fragments and alternative approaches."""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import struct
import os

kernel = WinDLL('kernel32')
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.OpenProcess.argtypes = [ctypes.c_int, ctypes.c_bool, ctypes.c_int]
kernel.ReadProcessMemory.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, 
    c_size_t, ctypes.POINTER(c_size_t)
]
kernel.VirtualQueryEx.restype = ctypes.c_size_t
kernel.VirtualQueryEx.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t
]

class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_uint32),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
    ]

def read_memory(h, addr, size):
    buf = create_string_buffer(size)
    if kernel.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, byref(c_size_t(0))):
        return buf.raw
    return None

def find_process():
    for p in psutil.process_iter():
        if 'NBA2K26' in p.name():
            return p.pid
    return None

def encode_wstring(s):
    return (s + "\x00").encode('utf-16-le')

def decode_wstring(data, max_chars=50):
    try:
        raw = data[:max_chars*2]
        return raw.decode('utf-16-le', errors='ignore').split('\x00')[0].strip()
    except:
        return ""

def main():
    pid = find_process()
    if not pid:
        print("NBA2K26.exe not running!")
        return
    
    print(f"PID: {pid}")
    h = kernel.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        print("Failed to open process!")
        return
    
    # Try searching for shorter, more distinctive fragments
    # These are less likely to be compressed/encoded
    short_fragments = [
        ("STAGGER", "Play name fragment"),
        ("ELBOW", "Play name fragment"),
        ("FLARE", "Play name fragment"),
        ("DELAY", "Play name fragment"),
        ("DBL TRI", "Play name fragment"),
        ("SWING BACK", "Play name fragment"),
    ]
    
    print("="*80)
    print("Searching for shorter play name fragments")
    print("="*80)
    
    for fragment, desc in short_fragments:
        print(f"\nSearching for '{fragment}' ({desc})...")
        fragment_bytes = encode_wstring(fragment)
        
        mbr = MBI()
        addr = 0
        hits = []
        
        while True:
            result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
            if result == 0:
                break
            
            if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
                buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
                if buf:
                    idx = buf.find(fragment_bytes)
                    while idx >= 0:
                        loc = mbr.BaseAddress + idx
                        # Get context
                        context = read_memory(h, loc - 30, 80)
                        if context:
                            full_text = decode_wstring(context, 40)
                            hits.append((loc, full_text))
                        idx = buf.find(fragment_bytes, idx + 2)
            
            addr = mbr.BaseAddress + mbr.RegionSize
        
        print(f"  Found {len(hits)} hits")
        if hits:
            for loc, text in hits[:5]:
                print(f"    0x{loc:X}: '{text}'")
    
    # Also try searching in game files
    print("\n" + "="*80)
    print("Searching in game files for play names")
    print("="*80)
    
    # Look for playcatalog.iff or playdata.iff
    game_dirs = [
        r"C:\Program Files (x86)\Steam\steamapps\common\NBA 2K26",
        r"C:\Program Files\Steam\steamapps\common\NBA 2K26",
        r"D:\Steam\steamapps\common\NBA 2K26",
    ]
    
    for game_dir in game_dirs:
        if os.path.exists(game_dir):
            print(f"\nFound game directory: {game_dir}")
            
            # Search for play catalog files
            for root, dirs, files in os.walk(game_dir):
                for f in files:
                    if 'play' in f.lower() and ('catalog' in f.lower() or 'data' in f.lower()):
                        filepath = os.path.join(root, f)
                        filesize = os.path.getsize(filepath)
                        print(f"  Found: {filepath} ({filesize} bytes)")
                        
                        # Search for play names in file
                        try:
                            with open(filepath, 'rb') as fh:
                                content = fh.read()
                            
                            # Search for UTF-16LE play names
                            for term in ["FIST DELAY", "FIST STAGGER", "QUICK FLARE", "PUNCH RIP"]:
                                term_utf16 = term.encode('utf-16-le')
                                idx = content.find(term_utf16)
                                if idx >= 0:
                                    print(f"    Found '{term}' at offset 0x{idx:X}")
                                    # Show context
                                    context_start = max(0, idx - 20)
                                    context_end = min(len(content), idx + 60)
                                    context = content[context_start:context_end]
                                    try:
                                        text = context.decode('utf-16-le', errors='ignore')
                                        print(f"    Context: '{text}'")
                                    except:
                                        pass
                        except Exception as e:
                            print(f"    Error reading file: {e}")
            
            break
    else:
        print("Game directory not found in common locations")

if __name__ == "__main__":
    main()
