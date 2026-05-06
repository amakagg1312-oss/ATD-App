# NBA Site Data to Attribute Feature Mapping

This document defines a concrete mapping from `NBA Site data/*.csv` into a canonical per-player feature row that can drive attribute formulas.

## Scope

- Season: `2025-26 regular season` files in `NBA Site data/`
- Output grain: one row per player (`PLAYER_ID`) with optional team split handling.
- Primary objective: replace legacy `Generator Database/attribute_source_*.csv` dependency with a normalization layer.

## Data Quality Summary

- CSV files discovered: 39
- Core join key coverage:
  - `PLAYER_ID`: 34 files
  - `PLAYER_NAME`: 33 files
  - `TEAM_ID`: 29 files
- High-coverage core files (`>= 560` players): 22
- Intersection across high-coverage core files: 569 players
- Known schema issue:
  - `player_shooting_2025-26_regular_season.csv` has `efg_pct` fully missing
- Special-case join files:
  - `player_defense_dash_*` files are name-based and do not include `PLAYER_ID`

## Canonical Keying and Merge Rules

Use these canonical keys for merge:

1. `player_id` from `PLAYER_ID` (or `player_id` in lowercase schema files)
2. `player_name` from `PLAYER_NAME` (or `player_name`)
3. `team_id` from `TEAM_ID`
4. `team_abbreviation` from `TEAM_ABBREVIATION`

Merge order:

1. Start from `player_traditional_2025-26_regular_season.csv` as base table.
2. Left-join all wide player tables by `PLAYER_ID`.
3. For files with repeated `PLAYER_ID` rows (mostly playtypes/shot dashboards), aggregate to one row per `PLAYER_ID` first.
4. For `player_defense_dash_*` files, join by normalized player name as fallback only.

## Aggregation Rules for Repeated PLAYER_ID Rows

Apply before merge:

1. Sum-like columns:
  - Ends with or contains: `_M`, `_A`, `PTS`, `AST`, `POSS`, `FGM`, `FGA`, `FG3M`, `FG3A`, `FTA`, `FTM`
  - Aggregate by `sum`
2. Rate/percentage columns:
  - Contains: `PCT`, `RATE`, `RATIO`, `AVG`
  - Aggregate by weighted average using `POSS` if present, else `GP`, else simple mean
3. Identifier/meta columns:
  - Keep first non-empty value

## Feature Mapping by Formula Family

The left side is the canonical feature target. The right side is source column(s).

### Identity and Bio

- `player_id` <= `player_traditional.PLAYER_ID`
- `player_name` <= `player_traditional.PLAYER_NAME`
- `age` <= `player_bio.AGE` fallback `player_traditional.AGE`
- `height_in` <= `player_bio.PLAYER_HEIGHT_INCHES`
- `weight_lbs` <= `player_bio.PLAYER_WEIGHT`
- `per_game_g` <= `player_traditional.GP`
- `per_game_mp_per_game` <= `player_traditional.MIN`

### Traditional Box Production

- `per_game_pts_per_game` <= `player_traditional.PTS`
- `per_game_ast_per_game` <= `player_traditional.AST`
- `per_game_tov_per_game` <= `player_traditional.TOV`
- `per_game_stl_per_game` <= `player_traditional.STL`
- `per_game_blk_per_game` <= `player_traditional.BLK`
- `per_game_fga_per_game` <= `player_traditional.FGA`
- `per_game_fg_percent` <= `player_traditional.FG_PCT`
- `per_game_x3pa_per_game` <= `player_traditional.FG3A`
- `per_game_x3p_percent` <= `player_traditional.FG3_PCT`
- `per_game_fta_per_game` <= `player_traditional.FTA`
- `per_game_ft_percent` <= `player_traditional.FT_PCT`

### Advanced / Usage

