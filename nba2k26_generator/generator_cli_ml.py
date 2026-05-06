# ML-based attribute generation using NBA Site data directly
import re
import unicodedata
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

try:
    from nba2k26_generator.ml import AttributeGenerator
    from nba2k26_generator.ml.data_loader import (
        merge_season_data,
        normalize_name,
    )
    from nba2k26_generator.ml.feature_engineering import (
        engineer_features,
        get_feature_columns,
        detect_position_group,
    )

    ML_AVAILABLE = True
except Exception as e:
    ML_AVAILABLE = False
    ML_LOAD_ERROR = str(e)

try:
    from nba2k26_generator.roles import (
        assign_roles,
        apply_role_boosts,
        load_role_catalog,
    )
    ROLES_AVAILABLE = True
except Exception:
    ROLES_AVAILABLE = False

# Import compute_overall_rating for OVR calculation
try:
    from nba2k26_generator.generator_cli import (
        compute_overall_rating,
        compute_attribute_family_averages,
    )
except ImportError:
    compute_overall_rating = None
    compute_attribute_family_averages = None


# Cache for merged+engineered season data (avoid re-loading CSVs)
_season_cache: Dict[str, pd.DataFrame] = {}

# Cache for committee attribute floors
_committee_floors_cache: Optional[Dict[str, Dict[str, int]]] = None


def _load_committee_floors() -> Dict[str, Dict[str, int]]:
    """Load NBA 2K27 ATD Committee attributes from the Excel file.

    Returns dict mapping player_name -> {attribute_name: value}
    """
    global _committee_floors_cache
    if _committee_floors_cache is not None:
        return _committee_floors_cache

    _committee_floors_cache = {}

    try:
        # Try multiple possible locations for the Excel file
        import os
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "Player Roles", "attributes two.xlsx"),
            os.path.join(os.getcwd(), "Player Roles", "attributes two.xlsx"),
        ]

        excel_path = None
        for c in candidates:
            if os.path.exists(c):
                excel_path = c
                break

        if excel_path is None:
            return _committee_floors_cache

        df = pd.read_excel(excel_path, header=None)

        # Row 4 has the attribute names (header row)
        attr_names = df.iloc[4].tolist()

        # Map committee column names to our internal attribute names
        name_map = {
            "Driving Layup": "Driving Layup",
            "Standing Dunk": "Standing Dunk",
            "Driving Dunk": "Driving Dunk",
            "Close Shot": "Close Shot",
            "Mid-Range Shot": "Mid-Range Shot",
            "Three-Point Shot": "Three-Point Shot",
            "Free Thow": "Free Throw",
            "Free Throw": "Free Throw",
            "Post Hook": "Post Hook",
            "Post Fade": "Post Fade",
            "Post Control": "Post Control",
            "Draw Foul": "Draw Foul",
            "Shot IQ": "Shot IQ",
            "Ball Handle": "Ball Handle",
            "Speed with Ball": "Speed with Ball",
            "Hands": "Hands",
            "Pass Accuracy": "Pass Accuracy",
            "Pass IQ": "Pass IQ",
            "Pass Vision": "Pass Vision",
            "Offensive Consistency": "Offensive Consistency",
            "Interior Defense": "Interior Defense",
            "Perimeter Defense": "Perimeter Defense",
            "Steal": "Steal",
            "Block": "Block",
            "Offensive Rebound": "Offensive Rebound",
            "Defensive Rebound": "Defensive Rebound",
            "Help Defense IQ": "Help Defense IQ",
            "Pass Perception": "Pass Perception",
            "Defensive Consistency": "Defensive Consistency",
            "Speed": "Speed",
            "Agility": "Agility",
            "Strength": "Strength",
            "Vertical": "Vertical",
            "Stamina\n(Second To last)": "Stamina",
            "Stamina": "Stamina",
            "Intangibles\n(Last)": "Intangibles",
            "Intangibles": "Intangibles",
            "Hustle": "Hustle",
        }

        # Parse each row: col 0 = OVR, col 1 = player name, cols 2+ = attributes
        for idx in range(5, len(df)):
            row = df.iloc[idx]
            player_name = str(row.iloc[1]).strip()
            if not player_name or player_name == "nan":
                continue

            attrs = {}
            for col_idx in range(2, min(len(row), len(attr_names))):
                attr_name_raw = attr_names[col_idx]
                if pd.isna(attr_name_raw):
                    continue
                attr_name_raw = str(attr_name_raw).strip()
                mapped_name = name_map.get(attr_name_raw, attr_name_raw)

                val = row.iloc[col_idx]
                if pd.notna(val):
                    try:
                        attrs[mapped_name] = int(float(val))
                    except (ValueError, TypeError):
                        pass

            if attrs:
                normalized_name = unicodedata.normalize("NFKD", player_name.lower()).encode("ascii", "ignore").decode("ascii")
                _committee_floors_cache[normalized_name] = attrs

    except Exception:
        pass

    return _committee_floors_cache


