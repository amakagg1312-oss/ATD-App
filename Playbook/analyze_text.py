import struct

path = 'D:\\project\\Playbook\\game files\\english_extracted\\TEXT.VCLOCALIZEDATA'
with open(path, 'rb') as f:
    content = f.read()

print('File size: {} bytes'.format(len(content)))

# The header suggests a structured format
# Let's try to parse it
# First 16 bytes are zeros, then at offset 0x10 we have 0x31 (49)
# This might be a string table with offsets

# Let's look at the structure more carefully
print('\nHeader analysis:')
for i in range(0, 64, 4):
    val = struct.unpack_from('<I', content, i)[0]
    print('  Offset 0x{:02X}: 0x{:08X} ({})'.format(i, val, val))

# Search for specific play name patterns
# The user mentioned: "mem iso 3 go", "90 fist 14 quick 2", "quick 1 chest"
search_patterns = [
    b'mem', b'iso', b'fist', b'quick', b'chest',
    b'horns', b'pistol', b'flex', b'motion',
    b'pick', b'roll', b'isolation', b'triangle',
    b'princeton', b'alley', b'drive', b'post',
    b'screen', b'cut', b'spot', b'corner',
]

print('\nSearching for play-related strings:')
for pattern in search_patterns:
    idx = 0
    found = 0
    while found < 10:
        idx = content.lower().find(pattern, idx)
        if idx == -1:
            break
        # Extract surrounding context as ASCII
        start = max(0, idx - 10)
        end = min(len(content), idx + 50)
        ctx = content[start:end]
        ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
        print('  0x{:X}: ...{}...'.format(idx, ascii_ctx))
        found += 1
        idx += 1
