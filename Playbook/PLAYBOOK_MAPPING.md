# NBA 2K26 Playbook Memory Mapping

## CONFIRMED VERIFIED MAPPING

### Memory Addresses (Verified April 2026)

| Component | Address | Notes |
|----------|---------|-------|
| Play String Block | 0x2FFCD8000 | Contains ~1731 play names as UTF-16LE |
| 76ers Playbook Base | 0x2FFCA19D0 | 60 plays at stride 0x30 |
| Stride | 0x30 (48 bytes) | Each play entry is 48 bytes |

### Data Structure

Each play entry (48 bytes):
- **Bytes 0-3**: Offset (4 bytes, little-endian) - Points into play string block
- **Bytes 4+**: Unused or other game data

To read a play name:
1. Read 4-byte offset at `playbook_base + (index * 0x30)`
2. Add offset to `play_string_base` (0x2FFCD8000)
3. Read UTF-16LE string from that address

### Example: Reading 76ers Playbook

```
Playbook Base: 0x2FFCA19D0
Stride: 0x30 (48 bytes)

Index 0: offset 2252 -> "FIST 64 STS"
Index 1: offset 1352 -> "CLE FIST 15 DRA"
Index 2: offset 1133 -> "SAS FIST 15 FLAT OU"
Index 3: offset 557 -> "FIST 21 IVERSON"
Index 4: offset 742 -> "FIST CHEST FLAR"
Index 5: offset 2591 -> "'06 POR FIST 15 U"
Index 6: offset 1245 -> "'16 MEM PUNCH 5 WEA"
Index 7: offset 3065 -> "'16 CHA PUNCH 3 DOW"
Index 8: offset 916 -> "MIL FIST 34 DOWN SLI"
Index 9: offset 2259 -> "FIST 64 STS"
... (continues to index 59)
```

### App Implementation Notes for Playbook Creation

To create/modify a playbook:
1. Find play name in string block (0x2FFCD8000) - get its byte offset
2. Write offset value to playbook array entry: offset = target_byte_offset (not absolute address)
3. Each team has its own playbook base address

### Finding Other Team Playbooks

Each team has different base address. To find:
1. Load team in roster editor
2. Search memory for known play names
3. Look for array of 60 x 4-byte offsets

### Script: read_76ers_playbook.py

Run: `python read_76ers_playbook.py`
- Reads from running NBA2K26.exe (PID 58172)
- Outputs plays to JSON
- Requires Administrator

### Files Generated

- `76ers_final.json` - 60 plays with offsets and names
- `read_76ers_playbook.py` - Script to read playbook