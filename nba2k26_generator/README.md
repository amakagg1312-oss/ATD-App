# NBA 2K26 Generator CLI (Milestone 1)

This is a first working milestone for the NBA 2K26 realism generator.

## What it does
- Loads all era CSV files from `Generator Database/`
- Handles semicolon-delimited data and decimal-comma numeric values
- Selects a specific player-season row (prefers aggregated `2TM` row when present)
- Computes an initial set of core tendencies from real stats
- Applies recommended and absolute caps (derived from your tendencies workbook)
- Prints a detailed report:
  - raw evidence metrics
  - pre-cap tendency value
  - cap-applied final tendency value

## Usage

From workspace root:

```powershell
python nba2k26_generator/generator_cli.py --player "Giannis Antetokounmpo" --season "2025-26"
```

Optional:

```powershell
python nba2k26_generator/generator_cli.py --player "Nikola Jokic" --season "2024-25" --database-dir "Generator Database"
```

## Notes
- This is an intentionally extendable baseline. More tendencies, archetype logic, badge logic, and UI layer come next.
- Current formulas are weighted heuristics designed for realism and can be tuned quickly as we validate outputs.
