"""
Scoring Configuration Validator

Ensures scoring configuration is consistent and valid across the system.
"""

from src.config.scoring_config import SCORING_WEIGHTS, SCORING_RULES


def validate_scoring_configuration():
    """Validate scoring configuration for consistency and business rules."""

    errors = []
    warnings = []

    # Check that all point values are positive
    for attr_name, value in SCORING_WEIGHTS.__dict__.items():
        if not attr_name.startswith("_") and isinstance(value, int):
            if value <= 0:
                errors.append(
                    f"SCORING_WEIGHTS.{attr_name} must be positive, got {value}"
                )

    # Check business rule consistency
    if SCORING_RULES.REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES:
        if SCORING_WEIGHTS.HARD_RULE_COMPLIANCE <= SCORING_WEIGHTS.PREFERRED_ROOM:
            warnings.append(
                f"Hard rule points ({SCORING_WEIGHTS.HARD_RULE_COMPLIANCE}) should be "
                f"greater than soft preference points ({SCORING_WEIGHTS.PREFERRED_ROOM}) "
                "when REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES is True"
            )

    # Check historical frequency cap makes sense
    if (
        SCORING_WEIGHTS.HISTORICAL_FREQUENCY_MAX_CAP
        < SCORING_WEIGHTS.HARD_RULE_COMPLIANCE
    ):
        warnings.append(
            f"Historical frequency cap ({SCORING_WEIGHTS.HISTORICAL_FREQUENCY_MAX_CAP}) "
            f"is less than hard rule points ({SCORING_WEIGHTS.HARD_RULE_COMPLIANCE}). "
            "This may make historical data too weak."
        )

    # Check enrollment priority logic
    if SCORING_RULES.ENROLLMENT_PRIORITY_DIVISOR <= 0:
        errors.append("ENROLLMENT_PRIORITY_DIVISOR must be positive")

    if SCORING_WEIGHTS.ENROLLMENT_PRIORITY_MAX <= 0:
        errors.append("ENROLLMENT_PRIORITY_MAX must be positive")

    return errors, warnings


def print_scoring_configuration():
    """Print current scoring configuration for reference."""
    print("=== SCORING CONFIGURATION ===")
    print("\n--- Point Values ---")
    for attr_name, value in SCORING_WEIGHTS.__dict__.items():
        if not attr_name.startswith("_") and isinstance(value, int):
            print(f"{attr_name}: {value}")

    print("\n--- Business Rules ---")
    for attr_name, value in SCORING_RULES.__dict__.items():
        if not attr_name.startswith("_"):
            print(f"{attr_name}: {value}")

    # Validate and show any issues
    errors, warnings = validate_scoring_configuration()
    if errors:
        print(f"\n--- ERRORS ---")
        for error in errors:
            print(f"❌ {error}")

    if warnings:
        print(f"\n--- WARNINGS ---")
        for warning in warnings:
            print(f"⚠️  {warning}")

    if not errors and not warnings:
        print("\n✅ Configuration is valid!")


if __name__ == "__main__":
    print_scoring_configuration()
