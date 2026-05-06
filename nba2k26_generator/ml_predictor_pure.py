"""Pure Python ML predictor using exported tree models.

No sklearn/pandas imports. Reads:
- models_export.json: exported tree models + scalers
- ml_feature_stats.json: pre-computed feature statistics for percentiles

Usage:
    from ml_predictor_pure import predict_attributes
    attrs = predict_attributes(row, all_rows, position)
"""
import json
import math
import os
import bisect

_MODELS = None
_FEATURE_NAMES = None
_FEATURE_STATS = None

def _load_json(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def _get_models():
    global _MODELS
    if _MODELS is None:
        _MODELS = _load_json("models_export.json")
    return _MODELS

def _get_feature_names():
    global _FEATURE_NAMES
    if _FEATURE_NAMES is None:
        _FEATURE_NAMES = _load_json("ml_feature_names.json")
    return _FEATURE_NAMES

def _get_feature_stats():
    global _FEATURE_STATS
    if _FEATURE_STATS is None:
        _FEATURE_STATS = _load_json("ml_feature_stats.json")
    return _FEATURE_STATS

def sf(v, default=0.0):
    """Safe float conversion."""
    try:
        f = float(str(v or "").strip())
        return f if f == f else default
    except Exception:
        return default

def _get_nested(row, *keys):
    """Get value from row, trying multiple keys."""
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() and str(v).strip().lower() not in ("", "nan", "none", "na"):
            return v
    # Also try lowercase versions
    for k in keys:
        v = row.get(k.lower())
        if v is not None and str(v).strip() and str(v).strip().lower() not in ("", "nan", "none", "na"):
            return v
    return None

def _compute_percentile(value, sorted_values):
    """Compute percentile rank using binary search on sorted values."""
    if not sorted_values:
        return 50.0
    # What percentage of values are less than this value
    idx = bisect.bisect_left(sorted_values, value)
    return (idx / len(sorted_values)) * 100.0

def compute_features(row, all_rows):
    """Compute 123 ML features from a player row.
    
    Args:
        row: player data dict (merged from all CSVs)
        all_rows: all player rows for percentile computation
    
    Returns:
        List of 123 feature values
    """
    gp = sf(_get_nested(row, "GP", "gp", "per_game_g"), 1.0)
    if gp <= 0:
        gp = 1.0
    
    # Per-game stats
    pts = sf(_get_nested(row, "PTS", "pts", "per_game_pts_per_game"))
    reb = sf(_get_nested(row, "REB", "reb", "per_game_reb_per_game"))
    ast = sf(_get_nested(row, "AST", "ast", "per_game_ast_per_game"))
    stl = sf(_get_nested(row, "STL", "stl", "per_game_stl_per_game"))
    blk = sf(_get_nested(row, "BLK", "blk", "per_game_blk_per_game"))
    tov = sf(_get_nested(row, "TOV", "tov", "per_game_tov_per_game"))
    oreb = sf(_get_nested(row, "OREB", "oreb", "per_game_oreb_per_game"))
    dreb = sf(_get_nested(row, "DREB", "dreb", "per_game_dreb_per_game"))
    fgm = sf(_get_nested(row, "FGM", "fgm"))
    fga = sf(_get_nested(row, "FGA", "fga"))
    fg3m = sf(_get_nested(row, "FG3M", "fg3m"))
    fg3a = sf(_get_nested(row, "FG3A", "fg3a"))
    ftm = sf(_get_nested(row, "FTM", "ftm"))
    fta = sf(_get_nested(row, "FTA", "fta"))
    pf = sf(_get_nested(row, "PF", "pf", "per_game_pf_per_game"))
    pfd = sf(_get_nested(row, "PFD", "pfd"))
    
    mins = sf(_get_nested(row, "MIN", "min", "per_game_mp_per_game"), 30.0)
    mins_safe = max(mins, 0.1)
    
    # Per-36 stats
    p36_pts = pts / mins_safe * 36
    p36_reb = reb / mins_safe * 36
    p36_ast = ast / mins_safe * 36
    p36_blk = blk / mins_safe * 36
    p36_stl = stl / mins_safe * 36
    
    # Shooting percentages
    fg_pct = sf(_get_nested(row, "FG_PCT", "fg_pct", "per_game_fg_percent"))
    fg3_pct = sf(_get_nested(row, "FG3_PCT", "fg3_pct", "per_game_x3p_percent"))
    ft_pct = sf(_get_nested(row, "FT_PCT", "ft_pct", "per_game_ft_percent"))
    ts_pct = sf(_get_nested(row, "TS_PCT", "ts_pct", "advanced_ts_percent"))
    
    # Derived ratios
    fg3a_rate = fg3a / fga if fga > 0 else 0.0
    ft_rate = fta / fga if fga > 0 else 0.0
    ast_tov = ast / tov if tov > 0 else ast
    
    # Advanced stats
    usg = sf(_get_nested(row, "USG_PCT", "usg_pct", "advanced_usg_percent"))
    ast_pct = sf(_get_nested(row, "AST_PCT", "ast_pct", "advanced_ast_percent"))
    oreb_pct = sf(_get_nested(row, "OREB_PCT", "oreb_pct", "advanced_orb_percent"))
    dreb_pct = sf(_get_nested(row, "DREB_PCT", "dreb_pct", "advanced_drb_percent"))
    tov_pct = sf(_get_nested(row, "TOV_PCT", "tov_pct", "advanced_tov_percent"))
    
    # Tracking: Drives (merged data has season totals with _pg suffix, divide by GP)
    drives_raw = sf(_get_nested(row, "DRIVES"))
    drives_pg_val = sf(_get_nested(row, "tracking_drives_pg"))
    drives = drives_pg_val / gp if drives_pg_val > 0 else drives_raw / gp
    drive_fg = sf(_get_nested(row, "DRIVE_FG_PCT", "drive_fg_pct", "tracking_drive_fg_pct"))
    drive_ast = sf(_get_nested(row, "DRIVE_AST_PCT", "drive_ast_pct", "tracking_drive_ast_rate"))
    
    # Tracking: Touches (merged data has season totals with _pg suffix, divide by GP)
    touches_raw = sf(_get_nested(row, "TOUCHES"))
    touches_pg_val = sf(_get_nested(row, "tracking_touches_pg"))
    touches = touches_pg_val / gp if touches_pg_val > 0 else touches_raw / gp
    paint_touch_raw = sf(_get_nested(row, "PAINT_TOUCHES"))
    paint_touch_pg_val = sf(_get_nested(row, "tracking_paint_touches_pg"))
    paint_touch = paint_touch_pg_val / gp if paint_touch_pg_val > 0 else paint_touch_raw / gp
    pts_per_touch = sf(_get_nested(row, "PTS_PER_TOUCH", "pts_per_touch"))
    sec_per_touch = sf(_get_nested(row, "AVG_SEC_PER_TOUCH", "tracking_avg_sec_per_touch"))
    elbow_touch_raw = sf(_get_nested(row, "ELBOW_TOUCHES"))
    elbow_touch_pg_val = sf(_get_nested(row, "tracking_elbow_touches_pg"))
    elbow_touch = elbow_touch_pg_val / gp if elbow_touch_pg_val > 0 else elbow_touch_raw / gp
    
    # Tracking: Passing (merged data has season totals with _pg suffix, divide by GP)
    passes_raw = sf(_get_nested(row, "PASSES_MADE"))
    passes_pg_val = sf(_get_nested(row, "tracking_passes_made_pg"))
    passes = passes_pg_val / gp if passes_pg_val > 0 else passes_raw / gp
    pot_ast_raw = sf(_get_nested(row, "POTENTIAL_AST"))
    pot_ast_pg_val = sf(_get_nested(row, "tracking_potential_ast_pg"))
    pot_ast = pot_ast_pg_val / gp if pot_ast_pg_val > 0 else pot_ast_raw / gp
    ast_pass = sf(_get_nested(row, "AST_TO_PASS_PCT", "ast_to_pass_pct", "tracking_ast_to_pass_pct"))
    sec_ast_raw = sf(_get_nested(row, "SECONDARY_AST"))
    sec_ast_pg_val = sf(_get_nested(row, "tracking_secondary_ast_pg"))
    sec_ast = sec_ast_pg_val / gp if sec_ast_pg_val > 0 else sec_ast_raw / gp
    
    # Tracking: Catch & Shoot (merged data has season totals with _pg suffix, divide by GP)
    cs_fg3a_raw = sf(_get_nested(row, "CATCH_SHOOT_FG3A"))
    cs_fg3a_pg_val = sf(_get_nested(row, "tracking_catch_shoot_fg3a"))
    cs_fg3a = cs_fg3a_pg_val / gp if cs_fg3a_pg_val > 0 else cs_fg3a_raw / gp
    cs_fg = sf(_get_nested(row, "CATCH_SHOOT_FG_PCT", "catch_shoot_fg_pct", "tracking_catch_shoot_fg_pct"))
    
    # Tracking: Pull-Up (merged data has season totals with _pg suffix, divide by GP)
    pu_fg3a_raw = sf(_get_nested(row, "PULL_UP_FG3A", "PULLUP_FG3A"))
    pu_fg3a_pg_val = sf(_get_nested(row, "tracking_pullup_fg3a"))
    pu_fg3a = pu_fg3a_pg_val / gp if pu_fg3a_pg_val > 0 else pu_fg3a_raw / gp
    pu_fg = sf(_get_nested(row, "PULL_UP_FG3_PCT", "PULLUP_FG3_PCT", "tracking_pullup_fg3_pct"))
    
    # Tracking: Speed
    avg_speed = sf(_get_nested(row, "AVG_SPEED", "tracking_avg_speed"))
    avg_speed_off = sf(_get_nested(row, "AVG_SPEED_OFF", "tracking_avg_speed_off"))
    
    # Playtypes
    bh_pct = sf(_get_nested(row, "BALL_HANDLER_POSS_PCT", "f_ball_handler_poss_pct", "playtype_ballhandler_poss_pct"))
    bh_ppp = sf(_get_nested(row, "BALL_HANDLER_PPP", "f_ball_handler_ppp", "playtype_ballhandler_ppp"))
    iso_pct = sf(_get_nested(row, "ISOLATION_POSS_PCT", "f_isolation_poss_pct", "playtype_isolation_poss_pct"))
    iso_ppp = sf(_get_nested(row, "ISOLATION_PPP", "f_isolation_ppp", "playtype_isolation_ppp"))
    trans_pct = sf(_get_nested(row, "TRANSITION_POSS_PCT", "f_transition_poss_pct", "playtype_transition_poss_pct"))
    trans_ppp = sf(_get_nested(row, "TRANSITION_PPP", "f_transition_ppp", "playtype_transition_ppp"))
    os_pct = sf(_get_nested(row, "OFF_SCREEN_POSS_PCT", "f_off_screen_poss_pct", "playtype_offscreen_poss_pct"))
    os_ppp = sf(_get_nested(row, "OFF_SCREEN_PPP", "f_off_screen_ppp", "playtype_offscreen_ppp"))
    cut_pct = sf(_get_nested(row, "CUT_POSS_PCT", "f_cut_poss_pct", "playtype_cut_poss_pct"))
    cut_ppp = sf(_get_nested(row, "CUT_PPP", "f_cut_ppp", "playtype_cut_ppp"))
    roll_pct = sf(_get_nested(row, "ROLL_MAN_POSS_PCT", "f_roll_man_poss_pct", "playtype_rollman_poss_pct"))
    roll_ppp = sf(_get_nested(row, "ROLL_MAN_PPP", "f_roll_man_ppp", "playtype_rollman_ppp"))
    
    # Hustle (merged data has season totals with _pg suffix, divide by GP)
    defl_raw = sf(_get_nested(row, "DEFLECTIONS"))
    defl_pg_val = sf(_get_nested(row, "hustle_deflections_pg"))
    deflections = defl_pg_val / gp if defl_pg_val > 0 else defl_raw / gp
    cont_raw = sf(_get_nested(row, "CONTESTED_SHOTS"))
    cont_pg_val = sf(_get_nested(row, "hustle_contested_shots_pg"))
    contested = cont_pg_val / gp if cont_pg_val > 0 else cont_raw / gp
    cont3_raw = sf(_get_nested(row, "CONTESTED_SHOTS_3PT"))
    cont3_pg_val = sf(_get_nested(row, "hustle_contested_3pt_pg"))
    contested3 = cont3_pg_val / gp if cont3_pg_val > 0 else cont3_raw / gp
    box_raw = sf(_get_nested(row, "BOX_OUTS"))
    box_pg_val = sf(_get_nested(row, "hustle_box_outs_pg"))
    boxouts = box_pg_val / gp if box_pg_val > 0 else box_raw / gp
    
    # Bio
    height = sf(_get_nested(row, "PLAYER_HEIGHT_INCHES", "player_info_ht_in_in"))
    weight = sf(_get_nested(row, "PLAYER_WEIGHT", "player_info_wt"))
    age = sf(_get_nested(row, "AGE"))
    
    # Compute percentiles
    stats = _get_feature_stats() or {}
    
    def pct(name, value):
        s = stats.get(name, {})
        sorted_vals = s.get("sorted", [])
        if sorted_vals:
            return _compute_percentile(value, sorted_vals)
        return 50.0
    
    # Build feature vector
    features = {
        # Per-game (16)
        "f_pg_pts": pts, "f_pg_reb": reb, "f_pg_ast": ast, "f_pg_stl": stl,
        "f_pg_blk": blk, "f_pg_tov": tov, "f_pg_oreb": oreb, "f_pg_dreb": dreb,
        "f_pg_fgm": fgm, "f_pg_fga": fga, "f_pg_fg3m": fg3m, "f_pg_fg3a": fg3a,
        "f_pg_ftm": ftm, "f_pg_fta": fta, "f_pg_pf": pf, "f_pg_pfd": pfd,
        # Per-36 (5)
        "f_36_pts": p36_pts, "f_36_reb": p36_reb, "f_36_ast": p36_ast,
        "f_36_blk": p36_blk, "f_36_stl": p36_stl,
        # Shooting (4)
        "f_fg_pct": fg_pct, "f_fg3_pct": fg3_pct, "f_ft_pct": ft_pct, "f_ts_pct": ts_pct,
        # Derived (3)
        "f_fg3a_rate": fg3a_rate, "f_ft_rate": ft_rate, "f_ast_tov_ratio": ast_tov,
        # Advanced (5)
        "f_usg": usg, "f_ast_pct": ast_pct, "f_oreb_pct": oreb_pct,
        "f_dreb_pct": dreb_pct, "f_tov_pct": tov_pct,
        # Drives (3)
        "f_drives_pg": drives, "f_drive_fg_pct": drive_fg, "f_drive_ast_pct": drive_ast,
        # Touches (5)
        "f_touches_pg": touches, "f_paint_touch_pg": paint_touch,
        "f_pts_per_touch": pts_per_touch, "f_sec_per_touch": sec_per_touch,
        "f_elbow_touch_pg": elbow_touch,
        # Passing (4)
        "f_passes_pg": passes, "f_pot_ast_pg": pot_ast,
        "f_ast_pass_pct": ast_pass, "f_sec_ast_pg": sec_ast,
        # Catch & Shoot (2)
        "f_cs_fg3a_pg": cs_fg3a, "f_cs_fg_pct": cs_fg,
        # Pull-Up (2)
        "f_pu_fg3a_pg": pu_fg3a, "f_pu_fg_pct": pu_fg,
        # Speed (2)
        "f_avg_speed": avg_speed, "f_avg_speed_off": avg_speed_off,
        # Playtypes (12)
        "f_ball_handler_poss_pct": bh_pct, "f_ball_handler_ppp": bh_ppp,
        "f_isolation_poss_pct": iso_pct, "f_isolation_ppp": iso_ppp,
        "f_transition_poss_pct": trans_pct, "f_transition_ppp": trans_ppp,
        "f_off_screen_poss_pct": os_pct, "f_off_screen_ppp": os_ppp,
        "f_cut_poss_pct": cut_pct, "f_cut_ppp": cut_ppp,
        "f_roll_man_poss_pct": roll_pct, "f_roll_man_ppp": roll_ppp,
        # Hustle (4)
        "f_deflections_pg": deflections, "f_contested_pg": contested,
        "f_contested3_pg": contested3, "f_boxouts_pg": boxouts,
        # Bio (3)
        "f_height": height, "f_weight": weight, "f_age": age,
    }
    
    # Add percentiles
    for name in [
        "f_pg_pts", "f_pg_reb", "f_pg_ast", "f_pg_stl", "f_pg_blk",
        "f_pg_tov", "f_pg_oreb", "f_pg_dreb", "f_pg_fgm", "f_pg_fga",
        "f_pg_fg3m", "f_pg_fg3a", "f_pg_ftm", "f_pg_fta",
        "f_36_pts", "f_36_reb", "f_36_ast", "f_36_blk", "f_36_stl",
        "f_fg_pct", "f_fg3_pct", "f_ft_pct", "f_ts_pct",
        "f_fg3a_rate", "f_ft_rate", "f_ast_tov_ratio",
        "f_usg", "f_ast_pct", "f_oreb_pct", "f_dreb_pct", "f_tov_pct",
        "f_drives_pg", "f_drive_fg_pct", "f_drive_ast_pct",
        "f_touches_pg", "f_paint_touch_pg", "f_pts_per_touch",
        "f_passes_pg", "f_pot_ast_pg", "f_ast_pass_pct", "f_sec_ast_pg",
        "f_cs_fg3a_pg", "f_cs_fg_pct",
        "f_pu_fg3a_pg", "f_pu_fg_pct",
        "f_avg_speed", "f_avg_speed_off",
        "f_deflections_pg", "f_contested_pg", "f_contested3_pg",
        "f_boxouts_pg", "f_height", "f_weight",
    ]:
        features[f"pct_{name}"] = pct(name, features.get(name, 0))
    
    # Return in correct order
    feat_names = _get_feature_names()
    if feat_names:
        return [features.get(n, 0.0) for n in feat_names]
    
    # Fallback: return as list in dict order
    return list(features.values())

def _predict_tree(nodes, features):
    """Traverse a single tree and return leaf value."""
    idx = 0
    while True:
        if nodes["is_leaf"][idx]:
            return nodes["value"][idx]
        
        feat_idx = nodes["feature_idx"][idx]
        threshold = nodes["num_threshold"][idx]
        
        if feat_idx < 0 or feat_idx >= len(features):
            idx = nodes["left"][idx]
        elif math.isnan(features[feat_idx]):
            idx = nodes["left"][idx] if nodes["missing_go_to_left"][idx] else nodes["right"][idx]
        elif features[feat_idx] <= threshold:
            idx = nodes["left"][idx]
        else:
            idx = nodes["right"][idx]

def _predict_hgb_model(model_data, features):
    """Predict using one HistGradientBoostingRegressor model."""
    baseline = model_data["baseline"]
    if isinstance(baseline, list):
        if isinstance(baseline[0], list):
            pred = baseline[0][0]
        else:
            pred = baseline[0]
    else:
        pred = baseline
    
    lr = model_data["learning_rate"]
    
    for tree in model_data["trees"]:
        leaf_val = _predict_tree(tree, features)
        pred += lr * leaf_val
    
    return pred

def _scale_features(features, scaler_data):
    """Apply RobustScaler transformation."""
    if scaler_data is None or scaler_data.get("center") is None:
        return features
    
    center = scaler_data["center"]
    scale = scaler_data["scale"]
    
    scaled = []
    for i, v in enumerate(features):
        if math.isnan(v) if isinstance(v, float) else False:
            scaled.append(0.0)
            continue
        c = center[i] if i < len(center) else 0
        s = scale[i] if i < len(scale) else 1
        if s == 0:
            scaled.append(0.0)
        else:
            scaled.append((v - c) / s)
    return scaled

def predict_attribute(pos_group, attr_name, features):
    """Predict one attribute using exported model."""
    models = _get_models()
    if models is None:
        return 50
    
    pos_data = models.get(pos_group)
    if pos_data is None:
        return 50
    
    attr_data = pos_data.get(attr_name)
    if attr_data is None:
        return 50
    
    ensemble = attr_data.get("ensemble", [])
    scaler_data = attr_data.get("scaler")
    
    if not ensemble:
        return 50
    
    scaled = _scale_features(features, scaler_data)
    
    preds = []
    for model_data in ensemble:
        p = _predict_hgb_model(model_data, scaled)
        preds.append(p)
    
    avg = sum(preds) / len(preds)
    return max(25, min(99, int(round(avg))))

def detect_position_group(position):
    """Detect position group from position string."""
    pos = str(position or "").upper()
    if "C" in pos and "PF" not in pos:
        return "big"
    if "PF" in pos:
        return "big"
    if "SF" in pos:
        return "wing"
    return "guard"

def predict_attributes(row, all_rows=None):
    """Predict all attributes for a player using ML models.
    
    Args:
        row: player data dict
        all_rows: all player rows for percentile computation
    
    Returns:
        Dict of attribute_name -> value (25-99)
    """
    position = str(row.get("position", row.get("pos", "")))
    pos_group = detect_position_group(position)
    
    features = compute_features(row, all_rows or [])
    
    ML_ATTRIBUTES = [
        "Driving Layup", "Standing Dunk", "Driving Dunk", "Close Shot",
        "Mid-Range Shot", "Three-Point Shot", "Free Throw", "Shot IQ",
        "Draw Foul", "Post Hook", "Post Fade", "Post Control",
        "Ball Handle", "Speed with Ball", "Hands", "Pass Accuracy",
        "Pass IQ", "Pass Vision", "Offensive Consistency", "Defensive Consistency",
        "Interior Defense", "Perimeter Defense", "Steal", "Block",
        "Help Defense IQ", "Pass Perception",
        "Offensive Rebound", "Defensive Rebound",
        "Speed", "Agility", "Strength", "Vertical", "Stamina",
        "Hustle", "Overall Durability", "Potential",
    ]
    
    attrs = {}
    for attr in ML_ATTRIBUTES:
        val = predict_attribute(pos_group, attr, features)
        attrs[attr] = val
    
    return attrs
