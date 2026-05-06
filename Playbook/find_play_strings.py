"""
Find play name strings by scanning ALL memory regions including mapped files.
Previous scan missed them because it capped regions at 64MB and skipped mapped files.
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
print('module_base = 0x{:X}'.format(module_base))

# ── Step 1: Map all memory regions, show large ones ───────────────────────────
print('\n=== LARGE MEMORY REGIONS (>16MB) ===')
MEM_COMMIT  = 0x1000
MEM_MAPPED  = 0x40000
MEM_PRIVATE = 0x20000
MEM_IMAGE   = 0x1000000

mbi = MEMORY_BASIC_INFORMATION()
addr = 0x10000
large_regions = []
all_regions   = []

while addr < 0x7FFFFFFFFFFF:
    ret = VirtualQueryEx(hproc, ctypes.c_void_p(addr),
                         ctypes.byref(mbi), ctypes.sizeof(mbi))
    if ret == 0:
        break
    base = mbi.BaseAddress or 0
    size = mbi.RegionSize or 0x1000

    if mbi.State == MEM_COMMIT:
        prot = mbi.Protect
        typ  = mbi.Type
        all_regions.append((base, size, prot, typ))
        if size >= 16 * 1024 * 1024:
            large_regions.append((base, size, prot, typ))

    next_addr = base + size
    if next_addr <= addr:
        break
    addr = next_addr

type_names = {MEM_MAPPED: 'MAPPED', MEM_PRIVATE: 'PRIVATE', MEM_IMAGE: 'IMAGE'}
prot_names = {0x02:'RO', 0x04:'RW', 0x20:'XR', 0x40:'XRW', 0x80:'XWC'}

for base, size, prot, typ in sorted(large_regions, key=lambda x: -x[1])[:30]:
    tname = type_names.get(typ, '0x{:X}'.format(typ))
    pname = prot_names.get(prot, '0x{:X}'.format(prot))
    print('  0x{:X}  {:8.1f} MB  {:7}  {}'.format(base, size/1024/1024, tname, pname))

# ── Step 2: Search for play strings in ALL regions (no size cap) ──────────────
SEARCH_TERMS = [b'FIST DOWN', b'FIST POP', b'PHI GIVE', b'ISO 31 ELBOW',
                b'PUNCH ELBOW', b'HANDOFF', b'PLAYBOOK']
SEARCH_UTF16 = [t.decode('ascii').encode('utf-16-le') for t in SEARCH_TERMS]

print('\n=== SCANNING ALL COMMITTED REGIONS FOR PLAY STRINGS ===')
print('Total committed regions: {}'.format(len(all_regions)))

hits = []
t0 = time.time()
chunk = 4 * 1024 * 1024  # read 4MB at a time to avoid OOM

for base, size, prot, typ in all_regions:
    # Skip PAGE_NOACCESS and PAGE_GUARD
    if prot in (0x01, 0x100) or prot & 0x100:
        continue

    offset = 0
    while offset < size:
        read_size = min(chunk, size - offset)
        data = mem_read(hproc, base + offset, read_size)
        if not data:
            offset += read_size
            continue
        data = bytes(data)

        for term in SEARCH_TERMS:
            idx = data.find(term)
            if idx != -1:
                abs_addr = base + offset + idx
                ctx = data[max(0, idx-16):idx+64]
                asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
                tname = type_names.get(typ, hex(typ))
                pname = prot_names.get(prot, hex(prot))
                hits.append((abs_addr, 'ASCII', term.decode(), tname, pname, ctx))

        for i, term16 in enumerate(SEARCH_UTF16):
            idx = data.find(term16)
            if idx != -1:
                abs_addr = base + offset + idx
                ctx = data[max(0, idx-32):idx+128]
                tname = type_names.get(typ, hex(typ))
                pname = prot_names.get(prot, hex(prot))
                hits.append((abs_addr, 'UTF16', SEARCH_TERMS[i].decode(), tname, pname, ctx))

        offset += read_size

    if time.time() - t0 > 45:
        print('45s limit reached at 0x{:X}'.format(base))
        break

print('Found {} hits in {:.1f}s'.format(len(hits), time.time() - t0))

# Show results
seen = set()
for abs_addr, enc, term, tname, pname, ctx in hits:
    key = (enc, term, abs_addr // 512)
    if key in seen:
        continue
    seen.add(key)
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx[:64])
    rva = abs_addr - module_base
    loc = 'RVA+0x{:X}'.format(rva) if 0 <= rva < 0x10000000 else '0x{:X}'.format(abs_addr)
    print('\n  [{}] "{}" at {} ({} {}):'.format(enc, term, loc, tname, pname))
    print('  {}'.format(asc))
    # Show surrounding as hex
    hex_c = ' '.join('{:02X}'.format(b) for b in ctx[:48])
    print('  {}'.format(hex_c))

if not hits:
    print('\nNothing found! Play names may be:')
    print('  - In a PAK/IFF file not yet mapped')
    print('  - Stored as hash IDs with no plain text in memory')
    print('  - In a region with special protection we are skipping')
    print('\nLarge mapped regions above are the best candidates to check manually.')

kernel32.CloseHandle(hproc)
