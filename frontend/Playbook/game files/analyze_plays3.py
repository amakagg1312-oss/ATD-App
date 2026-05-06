import struct

data = open('playdata_extracted/Plays.playdata', 'rb').read()
size = len(data)
print('File size:', size)

# Check END of file for strings (like we found before)
print('\nLast 100 bytes:', data[-100:])

# Look for UTF-16BE strings at end
print('\nSearching for UTF-16BE at end...')
for start in range(size - 10000, size - 100, 4):
    try:
        text = data[start:start+50].decode('utf-16-be', errors='ignore').strip('\x00')
        if len(text) > 5 and text.replace(' ', '').isalnum():
            print(f'At {start}: {text[:30]}')
            break
    except:
        pass

# Try reading as ASCII strings
print('\nSearching for ASCII strings at end...')
for start in range(size - 10000, size - 100, 4):
    try:
        text = data[start:start+50].decode('ascii', errors='ignore').strip('\x00')
        if len(text) > 5 and ' ' in text:
            print(f'At {start}: {text[:30]}')
            break
    except:
        pass