def _apply_committee_floors(
    attributes: Dict[str, int],
    player_name: str,
    season: str = "",
) -> Dict[str, int]:
    """Apply committee correction when ML is off by 10+ points.

    Only for 2025-26 season. If the committee value is 10+ points higher
    than the ML prediction, use the committee value. Otherwise keep ML.
    Shot IQ always uses the sheet value regardless of difference.
    """
    # Only apply for 2025-26 season
    season_str = str(season).strip().lower()
    if "2025-26" not in season_str and "2025_26" not in season_str:
        return attributes

    floors = _load_committee_floors()
    normalized_name = unicodedata.normalize("NFKD", player_name.lower()).encode("ascii", "ignore").decode("ascii")
    player_floors = floors.get(normalized_name)
    if not player_floors:
        return attributes

    result = dict(attributes)
    for attr_name, committee_val in player_floors.items():
        # Check both canonical and snake_case keys
        current = attributes.get(attr_name)
        if current is None:
            norm_key = re.sub(r"[^a-z0-9]+", "_", attr_name.strip().lower()).strip("_")
            current = attributes.get(norm_key)

        if current is not None:
            # Shot IQ always uses sheet value
            if attr_name == "Shot IQ":
                result[attr_name] = committee_val
                norm_key = re.sub(r"[^a-z0-9]+", "_", attr_name.strip().lower()).strip("_")
                result[norm_key] = committee_val
            # If ML is off by 10+ points, use committee value
            elif committee_val - current >= 10:
                result[attr_name] = committee_val
                norm_key = re.sub(r"[^a-z0-9]+", "_", attr_name.strip().lower()).strip("_")
                result[norm_key] = committee_val

    return result


def _force_shot_iq_from_sheet(
    attributes: Dict[str, int],
    player_name: str,
    season: str = "",
) -> Dict[str, int]:
    """Force Shot IQ to exactly match the committee sheet value.

    This is applied AFTER role boosts to ensure the sheet value is not
    overwritten by role-based +1/+2 boosts.
    """
    season_str = str(season).strip().lower()
    if "2025-26" not in season_str and "2025_26" not in season_str:
        return attributes

    floors = _load_committee_floors()
    normalized_name = unicodedata.normalize("NFKD", player_name.lower()).encode("ascii", "ignore").decode("ascii")
    player_floors = floors.get(normalized_name)
    if not player_floors:
        return attributes

    committee_val = player_floors.get("Shot IQ")
    if committee_val is None:
        return attributes

    result = dict(attributes)
    result["Shot IQ"] = committee_val
    norm_key = re.sub(r"[^a-z0-9]+", "_", "Shot IQ".strip().lower()).strip("_")
    result[norm_key] = committee_val

    return result


