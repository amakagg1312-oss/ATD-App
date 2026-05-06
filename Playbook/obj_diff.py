"""
Tight snap/diff of the playbook object and the u64[1] pointer fields.
Timed: user has 4 seconds to switch after 'READY'.
"""
import sys, struct, time, ctypes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playbook_scanner import (find_pid, get_module_base, mem_read, GAME_EXE,
                               PROCESS_ALL_ACCESS, kernel32, OpenProcess, TEAM_RVA)

pid = find_pid(GAME_EXE)
module_base = get_module_base(pid, GAME_EXE)
hproc = OpenProcess(PROCESS_ALL_ACCESS, False, pid)

VOLATILE_RVAS = [0x741F9E0, 0x741FA08]  # the two with real u64[1] pointers
OBJ_READ_SIZE = 0x4000  # 16KB

def snap_state(hproc, module_base):
    state = {}
    for rva in VOLATILE_RVAS:
        e = mem_read(hproc, module_base + rva, 16)
        if e:
            byte3 = e[3]
            u64_1 = struct.unpack_from('<Q', e, 8)[0]
            state[rva] = {'entry': bytes(e), 'byte3': byte3, 'u64_1': u64_1}
            if 0x10000 < u64_1 < 0x7FFFFFFFFFFF:
                obj = mem_read(hproc, u64_1, OBJ_READ_SIZE)
                if obj:
                    state[rva]['obj'] = bytes(obj)
    return state

def print_diff(label, addr, data_a, data_b):
    mn = min(len(data_a), len(data_b))
    diffs = [(i, data_a[i], data_b[i]) for i in range(mn) if data_a[i] != data_b[i]]
    if not diffs:
        print('  {} @ 0x{:X}: no change'.format(label, addr))
        return
    print('  {} @ 0x{:X}: {} bytes differ:'.format(label, addr, len(diffs)))
    blks, blk = [], [diffs[0]]
    for d in diffs[1:]:
        if d[0] == blk[-1][0]+1: blk.append(d)
        else: blks.append(blk); blk = [d]
    blks.append(blk)
    for blk in blks[:12]:
        off = blk[0][0]
        raw_a = bytes(x[1] for x in blk[:4]).ljust(4, b'\x00')
        raw_b = bytes(x[2] for x in blk[:4]).ljust(4, b'\x00')
        u32_a = struct.unpack('<I', raw_a)[0]
        u32_b = struct.unpack('<I', raw_b)[0]
        flag = '  *** CANDIDATE ***' if (1<=u32_a<=60 or 1<=u32_b<=60) and len(blk)<=4 else ''
        print('    +0x{:04X} abs 0x{:X}: {} -> {}  u32:{}->{} ({} bytes){}'.format(
            off, addr+off,
            ' '.join('{:02X}'.format(x[1]) for x in blk[:8]),
            ' '.join('{:02X}'.format(x[2]) for x in blk[:8]),
            u32_a, u32_b, len(blk), flag))

print('Snapping baseline...')
snap_a = snap_state(hproc, module_base)
for rva, s in snap_a.items():
    print('  RVA+0x{:X}: byte[3]={} u64[1]=0x{:X} obj_read={}'.format(
        rva, s['byte3'], s['u64_1'],
        len(s.get('obj', b'')) if s.get('obj') else 'N/A'))

print()
print('=== SWITCH THE PLAYBOOK NOW — you have 5 seconds ===')
for i in range(5, 0, -1):
    print('  {}...'.format(i))
    time.sleep(1.0)

print('Reading post-switch state...')
snap_b = snap_state(hproc, module_base)

print('\n=== RESULTS ===')
for rva in VOLATILE_RVAS:
    if rva not in snap_a or rva not in snap_b:
        continue
    a = snap_a[rva]
    b = snap_b[rva]
    print('\nRVA+0x{:X}:'.format(rva))
    print('  byte[3]: {} -> {}'.format(a['byte3'], b['byte3']))
    print('  u64[1]:  0x{:X} -> 0x{:X}  {}'.format(
        a['u64_1'], b['u64_1'],
        '(CHANGED)' if a['u64_1'] != b['u64_1'] else '(same)'))

    # diff the entry bytes
    print_diff('entry', module_base + rva, a['entry'], b['entry'])

    # diff the objects
    if a.get('obj') and b.get('obj') and a['u64_1'] == b['u64_1']:
        print('  Object at 0x{:X} (in-place changes):'.format(a['u64_1']))
        print_diff('obj', a['u64_1'], a['obj'], b['obj'])
    elif a.get('obj') and b.get('obj') and a['u64_1'] != b['u64_1']:
        print('  u64[1] changed: old obj vs new obj diff:')
        print_diff('old_obj', a['u64_1'], a['obj'], b['obj'])
        print_diff('new_obj', b['u64_1'], a.get('obj', b''), b['obj'])

kernel32.CloseHandle(hproc)
