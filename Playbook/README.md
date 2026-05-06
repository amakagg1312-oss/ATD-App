# NBA 2K26 Playbook Offset Finder

## Overview
This tool finds the exact memory offsets where playbook data is stored in NBA 2K26 by comparing team dumps from the running game.

## Files
- `team_dumper.py` - Connects to NBA2K26.exe and dumps a team's data to a .bin file
- `playbook_finder.py` - Compares two team dumps and identifies playbook offsets
- `2k26_offsets.json` - Copied from parent directory for offset references

## Workflow

### Step 1: Launch the game
Start NBA2K26 and navigate to a roster edit screen (Play Now → Edit Roster → pick a team).

### Step 2: Dump team with Playbook A
```bash
python team_dumper.py --team MIL --output playbook_A.bin
```

### Step 3: Change playbook in-game
In the roster editor, change the Bucks' playbook to something different.

### Step 4: Dump team with Playbook B
```bash
python team_dumper.py --team MIL --output playbook_B.bin
```

### Step 5: Compare dumps
```bash
python playbook_finder.py playbook_A.bin playbook_B.bin --show-all --output playbook_offsets.json
```

This will show you exactly which bytes changed - those are the playbook offsets!

## Available Teams
Common abbreviations:
- MIL (Bucks), LAL (Lakers), GSW (Warriors), BOS (Celtics)
- PHI (76ers), DEN (Nuggets), MIA (Heat), ATL (Hawks)
- DAL (Mavericks), PHX (Suns), BRK (Nets), CHI (Bulls)

You can also search by name: `--team Lakers`, `--team Boston`, etc.

## List all teams
```bash
python team_dumper.py --list
```

## Notes
- Run as Administrator (required for memory reading)
- Game must be in an editable roster screen
- Team struct size: 5672 bytes
- If offsets change after a game patch, update 2k26_offsets.json