def _get_engineered_season(season: str) -> pd.DataFrame:
    """Load and engineer features for a season from NBA Site CSVs.

    Results are cached so repeated calls for the same season are fast.
    """
    if season in _season_cache:
        return _season_cache[season]

    merged = merge_season_data(season)
    if merged.empty:
        return pd.DataFrame()

    # Ensure name_normalized column exists (merge_season_data creates _name_norm)
    if "name_normalized" not in merged.columns and "_name_norm" in merged.columns:
        merged["name_normalized"] = merged["_name_norm"]

    engineered = engineer_features(merged)

    # Carry name_normalized through
    if (
        "name_normalized" not in engineered.columns
        and "name_normalized" in merged.columns
    ):
        engineered["name_normalized"] = merged["name_normalized"].values

    _season_cache[season] = engineered
    return engineered


def compute_attributes_ml(
    row: Dict[str, Any],
    tendencies: List[Any],
    player_roles_dir: str,
    all_rows: Optional[List[Dict[str, Any]]] = None,
    badges_txt_path: str = "",
) -> Dict[str, Any]:
    """Compute player attributes using pure ML models + role system.

    Reads directly from NBA Site CSV data (same source as training)
    to guarantee zero feature mismatch between training and inference.

    Returns dict with keys: attributes, roles, unicorn_role, ovr
    """
    if not ML_AVAILABLE:
        return {"attributes": {}, "roles": [], "unicorn_role": None, "ovr": 50}

    try:
        # Initialize ML generator
        generator = AttributeGenerator()
        if not generator.load_models():
            return {"attributes": {}, "roles": [], "unicorn_role": None, "ovr": 50}

        # Determine player name and season
        player_name = str(row.get("player_name", row.get("Player", ""))).strip()
        season = str(row.get("season_label", row.get("season", "2024-25"))).strip()

        # Load engineered features from NBA Site CSVs
        engineered = _get_engineered_season(season)
        if engineered.empty:
            return {"attributes": {}, "roles": [], "unicorn_role": None, "ovr": 50}

        # Look up this player by normalized name
        player_norm = normalize_name(player_name)
        player_mask = engineered["name_normalized"] == player_norm
        player_rows = engineered[player_mask]

        if player_rows.empty:
            return {"attributes": {}, "roles": [], "unicorn_role": None, "ovr": 50}

        player_row = player_rows.iloc[0]

        # Get position
        position = str(row.get("position", row.get("pos", "SG")))
        pos_group = detect_position_group(position)

        # Extract feature columns (same as training)
        feature_cols = generator.feature_columns
        if not feature_cols:
            feature_cols = get_feature_columns(engineered)

        # Build feature vector from the engineered row
        X = np.zeros(len(feature_cols))
        for i, col in enumerate(feature_cols):
            if col in player_row.index:
                val = player_row[col]
                if pd.notna(val):
                    try:
                        X[i] = float(val)
                    except (ValueError, TypeError):
                        pass

        # Predict using ML models
        try:
            attributes = generator.predictor.predict_attributes(
                X, position_group=pos_group
            )
        except Exception as e:
            print(f"Prediction error: {e}")
            return {"attributes": {}, "roles": [], "unicorn_role": None, "ovr": 50}

        # Apply committee floors - 70/30 blend for 2025-26 season only
        attributes = _apply_committee_floors(attributes, player_name, season)

        # Build stats dict from engineered features for role assignment
        # Map raw column names to f_* format expected by assign_roles
        stats = {}

        def _sf(key: str, default: float = 0.0) -> float:
            """Safe float get from player_row."""
            try:
                val = player_row.get(key, default)
                v = float(val)
                return v if not pd.isna(v) else default
            except (ValueError, TypeError):
                return default

        gp = _sf("GP", 70.0)
        gp_tracking = _sf("GP_tracking_passing", 70.0)
        if gp_tracking <= 0:
            gp_tracking = gp

        stats["f_pg_pts"] = _sf("PTS", 0.0)
        stats["f_pg_reb"] = _sf("REB", 0.0)
        stats["f_pg_ast"] = _sf("AST", 0.0)
        stats["f_pg_stl"] = _sf("STL", 0.0)
        stats["f_pg_blk"] = _sf("BLK", 0.0)
        stats["f_pg_fga"] = _sf("FGA", 0.0)
        stats["f_pg_fg3a"] = _sf("FG3A", 0.0)
        stats["f_pg_fg3m"] = _sf("FG3M", 0.0)
        stats["f_pg_fta"] = _sf("FTA", 0.0)
        stats["f_pg_fgm"] = _sf("FGM", 0.0)

        # Advanced stats (handle 0-1 vs percentage format)
        usg_raw = _sf("USG_PCT", 0.0)
        stats["f_usg"] = usg_raw * 100 if usg_raw < 1 else usg_raw

        ast_pct_raw = _sf("AST_PCT", 0.0)
        stats["f_ast_pct"] = ast_pct_raw * 100 if ast_pct_raw < 1 else ast_pct_raw

        tov_pct_raw = _sf("E_TOV_PCT", 0.0)
        stats["f_tov_pct"] = tov_pct_raw * 100 if tov_pct_raw < 1 else tov_pct_raw

        stats["f_ts_pct"] = _sf("TS_PCT", 0.0)
        stats["f_fg_pct"] = _sf("FG_PCT", 0.0)
        stats["f_fg3_pct"] = _sf("FG3_PCT", 0.0)
        stats["f_ft_pct"] = _sf("FT_PCT", 0.0)

        # Tracking stats (per-game)
        stats["f_drives_pg"] = _sf("DRIVES", 0.0) / gp_tracking
        stats["f_paint_touch_pg"] = _sf("PAINT_TOUCHES", 0.0) / gp_tracking
        stats["f_touches_pg"] = _sf("TOUCHES", 0.0) / gp_tracking
        stats["f_deflections_pg"] = _sf("DEFLECTIONS", 0.0) / gp_tracking
        stats["f_contested_pg"] = _sf("CONTESTED_SHOTS", 0.0) / gp_tracking
        stats["f_boxouts_pg"] = _sf("DEF_BOXOUTS", 0.0) / gp_tracking
        stats["f_pot_ast_pg"] = _sf("POTENTIAL_AST", 0.0) / gp_tracking

        # Playtype stats
        stats["f_isolation_poss_pct"] = _sf("POSS_PCT_playtype_isolation", 0.0)
        stats["f_spot_up_poss_pct"] = _sf("POSS_PCT_playtype_spot_up", 0.0)

        # Catch-and-shoot / pull-up
        stats["f_cs_fg3a_pg"] = _sf("CATCH_SHOOT_FG3A", 0.0) / gp_tracking
        stats["f_pu_fg3a_pg"] = _sf("PULL_UP_FG3A", 0.0) / gp_tracking

        # Assign roles using ML attributes + NBA stats
        if ROLES_AVAILABLE:
            roles, unicorn_role, corrected_attrs = assign_roles(attributes, stats, position)
            # Apply role boosts to attributes (uses corrected_attrs from outlier correction)
            attributes = apply_role_boosts(corrected_attrs, roles, unicorn_role)
        else:
            roles = determine_roles_from_attributes(attributes)
            unicorn_role = None

        # Force Shot IQ from committee sheet AFTER role boosts
        attributes = _force_shot_iq_from_sheet(attributes, player_name, season)

        # Compute overall
        overall = generator.predictor.predict_overall(attributes)
        attributes["Overall"] = overall
        attributes.pop("Overall", None)

        # Normalize attribute keys
        normalized_attrs = {}
        for key, val in attributes.items():
            norm_key = re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")
            normalized_attrs[key] = val
            normalized_attrs[norm_key] = val

        # Calculate overall rating
        family_scores = compute_attribute_family_averages(normalized_attrs) if compute_attribute_family_averages else {}
        ovr = (
            compute_overall_rating(position, normalized_attrs, family_scores)
            if compute_overall_rating
            else 75
        )

        return {
            "attributes": normalized_attrs,
            "roles": roles,
            "unicorn_role": unicorn_role,
            "ovr": ovr,
        }

    except Exception as e:
        print(f"ML generation error: {e}")
        return {"attributes": {}, "roles": [], "unicorn_role": None, "ovr": 50}


