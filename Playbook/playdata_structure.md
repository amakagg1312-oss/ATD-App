# NBA 2K26 playdata.iff Structure

## File Info
- File: `playdata.iff` (ZIP archive containing `Plays.playdata`)
- Total size: 4,394,042 bytes

## Header (first 4 bytes)
- Value: 113 (0x71) = number of plays loaded

## Entry Structure (not fully determined)
- Unknown - could be 8-16 bytes per entry
- Contains play ID(s) and offset(s) to data

## Play Names (at end of file)
- Stored as UTF-16LE strings
- String table starts around offset 0x433000
- Names include team tags like "85 PHI 14 CUT", "01 LAL FIST 24 ANGLE", etc.

## Example Play Names from all_play_names.txt (12506 entries):
- Line 1: FIST "1-4" (offset 0x3BDA7C)
- Line 4: 00 CUT 3 RIP ALLEY
- Line 1947: 85 PHI 14 CUT (the play we see in-game)

## Play Index Mapping
- The game uses play INDEX (0-12506+) to reference plays
- Not direct file offsets - there's a lookup table/array
- Play index 14 maps to "85 PHI 14 CUT"

## Finding in Memory
- The play catalog appears to be loaded into memory
- When play changes in roster editor, NEW structures are created
- These structures at 0x24081240 area contain: count (1-5) + indices array