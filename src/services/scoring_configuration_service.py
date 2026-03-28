"""DB-backed scoring configuration service."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from copy import deepcopy
from typing import Any, Dict, Generator, List

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.config.database import get_db_session
from src.config.scoring_registry import (
    CURRENT_SCORING_DEFAULTS_REVISION,
    CURRENT_SCORING_SCHEMA_VERSION,
    build_default_scoring_config,
    diff_scoring_config,
    get_nested_value,
    get_scoring_field_specs,
    set_nested_value,
    validate_scoring_config_values,
)
from src.repositories.app_configuration import AppConfigurationRepository

logger = logging.getLogger(__name__)


class ScoringConfigurationService:
    """Load, validate, migrate, and persist scoring configuration."""

    CONFIG_KEY = "scoring"

    def __init__(self, session: Session | None = None):
        self._session = session

    def get_effective_config_dict(self) -> Dict[str, Any]:
        """Return the effective scoring configuration from defaults + DB overrides."""
        defaults = build_default_scoring_config()

        record = self._get_active_record()
        if record:
            migrated_overrides = self._migrate_overrides_to_current(
                record.overrides_json,
                record.schema_version,
            )
            effective = self._merge_config(defaults, migrated_overrides)
            is_valid, errors = validate_scoring_config_values(effective)
            if is_valid:
                return effective

            logger.error(
                "Invalid scoring configuration stored in DB. Falling back to defaults. Errors: %s",
                "; ".join(errors),
            )
            return defaults

        return defaults

    def get_ui_rows(self) -> List[Dict[str, Any]]:
        """Return scoring rows for UI rendering."""
        effective = self.get_effective_config_dict()
        defaults = build_default_scoring_config()
        rows = []

        for spec in get_scoring_field_specs():
            current_value = get_nested_value(effective, spec.key, spec.default)
            default_value = get_nested_value(defaults, spec.key, spec.default)
            rows.append(
                {
                    "Chave": spec.key,
                    "Parâmetro": spec.label,
                    "Valor Atual": current_value,
                    "Valor Padrão": default_value,
                    "Categoria": spec.section,
                    "Descrição": spec.description,
                    "Origem": (
                        "override" if current_value != default_value else "default"
                    ),
                    "Tipo": "bool" if spec.value_type is bool else "int",
                    "Mínimo": spec.min_value,
                    "Máximo": spec.max_value,
                }
            )

        return rows

    def save_effective_config(
        self,
        effective_config: Dict[str, Any],
        *,
        username: str | None = None,
        reason: str | None = None,
        source: str = "ui",
    ) -> Dict[str, Any]:
        """Persist a full effective config by storing only its overrides."""
        defaults = build_default_scoring_config()
        normalized = self._normalize_config(effective_config)
        is_valid, errors = validate_scoring_config_values(normalized)
        if not is_valid:
            raise ValueError("; ".join(errors))

        overrides = diff_scoring_config(normalized, defaults=defaults)

        with self._session_scope() as session:
            repo = AppConfigurationRepository(session)
            try:
                repo.upsert(
                    config_key=self.CONFIG_KEY,
                    schema_version=str(CURRENT_SCORING_SCHEMA_VERSION),
                    overrides_json=overrides,
                    defaults_revision=CURRENT_SCORING_DEFAULTS_REVISION,
                    updated_by=username,
                    change_reason=reason,
                    source=source,
                )
                repo.add_history(
                    config_key=self.CONFIG_KEY,
                    schema_version=str(CURRENT_SCORING_SCHEMA_VERSION),
                    overrides_json=overrides,
                    effective_config_json=normalized,
                    changed_by=username,
                    change_reason=reason,
                    source=source,
                )
                session.commit()
            except Exception:
                session.rollback()
                raise

        return normalized

    def _get_active_record(self):
        try:
            with self._session_scope() as session:
                return AppConfigurationRepository(session).get_by_key(self.CONFIG_KEY)
        except OperationalError as exc:
            logger.debug("Scoring configuration DB read unavailable: %s", exc)
            return None

    @contextmanager
    def _session_scope(self) -> Generator[Session, None, None]:
        if self._session is not None:
            yield self._session
            return

        with get_db_session() as session:
            yield session

    def _normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        defaults = build_default_scoring_config()
        normalized = deepcopy(defaults)

        for spec in get_scoring_field_specs():
            value = get_nested_value(config, spec.key, spec.default)
            set_nested_value(normalized, spec.key, value)

        return normalized

    def _merge_config(
        self, defaults: Dict[str, Any], overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        merged = deepcopy(defaults)
        for spec in get_scoring_field_specs():
            value = get_nested_value(overrides, spec.key, None)
            if value is not None:
                set_nested_value(merged, spec.key, value)
        return merged

    def _migrate_overrides_to_current(
        self, overrides: Dict[str, Any], schema_version: str | None
    ) -> Dict[str, Any]:
        """Normalize persisted overrides to the current schema version."""
        current = self._normalize_partial_overrides(overrides)

        # Placeholder for future schema migrations.
        # When schema_version increases, add explicit transforms here.
        _ = schema_version
        return current

    def _normalize_partial_overrides(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {"weights": {}, "rules": {}}

        for spec in get_scoring_field_specs():
            value = get_nested_value(overrides, spec.key, None)
            if value is not None:
                set_nested_value(normalized, spec.key, value)

        return {section: values for section, values in normalized.items() if values}
