import re
line = "  1: 1 = FIST \"1-4\""
match = re.match(r'^\s*(\d+):\s*(\d+)\s*=\s*(.+)$', line)
if match:
    print("Group 1:", match.group(1))
    print("Group 2:", match.group(2))
    print("Group 3:", match.group(3))
else:
    print("No match")