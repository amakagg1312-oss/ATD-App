import struct

data = open('RosterNBA0004', 'rb').read(100)
print('First 20 bytes:', data[:20])
print('Header:', data[:4])
print('Is EBNH:', data[:4] == b'EBNH')