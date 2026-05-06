"""
Search the live process heap for play name strings and find the catalog
structure that associates names with play code pointers.

Play names from screenshot: "FIST DOWN 25", "FIST POP 5", "PHI GIVE 51 SPREAD",
"ISO 31 ELBOW", "PUNCH ELBOW 54", "PHI HIGH 5 ELBOW", etc.

Strategy:
1. Enumerate all readable heap regions
2. Search for play name substrings as ASCII and UTF-16
3. When found, dump surrounding context to find the play struct layout
4. Cross-reference with the vtable code pointers from sub+0x048
"""
import sys, struct, ctypes, time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess,
                               MEMORY_BASIC_INFORMATION, VirtualQueryEx)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

# Known play names from the 76ers playbook screenshot
SEARCH_TERMS_ASCII = [
    b'FIST DOWN', b'FIST POP', b'FIST 5', b'FIST 21',
    b'FIST 13', b'FIST HORNS',
    b'PHI GIVE', b'PHI HIGH', b'ISO 31', b'PUNCH ELBOW',
    b'PUNCH 54', b'GIVE 53',
]
SEARCH_TERMS_UTF16 = [t.decode('ascii').encode('utf-16-le') for t in SEARCH_TERMS_ASCII]

# Vtable/code pointers we're looking for (from sub+0x048 in play slots)
KNOWN_PLAY_PTRS = [
    0x645A1B, 0x645A1E, 0x645A20, 0x645A21, 0x645A42, 0x645A47,
    0x645A4A, 0x645A4D, 0x645A95, 0x645A98, 0x645A9A, 0x645A9B,
    0x645A9D, 0x645A9E, 0x645AA0, 0x645AA1, 0x645AA3, 0x645AA4,
    0x645AC1, 0x645AC2, 0x645AC4, 0x645AC5, 0x645AC7, 0x645AC8,
    0x645ACA, 0x645ACB, 0x645ACD, 0x645ACE, 0x645AD0, 0x645AD1,
    0x645ADE, 0x645ADF, 0x645AE1, 0x645AE2,
]
# As absolute addresses (module_base + rva)
KNOWN_PLAY_PTRS_ABS = set(module_base + v for v in KNOWN_PLAY_PTRS)

def enum_regions(min_addr=0x10000, max_addr=0x7FFFFFFFFFFF, min_size=0, max_size=64*1024*1024):
    mbi = MEMORY_BASIC_INFORMATION()
    addr = min_addr
    while addr < max_addr:
        ret = VirtualQueryEx(hproc, ctypes.c_void_p(addr),
                             ctypes.byref(mbi), ctypes.sizeof(mbi))
        if ret == 0:
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0x1000
        # Only committed readable regions, skip huge/tiny
        if (mbi.State == 0x1000 and
            mbi.Protect not in (0x01, 0x100) and
            mbi.Protect & 0xFF not in (0x01,) and
            min_size <= size <= max_size):
            yield base, size
        next_addr = base + size
        if next_addr <= addr:
            break
        addr = next_addr

print('Scanning heap for play name strings...')
found_names   = []   # (addr, encoding, matched_term, context_bytes)
found_ptrs    = []   # (addr, matched_ptr_rva, context_bytes)
regions_read  = 0
total_bytes   = 0

t0 = time.time()
for base, size in enum_regions():
    data = mem_read(hproc, base, size)
    if not data:
        continue
    data = bytes(data)
    regions_read += 1
    total_bytes  += len(data)

    # Search ASCII
    for term in SEARCH_TERMS_ASCII:
        idx = 0
        while True:
            idx = data.find(term, idx)
            if idx == -1:
                break
            # Require letter before (if any) to avoid false positives mid-word
            ctx_start = max(0, idx - 32)
            ctx_end   = min(len(data), idx + 80)
            found_names.append((base + idx, 'ASCII', term.decode(), data[ctx_start:ctx_end]))
            idx += 1

    # Search UTF-16LE
    for i, term16 in enumerate(SEARCH_TERMS_UTF16):
        idx = 0
        while True:
            idx = data.find(term16, idx)
            if idx == -1:
                break
            ctx_start = max(0, idx - 32)
            ctx_end   = min(len(data), idx + 128)
            found_names.append((base + idx, 'UTF16', SEARCH_TERMS_ASCII[i].decode(), data[ctx_start:ctx_end]))
            idx += 2

    # Search for known play code pointers stored as u64 in heap
    for ptr_abs in KNOWN_PLAY_PTRS_ABS:
        target = struct.pack('<Q', ptr_abs)
        idx = 0
        while True:
            idx = data.find(target, idx)
            if idx == -1:
                break
            ctx_start = max(0, idx - 64)
            ctx_end   = min(len(data), idx + 128)
            rva = ptr_abs - module_base
            found_ptrs.append((base + idx, rva, data[ctx_start:ctx_end]))
            idx += 8

    if time.time() - t0 > 30:
        print('  30s limit reached, stopping scan')
        break

print('Scan done: {} regions, {} MB in {:.1f}s'.format(
    regions_read, total_bytes // (1024*1024), time.time() - t0))

# ── RESULTS: name hits ────────────────────────────────────────────────────────
print('\n=== PLAY NAME HITS ({}) ==='.format(len(found_names)))
dedup = set()
for addr, enc, term, ctx in found_names:
    key = (enc, term, addr // 256)
    if key in dedup:
        continue
    dedup.add(key)
    hex_ctx  = ' '.join('{:02X}'.format(b) for b in ctx[:48])
    asc_ctx  = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx[:48])
    print('\n  0x{:X} [{}] "{}":'.format(addr, enc, term))
    print('  hex: {}'.format(hex_ctx))
    print('  asc: {}'.format(asc_ctx))

    # Look for a code pointer nearby in the context
    for i in range(0, len(ctx) - 7, 8):
        v = struct.unpack_from('<Q', ctx, i)[0]
        rva = v - module_base
        if rva in KNOWN_PLAY_PTRS:
            offset_from_name = (addr - (addr - 32 + i))
            print('  *** PLAY CODE PTR 0x{:X} (RVA+0x{:X}) found at ctx+0x{:X}'.format(
                v, rva, i))

# ── RESULTS: code pointer hits ────────────────────────────────────────────────
print('\n=== PLAY CODE POINTER REFERENCES IN HEAP ({} hits) ==='.format(len(found_ptrs)))
# Group by RVA
from collections import defaultdict
by_rva = defaultdict(list)
for addr, rva, ctx in found_ptrs:
    by_rva[rva].append((addr, ctx))

for rva in sorted(by_rva.keys()):
    hits = by_rva[rva]
    print('\n  RVA+0x{:X}: {} heap locations store this ptr'.format(rva, len(hits)))
    for addr, ctx in hits[:3]:
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx[:64])
        # Show context before the ptr (might contain play name or ID)
        print('    0x{:X}: {}'.format(addr, asc))

kernel32.CloseHandle(hproc)
