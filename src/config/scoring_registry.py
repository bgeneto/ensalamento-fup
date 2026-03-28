"""Central registry for scoring configuration fields and defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

CURRENT_SCORING_SCHEMA_VERSION = 1
CURRENT_SCORING_DEFAULTS_REVISION = "2026-03-28"


@dataclass(frozen=True)
class ScoringFieldSpec:
    """Schema definition for a single scoring configuration field."""

    key: str
    section: str
    label: str
    description: str
    value_type: type
    default: int | bool
    order: int
    min_value: int | None = None
    max_value: int | None = None


SCORING_FIELD_SPECS: List[ScoringFieldSpec] = [
    ScoringFieldSpec(
        key="weights.CAPACITY_ADEQUATE",
        section="Base",
        label="Capacidade Adequada",
        description="Pontos quando a sala atende a capacidade da turma.",
        value_type=int,
        default=3,
        min_value=0,
        max_value=100,
        order=10,
    ),
    ScoringFieldSpec(
        key="weights.HARD_RULE_COMPLIANCE",
        section="Regras",
        label="Regra Obrigatória",
        description="Pontos por atender uma regra rígida obrigatória.",
        value_type=int,
        default=20,
        min_value=0,
        max_value=100,
        order=20,
    ),
    ScoringFieldSpec(
        key="weights.PREFERRED_ROOM",
        section="Preferências",
        label="Sala Preferida",
        description="Pontos quando a sala está nas preferências do professor.",
        value_type=int,
        default=4,
        min_value=0,
        max_value=100,
        order=30,
    ),
    ScoringFieldSpec(
        key="weights.PREFERRED_CHARACTERISTIC",
        section="Preferências",
        label="Característica Preferida",
        description="Pontos por característica preferida atendida.",
        value_type=int,
        default=4,
        min_value=0,
        max_value=100,
        order=40,
    ),
    ScoringFieldSpec(
        key="weights.HISTORICAL_FREQUENCY_PER_ALLOCATION",
        section="Histórico",
        label="Histórico por Alocação",
        description="Pontos adicionados por ocorrência histórica disciplina-sala.",
        value_type=int,
        default=4,
        min_value=0,
        max_value=100,
        order=50,
    ),
    ScoringFieldSpec(
        key="weights.HISTORICAL_FREQUENCY_MAX_CAP",
        section="Histórico",
        label="Lim. Máximo Histórico",
        description="Limite máximo de pontos acumulados pelo histórico.",
        value_type=int,
        default=80,
        min_value=0,
        max_value=500,
        order=60,
    ),
    ScoringFieldSpec(
        key="weights.HYBRID_ROOM_TYPE_MATCH",
        section="Híbridas",
        label="Match de Tipo para Híbridas",
        description="Bônus quando o tipo da sala coincide com o padrão histórico da disciplina híbrida.",
        value_type=int,
        default=15,
        min_value=0,
        max_value=100,
        order=70,
    ),
    ScoringFieldSpec(
        key="weights.DISCIPLINE_EXISTING_ROOM_BONUS",
        section="Continuidade",
        label="Bônus Sala Atual da Disciplina",
        description="Bônus por manter a disciplina na sala já usada em outro dia.",
        value_type=int,
        default=12,
        min_value=0,
        max_value=100,
        order=80,
    ),
    ScoringFieldSpec(
        key="weights.PROFESSOR_ANCHOR_ROOM_BONUS",
        section="Continuidade",
        label="Âncora Professor na Mesma Sala",
        description="Bônus por manter o professor ancorado exatamente na mesma sala.",
        value_type=int,
        default=8,
        min_value=0,
        max_value=100,
        order=90,
    ),
    ScoringFieldSpec(
        key="weights.PROFESSOR_ANCHOR_BUILDING_BONUS",
        section="Continuidade",
        label="Âncora Professor no Mesmo Prédio",
        description="Bônus por manter o professor no mesmo prédio.",
        value_type=int,
        default=4,
        min_value=0,
        max_value=100,
        order=100,
    ),
    ScoringFieldSpec(
        key="weights.PROFESSOR_ANCHOR_ROOM_TYPE_BONUS",
        section="Continuidade",
        label="Âncora Professor no Mesmo Tipo",
        description="Bônus por manter o professor no mesmo tipo de sala.",
        value_type=int,
        default=2,
        min_value=0,
        max_value=100,
        order=110,
    ),
    ScoringFieldSpec(
        key="weights.FUTURE_DAY_COVERAGE_PER_DAY",
        section="Continuidade",
        label="Cobertura de Dias Futuros",
        description="Bônus por cada dia futuro da disciplina coberto pela mesma sala.",
        value_type=int,
        default=2,
        min_value=0,
        max_value=100,
        order=120,
    ),
    ScoringFieldSpec(
        key="weights.NON_HYBRID_FRAGMENTATION_PENALTY",
        section="Continuidade",
        label="Penalidade por Fragmentação",
        description="Penalidade aplicada quando disciplina não híbrida é fragmentada.",
        value_type=int,
        default=6,
        min_value=0,
        max_value=100,
        order=130,
    ),
    ScoringFieldSpec(
        key="weights.PRIORITY_SPECIFIC_ROOM_REQUIRED",
        section="Prioridade",
        label="Prioridade Sala Específica",
        description="Prioridade para demandas que exigem sala específica.",
        value_type=int,
        default=50,
        min_value=0,
        max_value=500,
        order=140,
    ),
    ScoringFieldSpec(
        key="weights.PRIORITY_MOBILITY_CONSTRAINTS",
        section="Prioridade",
        label="Prioridade Restrição de Mobilidade",
        description="Prioridade para demandas com restrições de mobilidade.",
        value_type=int,
        default=30,
        min_value=0,
        max_value=500,
        order=150,
    ),
    ScoringFieldSpec(
        key="weights.PRIORITY_ROOM_PREFERENCES",
        section="Prioridade",
        label="Prioridade Preferência de Sala",
        description="Prioridade para demandas com forte preferência de sala.",
        value_type=int,
        default=20,
        min_value=0,
        max_value=500,
        order=160,
    ),
    ScoringFieldSpec(
        key="weights.PRIORITY_CHARACTERISTIC_PREFERENCES",
        section="Prioridade",
        label="Prioridade Preferência de Característica",
        description="Prioridade para demandas dependentes de características específicas.",
        value_type=int,
        default=15,
        min_value=0,
        max_value=500,
        order=170,
    ),
    ScoringFieldSpec(
        key="rules.REQUIRE_HARD_RULES_FOR_SOFT_PREFERENCES",
        section="Regras",
        label="Exigir Hard Rules para Preferências",
        description="Só aplicar preferências suaves quando as regras rígidas forem satisfeitas.",
        value_type=bool,
        default=True,
        order=180,
    ),
    ScoringFieldSpec(
        key="rules.HISTORICAL_EXCLUDE_CURRENT_SEMESTER",
        section="Regras",
        label="Excluir Semestre Atual do Histórico",
        description="Ignora o semestre atual ao calcular frequência histórica.",
        value_type=bool,
        default=True,
        order=190,
    ),
]


def build_default_scoring_config() -> Dict[str, Dict[str, Any]]:
    """Build the canonical scoring configuration from the registry."""
    config: Dict[str, Dict[str, Any]] = {"weights": {}, "rules": {}}

    for spec in SCORING_FIELD_SPECS:
        section, field_name = spec.key.split(".", 1)
        config.setdefault(section, {})
        config[section][field_name] = spec.default

    return config


def get_scoring_field_specs() -> List[ScoringFieldSpec]:
    """Return scoring field specifications ordered for UI rendering."""
    return sorted(SCORING_FIELD_SPECS, key=lambda spec: spec.order)


def get_scoring_spec_map() -> Dict[str, ScoringFieldSpec]:
    """Return scoring field specifications indexed by dotted key."""
    return {spec.key: spec for spec in SCORING_FIELD_SPECS}


def set_nested_value(config: Dict[str, Any], dotted_key: str, value: Any) -> None:
    """Set a nested configuration value using a dotted key."""
    section, field_name = dotted_key.split(".", 1)
    config.setdefault(section, {})
    config[section][field_name] = value


def get_nested_value(
    config: Dict[str, Any], dotted_key: str, default: Any = None
) -> Any:
    """Get a nested configuration value using a dotted key."""
    section, field_name = dotted_key.split(".", 1)
    return config.get(section, {}).get(field_name, default)


def filter_known_scoring_config(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return only supported scoring configuration keys from a config dictionary."""
    filtered = build_default_scoring_config()

    for spec in get_scoring_field_specs():
        if get_nested_value(config, spec.key, None) is not None:
            set_nested_value(filtered, spec.key, get_nested_value(config, spec.key))

    return filtered


