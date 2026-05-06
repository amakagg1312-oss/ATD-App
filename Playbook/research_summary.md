# NBA 2K26 Playbook Memory Research

## Found Addresses
- 76ers Team: 0x2a818000 (stride 5672)
- Team playbook count fields: +0x33c, +0x340, +0x348 - but values don't seem to control display
- Multiple playbook structures with count+indices found in 0x24000000 - 0x25000000 range
- Play index 14 maps to "85 PHI 14 CUT" (in all_play_names.txt line 1947, offset 0x3E1942)

## What Didn't Work
- Writing to count fields in team data doesn't change what's shown in roster editor
- Writing to 0x2e40xxxx playbooks doesn't affect display
- Team data shows weird values: +0x33c = 25768, +0x340 = 3800039424 (0xe2800000)

## Key Finding
- When the play was changed, NEW playbook structures appeared at new addresses (0x24081240 area)
- But writing to those didn't change display either
- This suggests the data is either:
  1. Recreated each time the screen is opened
  2. There's a separate lookup/catalog
  3. The editor uses a different memory region

## Files Analyzed
- RosterNBA0020: 5.3MB, compressed with 'EBNH' header
- playdata.iff: 1.8MB play catalog
- playcatalog.iff: UI catalog (152KB)

## Next Steps Recommended
1. Use Cheat Engine: Open Cheat Engine, search for value 14 while in roster editor, then change play
2. Try in-game playcall instead of roster editor
3. The playbook data might be validated on-display using a play catalog lookup