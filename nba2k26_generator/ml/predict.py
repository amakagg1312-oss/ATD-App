"""Inference pipeline for NBA 2K26 attribute prediction."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .models import AttributePredictor, PositionSpecificModels
from .feature_engineering import engineer_features, get_feature_columns
from .config import MODELS_DIR, ATTRIBUTE_NAMES, ML_ATTRIBUTES, HEURISTIC_ATTRIBUTES


class AttributeGenerator:
    """Generate NBA 2K26 attributes using ML models."""

    def __init__(self, models_dir: Path = None):
        self.models_dir = models_dir or MODELS_DIR
        self.predictor = AttributePredictor()
        self.models_loaded = False
        self.feature_columns = None

    def load_models(self) -> bool:
        """Load trained models."""
        self.models_loaded = self.predictor.load_models(self.models_dir)

        if self.models_loaded:
            model_dir = Path(self.models_dir)
            feat_file = model_dir / "feature_columns.txt"
            if feat_file.exists():
                with open(feat_file, "r") as f:
                    self.feature_columns = [line.strip() for line in f]

        return self.models_loaded

    def _compute_heuristic_physical(
        self, height_inches: float, weight_lbs: float, position: str
    ) -> Dict[str, int]:
        """Compute heuristic physical attributes."""
        is_big = "C" in position or "PF" in position

        speed = 60
        agility = 60
        strength = 50
        vertical = 55
        stamina = 70

        if height_inches > 0:
            if height_inches < 75:
                speed += 15
                agility += 12
            elif height_inches < 80:
                speed += 8
                agility += 8
            else:
                speed -= 5
                strength += 10
                vertical += 8

        if weight_lbs > 0:
            if weight_lbs > 240:
                strength += 15
                speed -= 5
            elif weight_lbs > 200:
                strength += 8
            else:
                speed += 5
                agility += 5

        if is_big:
            strength += 10
            speed -= 8
            vertical += 5

        return {
            "Speed": max(40, min(99, speed)),
            "Agility": max(40, min(99, agility)),
            "Strength": max(40, min(99, strength)),
            "Vertical": max(40, min(99, vertical)),
            "Stamina": max(50, min(99, stamina)),
        }

    def _compute_heuristic_mental(
        self, experience_years: int, position: str
    ) -> Dict[str, int]:
        """Compute heuristic mental attributes."""
        intangibles = min(80, 45 + experience_years * 4)
        hustle = min(85, 55 + experience_years * 3)
        durability = max(60, 85 - experience_years * 2) if experience_years > 5 else 80
        potential = max(50, 85 - experience_years * 3)

        return {
            "Intangibles": int(intangibles),
            "Hustle": int(hustle),
            "Overall Durability": int(durability),
            "Potential": int(potential),
        }

    def generate_attributes(
        self,
        player_stats: Dict,
        position: str = "SG",
        height_inches: float = 78,
        weight_lbs: float = 200,
        experience_years: int = 3,
    ) -> Dict[str, int]:
        """Generate all 33 attributes for a player using pure ML."""
        if not self.models_loaded:
            if not self.load_models():
                return self._generate_fallback_attributes(position)

        feature_dict = self._extract_features(player_stats)

        if self.feature_columns:
            num_features = len(self.feature_columns)
            X = np.zeros(num_features)
            for i, col in enumerate(self.feature_columns):
                if col in feature_dict:
                    X[i] = feature_dict[col]
        else:
            X = np.array(list(feature_dict.values()))
            if len(X.shape) == 1:
                X = X.reshape(1, -1)

        pos_group = self._detect_position_group(position)

        try:
            attributes = self.predictor.predict_attributes(X, position_group=pos_group)
        except Exception as e:
            print(f"Prediction error: {e}")
            return self._generate_fallback_attributes(position)

        overall = self.predictor.predict_overall(attributes)
        attributes["Overall"] = overall

        return attributes

    # Attribute column names that should NOT be used as input features
    ATTRIBUTE_COLUMNS = set(ATTRIBUTE_NAMES) | {"Free Thow"}

    def _extract_features(self, stats: Dict) -> Dict[str, float]:
        """Extract features from player stats dict.

        If the stats dict contains pre-computed f_* and pct_f_* features
        (from generator_cli_ml.py), pass them through directly.
        Otherwise, fall back to computing from raw column names.
        """
        features = {}

        # Check if stats already has pre-computed f_* features
        has_precomputed = any(k.startswith("f_") for k in stats)

        if has_precomputed:
            # Direct passthrough of all pre-computed features
            for k, v in stats.items():
                if k.startswith("f_") or k.startswith("pct_f_"):
                    try:
                        features[k] = float(v)
                    except (ValueError, TypeError):
                        features[k] = 0.0
            return features

        # Legacy path: compute features from raw NBA column names
        def _get(*keys, default=0.0):
            for k in keys:
                if k in stats:
                    try:
                        return float(stats[k])
                    except (ValueError, TypeError):
                        pass
            return default

        gp = _get("per_game_g", "GP", default=1.0)
        if gp <= 0:
            gp = 1.0
        mins = _get("per_game_mp_per_game", "MIN", default=30.0)
        if mins <= 0:
            mins = 30.0

        pts = _get("per_game_pts_per_game")
        reb = _get("per_game_trb_per_game", "per_game_reb_per_game")
        ast = _get("per_game_ast_per_game")
        stl = _get("per_game_stl_per_game")
        blk = _get("per_game_blk_per_game")
        tov = _get("per_game_tov_per_game")
        fgm = _get("per_game_fg_per_game")
        fga = _get("per_game_fga_per_game")
        fg3m = _get("per_game_x3p_per_game")
        fg3a = _get("per_game_x3pa_per_game")
        ftm = _get("per_game_ft_per_game")
        fta = _get("per_game_fta_per_game")
        oreb = _get("per_game_oreb_per_game")
        dreb = _get("per_game_dreb_per_game")
        pf = _get("per_game_pf_per_game")
        pfd = _get("per_game_pfd_per_game")

        features["f_pg_pts"] = pts
        features["f_pg_reb"] = reb
        features["f_pg_ast"] = ast
        features["f_pg_stl"] = stl
        features["f_pg_blk"] = blk
        features["f_pg_tov"] = tov
        features["f_pg_oreb"] = oreb
        features["f_pg_dreb"] = dreb
        features["f_pg_pf"] = pf
        features["f_pg_pfd"] = pfd
        features["f_pg_fgm"] = fgm
        features["f_pg_fga"] = fga
        features["f_pg_fg3m"] = fg3m
        features["f_pg_fg3a"] = fg3a
        features["f_pg_ftm"] = ftm
        features["f_pg_fta"] = fta

        mins_safe = max(mins, 0.1)
        features["f_36_pts"] = pts / mins_safe * 36
        features["f_36_reb"] = reb / mins_safe * 36
        features["f_36_ast"] = ast / mins_safe * 36
        features["f_36_blk"] = blk / mins_safe * 36
        features["f_36_stl"] = stl / mins_safe * 36

        fg_pct = _get("per_game_fg_percent")
        fg3_pct = _get("per_game_x3p_percent")
        ft_pct = _get("per_game_ft_percent", "per_36_ft_percent")
        ts_pct = _get("advanced_ts_percent")
        efg_pct = _get("advanced_efg_percent", "per_game_e_fg_percent")

        features["f_fg_pct"] = fg_pct
        features["f_fg3_pct"] = fg3_pct
        features["f_ft_pct"] = ft_pct
        features["f_ts_pct"] = ts_pct
        features["f_efg_pct"] = efg_pct

        features["f_fg3a_rate"] = fg3a / max(fga, 0.1) if fga > 0 else 0.0
        features["f_ft_rate"] = fta / max(fga, 0.1) if fga > 0 else 0.0
        features["f_ast_tov_ratio"] = ast / max(tov, 0.1) if tov > 0 else ast

        features["f_usg"] = _get("advanced_usg_percent")
        features["f_ast_pct"] = _get("advanced_ast_percent")
        features["f_reb_pct"] = _get("advanced_reb_percent", default=0.0)
        features["f_oreb_pct"] = _get("advanced_orb_percent")
        features["f_dreb_pct"] = _get("advanced_drb_percent")
        features["f_tov_pct"] = _get("advanced_tov_percent")
        features["f_off_rtg"] = _get("advanced_off_rating", default=0.0)
        features["f_def_rtg"] = _get("advanced_def_rating", default=0.0)
        features["f_net_rtg"] = _get("advanced_net_rating", default=0.0)
        features["f_pie"] = _get("advanced_pie", default=0.0)
        features["f_pct_stl"] = _get("advanced_stl_percent")
        features["f_pct_blk"] = _get("advanced_blk_percent")

        features["f_drives_pg"] = _get("tracking_drives_pg")
        features["f_drive_fg_pct"] = _get("tracking_drive_fg_pct")
        features["f_drive_ast_pct"] = _get(
            "tracking_drive_ast_rate", "tracking_drive_ast_pct"
        )
        features["f_touches_pg"] = _get("tracking_touches_pg")
        features["f_paint_touch_pg"] = _get("tracking_paint_touches_pg")
        features["f_post_touch_pg"] = _get("tracking_post_touches_pg", default=0.0)
        features["f_elbow_touch_pg"] = _get("tracking_elbow_touches_pg")
        features["f_pts_per_touch"] = _get("tracking_pts_per_touch")
        features["f_sec_per_touch"] = _get("tracking_avg_sec_per_touch")
        features["f_passes_pg"] = _get("tracking_passes_made_pg")
        features["f_pot_ast_pg"] = _get("tracking_potential_ast_pg")
        features["f_ast_pass_pct"] = _get("tracking_ast_to_pass_pct")
        features["f_sec_ast_pg"] = _get("tracking_secondary_ast_pg")
        features["f_cs_fg3a_pg"] = _get("tracking_catch_shoot_fg3a_pg")
        features["f_cs_fg_pct"] = _get(
            "tracking_catch_shoot_fg3_pct", "tracking_catch_shoot_efg_pct"
        )
        features["f_pu_fg3a_pg"] = _get(
            "tracking_pullup_fg3a_pg", "tracking_pull_up_fg3a_pg", default=0.0
        )
        features["f_pu_fg_pct"] = _get(
            "tracking_pullup_fg3_pct", "tracking_pull_up_fg3_pct", default=0.0
        )
        features["f_avg_speed"] = _get("tracking_avg_speed")
        features["f_avg_speed_off"] = _get("tracking_avg_speed_off")
        features["f_dist_pg"] = _get("tracking_dist_miles_pg", "tracking_dist_miles")

        for pt in [
            "spot_up",
            "ball_handler",
            "isolation",
            "transition",
            "off_screen",
            "cut",
            "roll_man",
        ]:
            features[f"f_{pt}_poss_pct"] = _get(f"playtype_{pt}_poss_pct")
            features[f"f_{pt}_ppp"] = _get(f"playtype_{pt}_ppp")

        features["f_deflections_pg"] = _get("hustle_deflections_pg")
        features["f_contested_pg"] = _get("hustle_contested_shots_pg")
        features["f_contested3_pg"] = _get("hustle_contested_3pt_pg")
        features["f_boxouts_pg"] = _get("tracking_box_outs_pg")
        features["f_scr_ast_pg"] = _get("hustle_screen_assists_pg", default=0.0)

        features["f_height"] = _get("height_in", "player_info_ht_in_in")
        features["f_weight"] = _get("weight_lbs", "player_info_wt")
        features["f_age"] = _get("age")

        features["f_dd2_pg"] = _get("dd2_pg", default=0.0)
        features["f_td3_pg"] = _get("td3_pg", default=0.0)
        features["f_plus_minus"] = _get("plus_minus", default=0.0)

        # Percentile features
        has_true_percentiles = any(k.startswith("pct_f_") for k in stats)
        if has_true_percentiles:
            for k, v in stats.items():
                if k.startswith("pct_f_"):
                    features[k] = float(v)
        else:
            self._add_percentile_features(features, gp)

        return features

    def _add_percentile_features(self, features: Dict[str, float], gp: float):
        """Add approximate percentile features for inference.

        Uses heuristic estimates based on typical NBA stat distributions.
        """
        # Approximate percentile mappings based on typical NBA distributions
        # These are rough estimates that map stat values to percentile ranks
        pct_mappings = {
            # Points per game: 0pts=0th, 5pts=20th, 10pts=40th, 15pts=60th, 20pts=75th, 25pts=90th, 30pts=98th
            "f_pg_pts": lambda v: min(
                99,
                max(
                    1,
                    _interp(v, [0, 5, 10, 15, 20, 25, 30], [1, 20, 40, 60, 75, 90, 98]),
                ),
            ),
            # Assists per game: 0=0th, 2=30th, 4=50th, 6=70th, 8=85th, 10=95th, 12=99th
            "f_pg_ast": lambda v: min(
                99,
                max(
                    1, _interp(v, [0, 2, 4, 6, 8, 10, 12], [1, 30, 50, 70, 85, 95, 99])
                ),
            ),
            # Rebounds per game: 0=0th, 3=30th, 5=50th, 8=70th, 10=85th, 13=95th, 16=99th
            "f_pg_reb": lambda v: min(
                99,
                max(
                    1, _interp(v, [0, 3, 5, 8, 10, 13, 16], [1, 30, 50, 70, 85, 95, 99])
                ),
            ),
            # Steals per game: 0=0th, 0.5=30th, 1.0=50th, 1.5=70th, 2.0=85th, 2.5=95th
            "f_pg_stl": lambda v: min(
                99,
                max(
                    1, _interp(v, [0, 0.5, 1.0, 1.5, 2.0, 2.5], [1, 30, 50, 70, 85, 95])
                ),
            ),
            # Blocks per game: 0=0th, 0.3=30th, 0.7=50th, 1.2=70th, 1.8=85th, 2.5=95th
            "f_pg_blk": lambda v: min(
                99,
                max(
                    1, _interp(v, [0, 0.3, 0.7, 1.2, 1.8, 2.5], [1, 30, 50, 70, 85, 95])
                ),
            ),
            # FG%: 0.35=5th, 0.42=30th, 0.47=50th, 0.50=70th, 0.55=90th, 0.60=98th
            "f_fg_pct": lambda v: min(
                99,
                max(
                    1,
                    _interp(
                        v, [0.35, 0.42, 0.47, 0.50, 0.55, 0.60], [5, 30, 50, 70, 90, 98]
                    ),
                ),
            ),
            # 3P%: 0.25=5th, 0.33=30th, 0.36=50th, 0.39=70th, 0.42=85th, 0.45=95th
            "f_fg3_pct": lambda v: min(
                99,
                max(
                    1,
                    _interp(
                        v, [0.25, 0.33, 0.36, 0.39, 0.42, 0.45], [5, 30, 50, 70, 85, 95]
                    ),
                ),
            ),
            # FT%: 0.50=5th, 0.65=30th, 0.75=50th, 0.82=70th, 0.88=85th, 0.92=95th
            "f_ft_pct": lambda v: min(
                99,
                max(
                    1,
                    _interp(
                        v, [0.50, 0.65, 0.75, 0.82, 0.88, 0.92], [5, 30, 50, 70, 85, 95]
                    ),
                ),
            ),
            # TS%: 0.45=5th, 0.52=30th, 0.57=50th, 0.60=70th, 0.65=90th, 0.70=98th
            "f_ts_pct": lambda v: min(
                99,
                max(
                    1,
                    _interp(
                        v, [0.45, 0.52, 0.57, 0.60, 0.65, 0.70], [5, 30, 50, 70, 90, 98]
                    ),
                ),
            ),
            # USG%: 10=5th, 18=30th, 22=50th, 26=70th, 30=85th, 35=95th
            "f_usg": lambda v: min(
                99,
                max(1, _interp(v, [10, 18, 22, 26, 30, 35], [5, 30, 50, 70, 85, 95])),
            ),
            # AST%: 5=5th, 12=30th, 18=50th, 25=70th, 32=85th, 40=95th
            "f_ast_pct": lambda v: min(
                99, max(1, _interp(v, [5, 12, 18, 25, 32, 40], [5, 30, 50, 70, 85, 95]))
            ),
            # REB%: 5=5th, 10=30th, 14=50th, 18=70th, 22=85th, 28=95th
            "f_reb_pct": lambda v: min(
                99, max(1, _interp(v, [5, 10, 14, 18, 22, 28], [5, 30, 50, 70, 85, 95]))
            ),
            # PIE: 0=5th, 5=30th, 8=50th, 12=70th, 16=85th, 22=95th
            "f_pie": lambda v: min(
                99, max(1, _interp(v, [0, 5, 8, 12, 16, 22], [5, 30, 50, 70, 85, 95]))
            ),
            # Net rating: -10=5th, -3=30th, 0=50th, 3=70th, 6=85th, 10=95th
            "f_net_rtg": lambda v: min(
                99, max(1, _interp(v, [-10, -3, 0, 3, 6, 10], [5, 30, 50, 70, 85, 95]))
            ),
            # STL%: 0.5=5th, 1.0=30th, 1.5=50th, 2.0=70th, 2.5=85th, 3.0=95th
            "f_pct_stl": lambda v: min(
                99,
                max(
                    1,
                    _interp(v, [0.5, 1.0, 1.5, 2.0, 2.5, 3.0], [5, 30, 50, 70, 85, 95]),
                ),
            ),
            # BLK%: 0.3=5th, 0.8=30th, 1.5=50th, 2.5=70th, 3.5=85th, 5.0=95th
            "f_pct_blk": lambda v: min(
                99,
                max(
                    1,
                    _interp(v, [0.3, 0.8, 1.5, 2.5, 3.5, 5.0], [5, 30, 50, 70, 85, 95]),
                ),
            ),
            # Height: 72=5th, 75=30th, 78=50th, 80=70th, 82=85th, 84=95th
            "f_height": lambda v: min(
                99,
                max(1, _interp(v, [72, 75, 78, 80, 82, 84], [5, 30, 50, 70, 85, 95])),
            ),
            # Weight: 170=5th, 190=30th, 210=50th, 230=70th, 250=85th, 280=95th
            "f_weight": lambda v: min(
                99,
                max(
                    1,
                    _interp(v, [170, 190, 210, 230, 250, 280], [5, 30, 50, 70, 85, 95]),
                ),
            ),
        }

        for feat_name, pct_fn in pct_mappings.items():
            if feat_name in features:
                val = features[feat_name]
                if val > 0 or feat_name in ["f_net_rtg"]:
                    features[f"pct_{feat_name}"] = pct_fn(val)
                else:
                    features[f"pct_{feat_name}"] = 0.0

        # Derived percentile features
        if "f_pg_pts" in features and "f_pg_ast" in features:
            pts = features["f_pg_pts"]
            ast = features["f_pg_ast"]
            # Scoring+playmaking impact
            features["pct_pts_ast_combo"] = min(
                99,
                _interp(
                    pts + ast * 2, [5, 15, 25, 35, 45, 55], [5, 30, 50, 70, 85, 95]
                ),
            )

        if "f_pg_reb" in features and "f_pg_ast" in features:
            reb = features["f_pg_reb"]
            ast = features["f_pg_ast"]
            # Rebounding+playmaking (big man playmaker signal)
            features["pct_reb_ast_combo"] = min(
                99, _interp(reb + ast, [5, 10, 15, 20, 25], [5, 30, 50, 75, 95])
            )

    def _detect_position_group(self, position: str) -> str:
        """Detect position group from position."""
        pos_upper = position.upper()

        if "C" in pos_upper and "PF" not in pos_upper:
            return "big"
        if "PF" in pos_upper:
            return "big"
        if "SF" in pos_upper:
            return "wing"

        return "guard"

    def _generate_fallback_attributes(self, position: str) -> Dict[str, int]:
        """Generate fallback attributes when models unavailable."""
        pos_group = self._detect_position_group(position)

        attrs = {name: 50 for name in ATTRIBUTE_NAMES}

        if pos_group == "guard":
            attrs["Speed"] = 75
            attrs["Agility"] = 72
            attrs["Ball Handle"] = 68
            attrs["Pass Vision"] = 65
            attrs["Three-Point Shot"] = 62
        elif pos_group == "wing":
            attrs["Speed"] = 65
            attrs["Strength"] = 60
            attrs["Mid-Range Shot"] = 58
            attrs["Driving Dunk"] = 55
        else:
            attrs["Strength"] = 75
            attrs["Vertical"] = 65
            attrs["Interior Defense"] = 60
            attrs["Close Shot"] = 65

        return attrs


def _interp(value: float, x_points: List[float], y_points: List[float]) -> float:
    """Linear interpolation with clamping."""
    if value <= x_points[0]:
        return y_points[0]
    if value >= x_points[-1]:
        return y_points[-1]

    for i in range(len(x_points) - 1):
        if x_points[i] <= value <= x_points[i + 1]:
            t = (value - x_points[i]) / (x_points[i + 1] - x_points[i])
            return y_points[i] + t * (y_points[i + 1] - y_points[i])

    return y_points[-1]


def generate_player_attributes(
    player_stats: Dict, position: str = "SG", models_path: Path = None
) -> Dict[str, int]:
    """Convenience function to generate player attributes."""
    generator = AttributeGenerator(models_dir=models_path)

    if not generator.load_models():
        raise RuntimeError("Failed to load ML models. Please train models first.")

    return generator.generate_attributes(player_stats=player_stats, position=position)


if __name__ == "__main__":
    print("Testing AttributeGenerator...")
    generator = AttributeGenerator()

    if generator.load_models():
        print("Models loaded successfully!")

        sample_stats = {
            "PTS": 25.0,
            "AST": 8.0,
            "REB": 5.0,
            "STL": 1.5,
            "BLK": 0.3,
            "FG_PCT": 0.48,
            "FG3_PCT": 0.38,
            "FT_PCT": 0.85,
            "GP": 72,
            "MIN": 34.0,
        }

        attrs = generator.generate_attributes(sample_stats, position="PG")
        print(f"\nGenerated attributes for PG:")
        for k, v in attrs.items():
            print(f"  {k}: {v}")
    else:
        print("Models not found. Run train.py first.")
