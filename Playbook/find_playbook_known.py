"""Find playbook using known play names from previous session."""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import ctypes
from ctypes import wintypes, byref, c_size_t, WinDLL, create_string_buffer
import psutil
import struct
import json

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
    
    # Load known plays from previous session
    with open('D:\\project\\Playbook\\76ers_playbook_memory.json', 'r') as f:
        playbook_data = json.load(f)
    
    known_plays = playbook_data['plays']
    print(f"Loaded {len(known_plays)} known plays from previous session")
    
    # Get unique play names
    unique_plays = {}
    for play in known_plays:
        name = play['play_name']
        offset = play['byte_offset']
        if name not in unique_plays:
            unique_plays[name] = offset
    
    print(f"Found {len(unique_plays)} unique play names")
    
    # Try known addresses first
    print("\n" + "="*80)
    print("STEP 1: Testing known addresses")
    print("="*80)
    
    old_string_base = 0x2ffcd8000
    old_playbook_base = 0x2ffca1910
    
    # Test string block
    test_data = read_memory(h, old_string_base, 100)
    if test_data:
        print(f"String block @ 0x{old_string_base:X} is readable")
        # Try to read a known play
        for play in known_plays[:5]:
            play_addr = old_string_base + play['byte_offset']
            play_data = read_memory(h, play_addr, 40)
            if play_data:
                play_name = decode_wstring(play_data, 20)
                print(f"  Offset {play['byte_offset']}: '{play_name}'")
    else:
        print(f"String block @ 0x{old_string_base:X} is NOT readable (address changed)")
    
    # Test playbook base
    test_data = read_memory(h, old_playbook_base, 48)
    if test_data:
        print(f"\nPlaybook base @ 0x{old_playbook_base:X} is readable")
        offset_val = struct.unpack('<I', test_data[:4])[0]
        print(f"  First entry offset: {offset_val}")
    else:
        print(f"\nPlaybook base @ 0x{old_playbook_base:X} is NOT readable (address changed)")
    
    print("\n" + "="*80)
    print("STEP 2: Search for playbook by known play names")
    print("="*80)
    
    # Use shorter, more distinctive play name fragments
    search_fragments = [
        ("FIST 64", "FIST 64 STS"),
        ("IVERSON", "FIST 21 IVERSON"),
        ("PUNCH 5", "PUNCH 5 WEA"),
        ("HORNS", "HORNS 12"),
        ("CLE FIST", "CLE FIST 15 DRA"),
        ("SAS FIST", "SAS FIST 15 FLAT OU"),
    ]
    
    for fragment, full_name in search_fragments:
        print(f"\nSearching for '{fragment}'...")
        fragment_bytes = encode_wstring(fragment)
        
        mbr = MBI()
        addr = 0
        hits = []
        
        while True:
            result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
            if result == 0:
                break
            
            if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
                # Only search readable regions
                buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
                if buf:
                    idx = buf.find(fragment_bytes)
                    while idx >= 0:
                        loc = mbr.BaseAddress + idx
                        hits.append(loc)
                        idx = buf.find(fragment_bytes, idx + 2)
            
            addr = mbr.BaseAddress + mbr.RegionSize
        
        print(f"  Found {len(hits)} hits")
        if hits:
            for loc in hits[:3]:
                print(f"    0x{loc:X}")
                # Show context
                data = read_memory(h, loc - 20, 80)
                if data:
                    for off in range(0, min(len(data), 60), 16):
                        chunk = data[off:off+16]
                        hex_str = ' '.join(f'{b:02X}' for b in chunk)
                        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                        print(f"      [{off:03X}] {hex_str:<48} {ascii_str}")
    
    print("\n" + "="*80)
    print("STEP 3: Search for playbook array structure")
    print("="*80)
    
    # Look for arrays of 4-byte values that could be play offsets
    # Play offsets from the known data range from ~88 to ~3267
    # So we're looking for arrays of uint32 values in range 0x50-0x1000
    
    print("Searching for playbook-like arrays...")
    
    mbr = MBI()
    addr = 0
    regions = 0
    playbook_candidates = []
    
    while True:
        result = kernel.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbr), ctypes.sizeof(mbr))
        if result == 0:
            break
        
        if mbr.State == 0x1000 and mbr.RegionSize > 0 and mbr.RegionSize < 0x10000000:
            buf = read_memory(h, mbr.BaseAddress, min(mbr.RegionSize, 0x100000))
            if buf:
                # Look for sequences of 4-byte values in play offset range
                for i in range(0, len(buf) - 240, 48):  # Playbook stride is 48 bytes
                    # Check first 4 bytes
                    val = struct.unpack_from('<I', buf, i)[0]
                    if 0x50 < val < 0x2000:
                        # Check if next few entries also look like offsets
                        offsets = []
                        valid = True
                        for j in range(0, 96, 48):  # Check 2 entries
                            if i + j + 4 <= len(buf):
                                v = struct.unpack_from('<I', buf, i + j)[0]
                                if 0x50 < v < 0x2000:
                                    offsets.append(v)
                                else:
                                    valid = False
                                    break
                        
                        if valid and len(offsets) >= 2:
                            playbook_candidates.append((mbr.BaseAddress + i, offsets))
            
            regions += 1
            if regions % 5000 == 0:
                print(f"  Scanned {regions} regions, found {len(playbook_candidates)} candidates...")
        
        addr = mbr.BaseAddress + mbr.RegionSize
    
    print(f"\nFound {len(playbook_candidates)} playbook-like arrays")
    
    # Show top candidates
    for addr, offsets in playbook_candidates[:20]:
        print(f"  0x{addr:X}: {offsets}")

if __name__ == "__main__":
    main()
