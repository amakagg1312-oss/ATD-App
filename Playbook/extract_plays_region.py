path = 'D:\\project\\Playbook\\game files\\playdata_extracted\\Plays.playdata'
with open(path, 'rb') as f:
    data = f.read()

# The play names are in the region around 0x42F000-0x431000
# They appear to be stored at every 2-byte offset, overlapping
# Let's extract from both even and odd offsets and find the longest unique strings

start_region = 0x42F000
end_region = 0x432000

region = data[start_region:end_region]

# Extract strings from even offsets
even_strings = set()
for offset in range(0, len(region) - 8, 2):
    s = b''
    for j in range(offset, len(region)):
        if 32 <= region[j] < 127:
            s += bytes([region[j]])
        else:
            break
    if len(s) >= 10:
        decoded = s.decode('ascii', errors='ignore')
        # Check if it looks like a play name
        letter_count = sum(1 for c in decoded if c.isalpha() or c == ' ')
        if letter_count > len(decoded) * 0.6 and ' ' in decoded:
            even_strings.add(decoded)

# Filter out substrings
filtered = set()
for name in sorted(even_strings):
    is_sub = False
    for other in even_strings:
        if name != other and name in other:
            is_sub = True
            break
    if not is_sub:
        filtered.add(name)

print('Found {} unique play names:\n'.format(len(filtered)))
for name in sorted(filtered):
    print('  {}'.format(name))