def diff_scoring_config(
    effective_config: Dict[str, Any], defaults: Dict[str, Any] | None = None
) -> Dict[str, Dict[str, Any]]:
    """Return only fields that differ from defaults."""
    defaults = defaults or build_default_scoring_config()
    diff: Dict[str, Dict[str, Any]] = {"weights": {}, "rules": {}}

    for spec in get_scoring_field_specs():
        current_value = get_nested_value(effective_config, spec.key, spec.default)
        default_value = get_nested_value(defaults, spec.key, spec.default)
        if current_value != default_value:
            set_nested_value(diff, spec.key, current_value)

    return {section: values for section, values in diff.items() if values}


def validate_scoring_config_values(config: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate a scoring configuration against the registry and business rules."""
    errors: List[str] = []

    for spec in get_scoring_field_specs():
        value = get_nested_value(config, spec.key, spec.default)

        if spec.value_type is bool:
            if not isinstance(value, bool):
                errors.append(f"{spec.key} deve ser booleano, recebido: {value!r}")
            continue

        if not isinstance(value, int):
            errors.append(f"{spec.key} deve ser inteiro, recebido: {value!r}")
            continue

        if spec.min_value is not None and value < spec.min_value:
            errors.append(f"{spec.key} deve ser >= {spec.min_value}, recebido: {value}")

        if spec.max_value is not None and value > spec.max_value:
            errors.append(f"{spec.key} deve ser <= {spec.max_value}, recebido: {value}")

    historical_cap = get_nested_value(config, "weights.HISTORICAL_FREQUENCY_MAX_CAP", 0)
    historical_per_allocation = get_nested_value(
        config, "weights.HISTORICAL_FREQUENCY_PER_ALLOCATION", 0
    )
    if historical_cap < historical_per_allocation:
        errors.append(
            "weights.HISTORICAL_FREQUENCY_MAX_CAP não pode ser menor que "
            "weights.HISTORICAL_FREQUENCY_PER_ALLOCATION"
        )

    return (len(errors) == 0, errors)
