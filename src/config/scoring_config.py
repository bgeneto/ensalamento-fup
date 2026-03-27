"""
Scoring Configuration - Single Source of Truth for All Point Values

Centralized configuration for room-demand scoring systems across:
- Manual allocation scoring
- Autonomous allocation scoring
- Priority calculations
- Historical frequency bonuses

Configuration is loaded from JSON files for better maintainability.
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULTS_FILE = PROJECT_ROOT / "data" / "scoring_defaults.json"
LEGACY_USER_CONFIG_FILE = PROJECT_ROOT / "data" / "scoring_config.json"
USER_CONFIG_FILE = Path(
    os.getenv(
        "SCORING_CONFIG_PATH",
        str(PROJECT_ROOT / "data" / "runtime" / "scoring_config.json"),
    )
)


@dataclass
class ScoringWeights:
    """Point values for room-demand compatibility scoring.

    Opção 3 (Balanceada): Reduz peso de capacidade e aumenta peso de histórico.

    Estratégia de Scoring:
    - Capacidade adequada: 3 pontos (reduzido de 4 para diminuir dominância)
    - Histórico: 2 pontos por alocação (aumentado de 1 para valorizar estabilidade)
    - Cap máximo: 5 pontos (limite máximo de pontos históricos, não quantidade de alocações)

    Range total: 3-8 pontos
    - Sem histórico: 3 pts (apenas capacidade)
    - 1 histórico: 5 pts (3 + min(1*2, 5) = 3 + 2)
    - 2 históricos: 7 pts (3 + min(2*2, 5) = 3 + 4)
    - 3+ históricos: 8 pts (3 + min(3*2, 5) = 3 + 5, limitado pelo cap)

    Importante: HISTORICAL_FREQUENCY_MAX_CAP é um limite de PONTOS, não de alocações.
    Exemplo com cap=12:
    - 10 alocações * 2 pts/alocação = 20 pts → limitado a 12 pts
    - Score final: 3 (capacidade) + 5 (histórico cap) = 8 pts

    Impacto:
    - Disciplinas com mais histórico ganham claramente (gap maior)
    - Capacidade ainda é critério importante (salas inadequadas = 0 pts)
    - Novas disciplinas não ficam muito atrás (3 vs 5-7 pts é recuperável)

    Priority constants for demand ordering in autonomous allocation:
    - PRIORITY_SPECIFIC_ROOM_REQUIRED: Demands that MUST use specific rooms
    - PRIORITY_MOBILITY_CONSTRAINTS: Professors with mobility constraints
    - PRIORITY_ROOM_PREFERENCES: Graduate courses needing better rooms
    - PRIORITY_CHARACTERISTIC_PREFERENCES: Laboratory courses needing equipment
    """

    # Basic requirements (autonomous + manual allocation)
    CAPACITY_ADEQUATE: int = 3  # Changed from 4 → 3 (25% reduction)

    # Hard rules compliance (manual allocation only)
    HARD_RULE_COMPLIANCE: int = 20

    # Professor preferences (manual allocation only)
    PREFERRED_ROOM: int = 4
    PREFERRED_CHARACTERISTIC: int = 4

    # Historical frequency (autonomous allocation)
    HISTORICAL_FREQUENCY_PER_ALLOCATION: int = 2  # Changed from 1 → 2 (100% increase)
    HISTORICAL_FREQUENCY_MAX_CAP: int = 12

    # Hybrid discipline scoring (Phase 0 detection)
    # Bonus when room type matches historical pattern for day
    # (lab room on lab day, classroom on classroom day)
    HYBRID_ROOM_TYPE_MATCH: int = 15

    # Partial allocation continuity tuning
    DISCIPLINE_EXISTING_ROOM_BONUS: int = 12
    PROFESSOR_ANCHOR_ROOM_BONUS: int = 8
    PROFESSOR_ANCHOR_BUILDING_BONUS: int = 4
    PROFESSOR_ANCHOR_ROOM_TYPE_BONUS: int = 2
    FUTURE_DAY_COVERAGE_PER_DAY: int = 2
    NON_HYBRID_FRAGMENTATION_PENALTY: int = 6

    # Priority constants for autonomous allocation demand ordering
    PRIORITY_SPECIFIC_ROOM_REQUIRED: int = 50
    PRIORITY_MOBILITY_CONSTRAINTS: int = 30
    PRIORITY_ROOM_PREFERENCES: int = 20
    PRIORITY_CHARACTERISTIC_PREFERENCES: int = 15


@dataclass
class ScoringRules:
    """Business rules for scoring calculations."""

    # Only apply soft preferences if hard rules are satisfied
    REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES: bool = True

    # Historical frequency applies across all previous semesters
    HISTORICAL_EXCLUDE_CURRENT_SEMESTER: bool = True


def _load_config_from_json() -> Dict[str, Any]:
    """
    Load scoring configuration from JSON files.

    Returns:
        Dictionary containing weights and rules configuration
    """
    # Start with defaults
    config = {}

    # Load defaults first (fallback)
    try:
        with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
            defaults = json.load(f)
            config.update(defaults)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load defaults from {DEFAULTS_FILE}: {e}")

    user_config_path = get_existing_scoring_config_path()
    if user_config_path is None:
        logger.info("No user scoring override found. Using defaults only.")
        return config

    # Load user config (overrides defaults)
    try:
        with open(user_config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            # Merge user config with defaults
            for key in user_config:
                if key != "_metadata":  # Skip metadata
                    if key in config:
                        config[key].update(user_config[key])
                    else:
                        config[key] = user_config[key]
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(
            f"Could not load user config from {user_config_path}: {e}. Using defaults."
        )

    return config


def get_scoring_config_path() -> Path:
    """Return the writable path for user scoring overrides."""
    return USER_CONFIG_FILE


def get_existing_scoring_config_path() -> Path | None:
    """Return the active user scoring config file, preferring runtime override."""
    if USER_CONFIG_FILE.exists():
        return USER_CONFIG_FILE
    if LEGACY_USER_CONFIG_FILE.exists():
        return LEGACY_USER_CONFIG_FILE
    return None


def ensure_user_scoring_config_file() -> Path:
    """
    Ensure the writable user scoring config exists in the runtime data directory.

    Priority:
    1. Keep existing runtime override when present
    2. Migrate legacy tracked file into runtime override
    3. Seed runtime override from defaults
    """
    USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if USER_CONFIG_FILE.exists():
        return USER_CONFIG_FILE

    source_path = LEGACY_USER_CONFIG_FILE
    if not source_path.exists():
        source_path = DEFAULTS_FILE

    with open(source_path, "r", encoding="utf-8") as src:
        config = json.load(src)

    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as dst:
        json.dump(config, dst, indent=4, ensure_ascii=False)

    logger.info("Created runtime scoring override at %s", USER_CONFIG_FILE)
    return USER_CONFIG_FILE


def _create_scoring_weights_from_config(config: Dict[str, Any]) -> ScoringWeights:
    """Create ScoringWeights instance from configuration dictionary."""
    weights = config.get("weights", {})

    return ScoringWeights(
        CAPACITY_ADEQUATE=weights.get("CAPACITY_ADEQUATE", 3),
        HARD_RULE_COMPLIANCE=weights.get("HARD_RULE_COMPLIANCE", 20),
        PREFERRED_ROOM=weights.get("PREFERRED_ROOM", 4),
        PREFERRED_CHARACTERISTIC=weights.get("PREFERRED_CHARACTERISTIC", 4),
        HISTORICAL_FREQUENCY_PER_ALLOCATION=weights.get(
            "HISTORICAL_FREQUENCY_PER_ALLOCATION", 2
        ),
        HISTORICAL_FREQUENCY_MAX_CAP=weights.get("HISTORICAL_FREQUENCY_MAX_CAP", 12),
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
    """Create ScoringRules instance from configuration dictionary."""
    rules = config.get("rules", {})

    return ScoringRules(
        REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES=rules.get(
            "REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES", True
        ),
        HISTORICAL_EXCLUDE_CURRENT_SEMESTER=rules.get(
            "HISTORICAL_EXCLUDE_CURRENT_SEMESTER", True
        ),
    )


# Load configuration and create global instances
_config = _load_config_from_json()
SCORING_WEIGHTS = _create_scoring_weights_from_config(_config)
SCORING_RULES = _create_scoring_rules_from_config(_config)


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
    """
    Validate scoring configuration values.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        weights = config.get("weights", {})

        # Validate weight values are non-negative integers
        weight_keys = [
            "CAPACITY_ADEQUATE",
            "HARD_RULE_COMPLIANCE",
            "PREFERRED_ROOM",
            "PREFERRED_CHARACTERISTIC",
            "HISTORICAL_FREQUENCY_PER_ALLOCATION",
            "HISTORICAL_FREQUENCY_MAX_CAP",
            "HYBRID_ROOM_TYPE_MATCH",
            "DISCIPLINE_EXISTING_ROOM_BONUS",
            "PROFESSOR_ANCHOR_ROOM_BONUS",
            "PROFESSOR_ANCHOR_BUILDING_BONUS",
            "PROFESSOR_ANCHOR_ROOM_TYPE_BONUS",
            "FUTURE_DAY_COVERAGE_PER_DAY",
            "NON_HYBRID_FRAGMENTATION_PENALTY",
            "PRIORITY_SPECIFIC_ROOM_REQUIRED",
            "PRIORITY_MOBILITY_CONSTRAINTS",
            "PRIORITY_ROOM_PREFERENCES",
            "PRIORITY_CHARACTERISTIC_PREFERENCES",
        ]

        for key in weight_keys:
            value = weights.get(key)
            if not isinstance(value, int) or value < 0:
                logger.error(f"Invalid weight value for {key}: {value}")
                return False

        # Validate historical frequency cap is reasonable
        hist_cap = weights.get("HISTORICAL_FREQUENCY_MAX_CAP", 0)
        hist_per_alloc = weights.get("HISTORICAL_FREQUENCY_PER_ALLOCATION", 0)
        if hist_cap < hist_per_alloc:
            logger.warning(
                f"Historical frequency max cap ({hist_cap}) is less than per allocation ({hist_per_alloc})"
            )

        # Validate rules are boolean
        rules = config.get("rules", {})
        rule_keys = [
            "REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES",
            "HISTORICAL_EXCLUDE_CURRENT_SEMESTER",
        ]

        for key in rule_keys:
            value = rules.get(key)
            if not isinstance(value, bool):
                logger.error(f"Invalid rule value for {key}: {value}")
                return False

        return True

    except Exception as e:
        logger.error(f"Configuration validation error: {e}")
        return False


def reload_scoring_config() -> None:
    """
    Reload scoring configuration from JSON files.

    Useful after configuration changes via the UI.
    """
    global _config, SCORING_WEIGHTS, SCORING_RULES

    _config = _load_config_from_json()

    # Validate configuration before applying
    if not validate_scoring_config(_config):
        logger.error("Invalid scoring configuration, keeping current values")
        return

    SCORING_WEIGHTS = _create_scoring_weights_from_config(_config)
    SCORING_RULES = _create_scoring_rules_from_config(_config)

    logger.info("Scoring configuration reloaded from JSON")
