"""
Live watcher v2 - polls module .data section + team struct regions every 0.3s.
Run this, then press the playbook cycle button in-game.
"""
import sys, struct, time
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess, TEAM_RVA, TEAM_STRIDE)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
team_data_raw = mem_read(hproc, struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0], TEAM_STRIDE)
table_base = struct.unpack('<Q', mem_read(hproc, module_base + TEAM_RVA, 8))[0]

ptr_FE8 = struct.unpack_from('<Q', team_data_raw, 0x0FE8)[0]
ptr_FF0 = struct.unpack_from('<Q', team_data_raw, 0x0FF0)[0]
ptr_12F8 = struct.unpack_from('<Q', team_data_raw, 0x12F8)[0]

regions = [
    ('mod_741E000', module_base + 0x741E000, 0x4000),
    ('mod_741B000', module_base + 0x741B000, 0x1000),
    ('mod_7E1E000', module_base + 0x7E1E000, 0x1000),
    ('team_structs', table_base, TEAM_STRIDE * 42),
    ('team+FE8', ptr_FE8, 8192),
    ('team+FF0', ptr_FF0, 8192),
    ('team+12F8', ptr_12F8, 8192),
]

baseline = {}
for label, addr, size in regions:
    if 0x100000000 < addr < 0xF00000000 or module_base <= addr <= module_base + 0x10000000:
        d = mem_read(hproc, addr, size)
        if d:
            baseline[(label, addr)] = d
            print('Watching {:25s} @ 0x{:X} ({:,} bytes)'.format(label, addr, size))

sys.stdout.flush()
print()
print('PRESS THE PLAYBOOK CYCLE BUTTON IN-GAME NOW.')
print('-' * 60)
sys.stdout.flush()

poll = 0
try:
    while True:
        time.sleep(0.3)
        poll += 1
        found_any = False
        for label, addr, size in regions:
            key = (label, addr)
            if key not in baseline:
                continue
            cur = mem_read(hproc, addr, size)
            if not cur:
                continue
            prev = baseline[key]
            mn = min(len(prev), len(cur))
            diffs = [(j, prev[j], cur[j]) for j in range(mn) if prev[j] != cur[j]]
            if not diffs:
                continue
            found_any = True
            ts = time.strftime('%H:%M:%S')
            blks, blk = [], [diffs[0]]
            for d in diffs[1:]:
                if d[0] == blk[-1][0] + 1:
                    blk.append(d)
                else:
                    blks.append(blk); blk = [d]
            blks.append(blk)
            for blk in blks[:8]:
                off = blk[0][0]
                abs_a = addr + off
                rva = abs_a - module_base
                raw_a = bytes(x[1] for x in blk[:4]).ljust(4, b'\x00')
                raw_b = bytes(x[2] for x in blk[:4]).ljust(4, b'\x00')
                u32_a = struct.unpack('<I', raw_a)[0]
                u32_b = struct.unpack('<I', raw_b)[0]
                u16_a = struct.unpack('<H', raw_a[:2])[0]
                u16_b = struct.unpack('<H', raw_b[:2])[0]
                ha = ' '.join('{:02X}'.format(x[1]) for x in blk[:8])
                hb = ' '.join('{:02X}'.format(x[2]) for x in blk[:8])
                rva_str = ' RVA+0x{:X}'.format(rva) if 'mod_' in label else ''
                print('[{}] {:12s}{} +0x{:X} abs 0x{:X}: [{}]->[{}] u32:{}->{} u16:{}->{} ({} bytes)'.format(
                    ts, label, rva_str, off, abs_a,
                    ha, hb, u32_a, u32_b, u16_a, u16_b, len(blk)))
            baseline[key] = cur
            sys.stdout.flush()
        if poll % 30 == 0 and not found_any:
            print('[{}] Polling... ({} polls)'.format(time.strftime('%H:%M:%S'), poll))
            sys.stdout.flush()
except KeyboardInterrupt:
    print('\nStopped.')

kernel32.CloseHandle(hproc)