def generate_player_attributes(
    player_name: str,
    season: str = "2024-25",
    position: Optional[str] = None,
) -> Dict[str, int]:
    """Generate attributes for a player directly from NBA Site CSV data.

    This is the primary inference entry point. It reads from the exact same
    CSV files used during training, guaranteeing zero feature mismatch.

    Args:
        player_name: Player's full name (e.g., "Stephen Curry")
        season: NBA season (e.g., "2024-25")
        position: Override position (auto-detected if None)

    Returns:
        Dict mapping attribute names to integer values (25-99)
    """
    if not ML_AVAILABLE:
        raise RuntimeError("ML models not available")

    # Load and engineer features from NBA Site CSVs
    engineered = _get_engineered_season(season)
    if engineered.empty:
        raise ValueError(f"No NBA Site data found for season {season}")

    # Look up player
    player_norm = normalize_name(player_name)
    player_mask = engineered["name_normalized"] == player_norm
    player_rows = engineered[player_mask]

    if player_rows.empty:
        raise ValueError(f"Player '{player_name}' not found in {season} NBA Site data")

    player_row = player_rows.iloc[0]

    # Detect position
    if position is None:
        pos_col = None
        for c in ["POSITION", "pos", "position"]:
            if c in player_row.index and pd.notna(player_row[c]):
                position = str(player_row[c])
                break
        if position is None:
            position = "SG"

    pos_group = detect_position_group(position)

    # Load model
    generator = AttributeGenerator()
    if not generator.load_models():
        raise RuntimeError("Failed to load ML models")

    feature_cols = generator.feature_columns
    if not feature_cols:
        feature_cols = get_feature_columns(engineered)

    # Build feature vector
    X = np.zeros(len(feature_cols))
    for i, col in enumerate(feature_cols):
        if col in player_row.index:
            val = player_row[col]
            if pd.notna(val):
                try:
                    X[i] = float(val)
                except (ValueError, TypeError):
                    pass

    # Predict
    attributes = generator.predictor.predict_attributes(X, position_group=pos_group)

    # Add physical/mental defaults
    overall = generator.predictor.predict_overall(attributes)
    attributes["Overall"] = overall

    return attributes