- `advanced_usg_percent` <= `player_advanced.USG_PCT`
- `advanced_ast_percent` <= `player_advanced.AST_PCT`
- `advanced_tov_percent` <= `player_advanced.E_TOV_PCT` fallback `player_usage.PCT_TOV`
- `advanced_orb_percent` <= `player_advanced.OREB_PCT`
- `advanced_drb_percent` <= `player_advanced.DREB_PCT`
- `advanced_stl_percent` <= `player_usage.PCT_STL`
- `advanced_blk_percent` <= `player_usage.PCT_BLK`
- `advanced_ts_percent` <= `player_advanced.TS_PCT`

### Scoring Profile and Shot Diet

- `shooting_percent_fga_from_x0_3_range` <= `player_shooting_by_zone.restricted_area_fga / traditional.FGA`
- `shooting_percent_fga_from_x3_10_range` <= `player_shooting_by_zone.in_the_paint_non_ra_fga / traditional.FGA`
- `shooting_percent_fga_from_x10_16_range` <= `player_shooting_by_zone.mid_range_fga / traditional.FGA`
- `shooting_percent_fga_from_x16_3p_range` <= `player_scoring.PCT_PTS_2PT_MR` (proxy when exact zone split unavailable)
- `shooting_percent_fga_from_x3p_range` <= `player_scoring.PCT_FGA_3PT`
- `shooting_fg_percent_from_x0_3_range` <= `player_shooting_by_zone.restricted_area_fg_pct`
- `shooting_fg_percent_from_x10_16_range` <= `player_shooting_by_zone.mid_range_fg_pct`
- `shooting_num_of_dunks` <= derived from `player_scoring.PCT_PTS_PAINT * PTS` and `tracking` proxies if direct not present

### Tracking and Movement

- `tracking_avg_speed` <= `player_tracking_speed_distance.AVG_SPEED`
- `tracking_avg_speed_off` <= `player_tracking_speed_distance.AVG_SPEED_OFF`
- `tracking_avg_speed_def` <= `player_tracking_speed_distance.AVG_SPEED_DEF`
- `tracking_drives` <= `player_tracking_drives.DRIVES`
- `tracking_drive_fg_pct` <= `player_tracking_drives.DRIVE_FG_PCT`
- `tracking_pull_up_3pa` <= `player_tracking_pullup.PULL_UP_FG3A`
- `tracking_pull_up_3p_pct` <= `player_tracking_pullup.PULL_UP_FG3_PCT`
- `tracking_catch_shoot_3pa` <= `player_tracking_catch_shoot.CATCH_SHOOT_FG3A`
- `tracking_catch_shoot_3p_pct` <= `player_tracking_catch_shoot.CATCH_SHOOT_FG3_PCT`
- `tracking_passes_made` <= `player_tracking_passing.PASSES_MADE`
- `tracking_potential_ast` <= `player_tracking_passing.POTENTIAL_AST`

### Defense and Hustle

- `advanced_dws` <= `player_defense.DEF_WS`
- `advanced_dbpm` <= not directly available in current scrape; proxy from `DEF_RATING`, `PCT_STL`, `PCT_BLK`
- `defense_rating` <= `player_defense.DEF_RATING`
- `hustle_deflections` <= `player_hustle.DEFLECTIONS`
- `hustle_contested_2pt` <= `player_hustle.CONTESTED_SHOTS_2PT`
- `hustle_contested_3pt` <= `player_hustle.CONTESTED_SHOTS_3PT`

## Legacy Key Compatibility Layer

Current generator formulas expect legacy keys like:

- `per_game_x3pa_per_game`
- `advanced_usg_percent`
- `shooting_percent_fga_from_x0_3_range`
- `pbp_features_*`

Recommendation:

1. Normalize NBA Site data into canonical keys above.
2. Add a compatibility adapter that writes legacy key aliases from canonical features.
3. For unavailable pbp-only keys (`pbp_features_*`), use tracking/playtype proxies and explicit fallbacks.

## Gaps to Address Before Full Formula Remake

1. No direct `pbp_features_*` columns in scrape.
2. `DBPM` missing as direct stat.
3. Some dashboard files are long-form buckets and require pivot.
4. `player_shooting.efg_pct` is unusable (100% missing).

## Readiness Verdict

This dataset is sufficient to remake all major attribute formulas if a robust normalization layer is added first. The only blocker is schema adaptation, not lack of usable signal.
