"""
Scoring Configuration - runtime accessors for scoring weights and rules.

This module keeps the public API used across the codebase while delegating
storage concerns to the DB-backed scoring configuration service.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from typing import Any, Dict

from src.config.scoring_registry import (
    build_default_scoring_config,
    validate_scoring_config_values,
)

logger = logging.getLogger(__name__)


@dataclass
class ScoringWeights:
    """Point values for room-demand compatibility scoring."""

    CAPACITY_ADEQUATE: int = 3
    HARD_RULE_COMPLIANCE: int = 20
    PREFERRED_ROOM: int = 4
    PREFERRED_CHARACTERISTIC: int = 4
    HISTORICAL_FREQUENCY_PER_ALLOCATION: int = 4
    HISTORICAL_FREQUENCY_MAX_CAP: int = 80
    HYBRID_ROOM_TYPE_MATCH: int = 15
    DISCIPLINE_EXISTING_ROOM_BONUS: int = 12
    PROFESSOR_ANCHOR_ROOM_BONUS: int = 8
    PROFESSOR_ANCHOR_BUILDING_BONUS: int = 4
    PROFESSOR_ANCHOR_ROOM_TYPE_BONUS: int = 2
    FUTURE_DAY_COVERAGE_PER_DAY: int = 2
    NON_HYBRID_FRAGMENTATION_PENALTY: int = 6
    PRIORITY_SPECIFIC_ROOM_REQUIRED: int = 50
    PRIORITY_MOBILITY_CONSTRAINTS: int = 30
    PRIORITY_ROOM_PREFERENCES: int = 20
    PRIORITY_CHARACTERISTIC_PREFERENCES: int = 15


@dataclass
class ScoringRules:
    """Business rules for scoring calculations."""

    REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES: bool = True
    HISTORICAL_EXCLUDE_CURRENT_SEMESTER: bool = True


def _load_config() -> Dict[str, Any]:
    """Load scoring configuration from DB, falling back to code defaults if needed."""
    try:
        from src.services.scoring_configuration_service import (
            ScoringConfigurationService,
        )

        return ScoringConfigurationService().get_effective_config_dict()
    except Exception as exc:
        logger.warning(
            "Falling back to code defaults because DB-backed load failed: %s",
            exc,
        )
        return build_default_scoring_config()


def _create_scoring_weights_from_config(config: Dict[str, Any]) -> ScoringWeights:
    """Create a ScoringWeights instance from a config dictionary."""
    weights = config.get("weights", {})
    return ScoringWeights(
        CAPACITY_ADEQUATE=weights.get("CAPACITY_ADEQUATE", 3),
        HARD_RULE_COMPLIANCE=weights.get("HARD_RULE_COMPLIANCE", 20),
        PREFERRED_ROOM=weights.get("PREFERRED_ROOM", 4),
        PREFERRED_CHARACTERISTIC=weights.get("PREFERRED_CHARACTERISTIC", 4),
        HISTORICAL_FREQUENCY_PER_ALLOCATION=weights.get(
            "HISTORICAL_FREQUENCY_PER_ALLOCATION", 4
        ),
        HISTORICAL_FREQUENCY_MAX_CAP=weights.get("HISTORICAL_FREQUENCY_MAX_CAP", 80),
        HYBRID_ROOM_TYPE_MATCH=weights.get("HYBRID_ROOM_TYPE_MATCH", 15),
        DISCIPLINE_EXISTING_ROOM_BONUS=weights.get(
            "DISCIPLINE_EXISTING_ROOM_BONUS", 12
        ),
        PROFESSOR_ANCHOR_ROOM_BONUS=weights.get("PROFESSOR_ANCHOR_ROOM_BONUS", 8),
        PROFESSOR_ANCHOR_BUILDING_BONUS=weights.get(
            "PROFESSOR_ANCHOR_BUILDING_BONUS", 4
        ),
        PROFESSOR_ANCHOR_ROOM_TYPE_BONUS=weights.get(
            "PROFESSOR_ANCHOR_ROOM_TYPE_BONUS", 2
        ),
        FUTURE_DAY_COVERAGE_PER_DAY=weights.get("FUTURE_DAY_COVERAGE_PER_DAY", 2),
        NON_HYBRID_FRAGMENTATION_PENALTY=weights.get(
            "NON_HYBRID_FRAGMENTATION_PENALTY", 6
        ),
        PRIORITY_SPECIFIC_ROOM_REQUIRED=weights.get(
            "PRIORITY_SPECIFIC_ROOM_REQUIRED", 50
        ),
        PRIORITY_MOBILITY_CONSTRAINTS=weights.get("PRIORITY_MOBILITY_CONSTRAINTS", 30),
        PRIORITY_ROOM_PREFERENCES=weights.get("PRIORITY_ROOM_PREFERENCES", 20),
        PRIORITY_CHARACTERISTIC_PREFERENCES=weights.get(
            "PRIORITY_CHARACTERISTIC_PREFERENCES", 15
        ),
    )


def _create_scoring_rules_from_config(config: Dict[str, Any]) -> ScoringRules:
    """Create a ScoringRules instance from a config dictionary."""
    rules = config.get("rules", {})
    return ScoringRules(
        REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES=rules.get(
            "REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES", True
        ),
        HISTORICAL_EXCLUDE_CURRENT_SEMESTER=rules.get(
            "HISTORICAL_EXCLUDE_CURRENT_SEMESTER", True
        ),
    )


def _apply_dataclass_values(target: Any, source: Any) -> None:
    """Mutate an existing dataclass instance in place."""
    for field in fields(target):
        setattr(target, field.name, getattr(source, field.name))


def get_scoring_breakdown_template() -> Dict[str, int]:
    """Get empty scoring breakdown structure."""
    return {
        "capacity_points": 0,
        "hard_rules_points": 0,
        "soft_preference_points": 0,
        "historical_frequency_points": 0,
        "discipline_continuity_points": 0,
        "professor_anchor_points": 0,
        "future_coverage_points": 0,
        "fragmentation_penalty": 0,
        "total_score": 0,
    }


def validate_scoring_config(config: Dict[str, Any]) -> bool:
    """Validate a scoring configuration dictionary."""
    is_valid, errors = validate_scoring_config_values(config)
    for error in errors:
        logger.error(error)
    return is_valid


SCORING_WEIGHTS = ScoringWeights()
SCORING_RULES = ScoringRules()
_config = build_default_scoring_config()


def reload_scoring_config() -> None:
    """Reload scoring configuration from DB or code defaults."""
    global _config

    loaded_config = _load_config()
    if not validate_scoring_config(loaded_config):
        logger.error("Invalid scoring configuration, keeping current values")
        return

    _config = loaded_config
    _apply_dataclass_values(
        SCORING_WEIGHTS, _create_scoring_weights_from_config(loaded_config)
    )
    _apply_dataclass_values(
        SCORING_RULES, _create_scoring_rules_from_config(loaded_config)
    )
    logger.info("Scoring configuration reloaded")


reload_scoring_config()