def generate_player_badges(
    player_name: str,
    season: str = "2024-25",
    position: Optional[str] = None,
    attrs: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    """Generate badges for a player from NBA Site CSV data + ML attributes.

    Args:
        player_name: Player's full name
        season: NBA season
        position: Override position
        attrs: Pre-computed attributes (if None, will compute them)

    Returns:
        List of badge dicts: [{"name": str, "tier": str, "score": float}, ...]
    """
    from nba2k26_generator.badges import compute_badges

    # Get engineered stats
    engineered = _get_engineered_season(season)
    if engineered.empty:
        raise ValueError(f"No NBA Site data found for season {season}")

    player_norm = normalize_name(player_name)
    player_mask = engineered["name_normalized"] == player_norm
    player_rows = engineered[player_mask]
    if player_rows.empty:
        raise ValueError(f"Player '{player_name}' not found in {season}")

    player_row = player_rows.iloc[0]

    # Get position
    if position is None:
        for c in ["POSITION", "pos", "position"]:
            if c in player_row.index and pd.notna(player_row[c]):
                position = str(player_row[c])
                break
        if position is None:
            position = "SG"

    # Get attributes if not provided
    if attrs is None:
        attrs = generate_player_attributes(player_name, season, position)

    # Convert player row to stats dict for badge scoring
    stats = {}
    for col in player_row.index:
        val = player_row[col]
        if pd.notna(val):
            try:
                stats[col] = float(val)
            except (ValueError, TypeError):
                stats[col] = val

    return compute_badges(attrs, stats, position)


def generate_player_full(
    player_name: str,
    season: str = "2024-25",
    position: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate full player profile: attributes + badges + roles.

    Args:
        player_name: Player's full name
        season: NBA season
        position: Override position

    Returns:
        Dict with keys: attributes, badges, roles, unicorn_role, position
    """
    attrs = generate_player_attributes(player_name, season, position)

    # Resolve position for role/badge generation
    if position is None:
        engineered = _get_engineered_season(season)
        player_norm = normalize_name(player_name)
        player_rows = engineered[engineered["name_normalized"] == player_norm]
        if not player_rows.empty:
            row = player_rows.iloc[0]
            for c in ["POSITION", "pos", "position"]:
                if c in row.index and pd.notna(row[c]):
                    position = str(row[c])
                    break
        if position is None:
            position = "SG"

    # Get engineered stats for role assignment
    engineered = _get_engineered_season(season)
    player_norm = normalize_name(player_name)
    player_rows = engineered[engineered["name_normalized"] == player_norm]
    stats = {}
    if not player_rows.empty:
        prow = player_rows.iloc[0]

        def _sf(key: str, default: float = 0.0) -> float:
            try:
                val = prow.get(key, default)
                v = float(val)
                return v if not pd.isna(v) else default
            except (ValueError, TypeError):
                return default

        gp_tracking = _sf("GP_tracking_passing", 70.0)
        if gp_tracking <= 0:
            gp_tracking = _sf("GP", 70.0)

        stats["f_pg_pts"] = _sf("PTS", 0.0)
        stats["f_pg_reb"] = _sf("REB", 0.0)
        stats["f_pg_ast"] = _sf("AST", 0.0)
        stats["f_pg_stl"] = _sf("STL", 0.0)
        stats["f_pg_blk"] = _sf("BLK", 0.0)
        stats["f_pg_fga"] = _sf("FGA", 0.0)
        stats["f_pg_fg3a"] = _sf("FG3A", 0.0)
        stats["f_pg_fg3m"] = _sf("FG3M", 0.0)
        stats["f_pg_fta"] = _sf("FTA", 0.0)
        stats["f_pg_fgm"] = _sf("FGM", 0.0)

        usg_raw = _sf("USG_PCT", 0.0)
        stats["f_usg"] = usg_raw * 100 if usg_raw < 1 else usg_raw

        ast_pct_raw = _sf("AST_PCT", 0.0)
        stats["f_ast_pct"] = ast_pct_raw * 100 if ast_pct_raw < 1 else ast_pct_raw

        tov_pct_raw = _sf("E_TOV_PCT", 0.0)
        stats["f_tov_pct"] = tov_pct_raw * 100 if tov_pct_raw < 1 else tov_pct_raw

        stats["f_ts_pct"] = _sf("TS_PCT", 0.0)
        stats["f_fg_pct"] = _sf("FG_PCT", 0.0)
        stats["f_fg3_pct"] = _sf("FG3_PCT", 0.0)
        stats["f_ft_pct"] = _sf("FT_PCT", 0.0)

        stats["f_drives_pg"] = _sf("DRIVES", 0.0) / gp_tracking
        stats["f_paint_touch_pg"] = _sf("PAINT_TOUCHES", 0.0) / gp_tracking
        stats["f_touches_pg"] = _sf("TOUCHES", 0.0) / gp_tracking
        stats["f_deflections_pg"] = _sf("DEFLECTIONS", 0.0) / gp_tracking
        stats["f_contested_pg"] = _sf("CONTESTED_SHOTS", 0.0) / gp_tracking
        stats["f_boxouts_pg"] = _sf("DEF_BOXOUTS", 0.0) / gp_tracking
        stats["f_pot_ast_pg"] = _sf("POTENTIAL_AST", 0.0) / gp_tracking

        stats["f_isolation_poss_pct"] = _sf("POSS_PCT_playtype_isolation", 0.0)
        stats["f_spot_up_poss_pct"] = _sf("POSS_PCT_playtype_spot_up", 0.0)

        stats["f_cs_fg3a_pg"] = _sf("CATCH_SHOOT_FG3A", 0.0) / gp_tracking
        stats["f_pu_fg3a_pg"] = _sf("PULL_UP_FG3A", 0.0) / gp_tracking

    # Assign roles and apply boosts
    unicorn_role = None
    if ROLES_AVAILABLE and stats:
        roles, unicorn_role, corrected_attrs = assign_roles(attrs, stats, position)
        attrs = apply_role_boosts(corrected_attrs, roles, unicorn_role)
    else:
        roles = determine_roles_from_attributes(attrs)

    badges = generate_player_badges(player_name, season, position, attrs)

    return {
        "attributes": attrs,
        "badges": badges,
        "roles": roles,
        "unicorn_role": unicorn_role,
        "position": position,
    }


# ── Helper functions (kept for backward compat) ───────────────────────


def _gv(row: Dict[str, Any], *keys, default=0.0) -> float:
    """Safely get a numeric value from a row dict."""
    for key in keys:
        if key in row:
            try:
                return float(row[key])
            except (ValueError, TypeError):
                pass
    return default


def extract_height_inches(row: Dict[str, Any]) -> float:
    """Extract height in inches from row."""
    h = row.get("height_inches", row.get("player_height_inches", 0))
    try:
        return float(h)
    except (ValueError, TypeError):
        pass

    h = _gv(row, "height_in", "player_info_ht_in_in")
    if h > 0:
        return h

    h_str = row.get("height", row.get("player_height", ""))
    if h_str and isinstance(h_str, str):
        match = re.match(r"(\d+)'(\d+)", h_str)
        if match:
            feet = int(match.group(1))
            inches = int(match.group(2))
            return feet * 12 + inches

    return 78


def extract_weight(row: Dict[str, Any]) -> float:
    """Extract weight in lbs from row."""
    w = _gv(row, "weight_lbs", "player_info_wt")
    if w > 0:
        return w
    return 200


def extract_experience(row: Dict[str, Any]) -> int:
    """Extract years of experience from row."""
    exp = row.get("experience", row.get("years_pro", 3))
    try:
        return int(float(exp))
    except (ValueError, TypeError):
        return 3


def determine_roles_from_attributes(attrs: Dict[str, Any]) -> List[str]:
    """Determine player roles based on attributes."""
    roles = []

    shooting = attrs.get("Three-Point Shot", attrs.get("three_point_shot", 50))
    playmaking = attrs.get(
        "Pass Vision", attrs.get("pass_vision", attrs.get("Ball Handle", 50))
    )
    finishing = attrs.get(
        "Driving Dunk", attrs.get("driving_dunk", attrs.get("Close Shot", 50))
    )
    defense = attrs.get(
        "Interior Defense",
        attrs.get("interior_defense", attrs.get("Perimeter Defense", 50)),
    )
    rebounding = attrs.get(
        "Defensive Rebound",
        attrs.get("defensive_rebound", attrs.get("Offensive Rebound", 50)),
    )

    if playmaking > 65 and attrs.get("Speed", 50) > 60:
        roles.append("Floor General")
    elif playmaking > 55 and shooting > 55:
        roles.append("Scoring PG")

    if shooting > 60 and finishing > 55:
        roles.append("3&D")
    elif shooting > 65:
        roles.append("Spot Up Shooter")

    if attrs.get("Mid-Range Shot", 50) > 55 and finishing > 50:
        roles.append("Mid-Range Specialist")

    if rebounding > 65:
        roles.append("Glass Cleaner")
    if finishing > 70 and defense > 55:
        roles.append("Rim Protector")
    if attrs.get("Post Control", attrs.get("Post Hook", 50)) > 60:
        roles.append("Post Scorer")

    if not roles:
        roles.append("Two-Way Player")

    return roles[:3]
