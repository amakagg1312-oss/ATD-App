path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

# Look at the raw bytes around 0x42F9E8 where we saw "DRIVE 2 D"
start = 0x42F9E0
end = 0x430100

region = data[start:end]

# Print hex dump with ASCII
print('Hex dump of play name region (0x{:X} - 0x{:X}):\n'.format(start, end))
for i in range(0, len(region), 16):
    hex_str = ' '.join('{:02X}'.format(b) for b in region[i:i+16])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in region[i:i+16])
    print('0x{:06X}: {:48s} {}'.format(start + i, hex_str, ascii_str))
