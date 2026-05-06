"""NBA 2K26 Generator package."""

__version__ = "1.0.0"

from .generator_cli import (
    load_rows,
    compute_tendencies,
    compute_attributes,
)

from .generator_cli_ml import (
    compute_attributes_ml,
)

from .badges import (
    compute_badges,
    compute_badge_groups,
    compute_badge_count_from_stats,
    load_badge_catalog,
    BADGE_TIER_ORDER,
    BADGE_TIER_THRESHOLDS,
    BADGE_MAX_TOTAL,
    BADGE_MAX_LEGEND,
    BADGE_MAX_HOF,
)

__all__ = [
    "load_rows",
    "compute_tendencies",
    "compute_attributes",
    "compute_attributes_ml",
    "compute_badges",
    "compute_badge_groups",
    "compute_badge_count_from_stats",
    "load_badge_catalog",
    "BADGE_TIER_ORDER",
    "BADGE_TIER_THRESHOLDS",
    "BADGE_MAX_TOTAL",
    "BADGE_MAX_LEGEND",
    "BADGE_MAX_HOF",
]
