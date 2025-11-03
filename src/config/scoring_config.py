"""
Scoring Configuration - Single Source of Truth for All Point Values

Centralized configuration for room-demand scoring systems across:
- Manual allocation scoring
- Autonomous allocation scoring
- Priority calculations
- Historical frequency bonuses
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ScoringWeights:
    """Point values for room-demand compatibility scoring."""

    # Basic requirements
    CAPACITY_ADEQUATE: int = 4

    # Hard rules compliance
    HARD_RULE_COMPLIANCE: int = 20

    # Professor preferences
    PREFERRED_ROOM: int = 4
    PREFERRED_CHARACTERISTIC: int = 4

    # Historical frequency
    HISTORICAL_FREQUENCY_PER_ALLOCATION: int = 1
    HISTORICAL_FREQUENCY_MAX_CAP: int = 12


@dataclass
class ScoringRules:
    """Business rules for scoring calculations."""

    # Only apply soft preferences if hard rules are satisfied
    REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES: bool = True

    # Historical frequency applies across all previous semesters
    HISTORICAL_EXCLUDE_CURRENT_SEMESTER: bool = True


# Global instances
SCORING_WEIGHTS = ScoringWeights()
SCORING_RULES = ScoringRules()


def get_scoring_breakdown_template() -> Dict[str, int]:
    """Get empty scoring breakdown structure."""
    return {
        "capacity_points": 0,
        "hard_rules_points": 0,
        "soft_preference_points": 0,
        "historical_frequency_points": 0,
        "total_score": 0,
    }
