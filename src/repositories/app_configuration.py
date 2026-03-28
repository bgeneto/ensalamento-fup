"""Repository for persisted application configuration records."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.models.app_configuration import AppConfiguration, AppConfigurationHistory
from src.schemas.app_configuration import (
    AppConfigurationHistoryRead,
    AppConfigurationRead,
)


class AppConfigurationRepository:
    """Data access layer for application configuration rows."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_key(self, config_key: str) -> Optional[AppConfigurationRead]:
        """Get an active configuration row by key."""
        record = (
            self.session.query(AppConfiguration)
            .filter(AppConfiguration.config_key == config_key)
            .first()
        )
        if not record:
            return None
        return self._to_read_dto(record)

    def upsert(
        self,
        *,
        config_key: str,
        schema_version: str,
        overrides_json: Dict[str, Any],
        defaults_revision: str | None,
        updated_by: str | None,
        change_reason: str | None,
        source: str,
    ) -> AppConfigurationRead:
        """Create or update the active configuration row for a key."""
        record = (
            self.session.query(AppConfiguration)
            .filter(AppConfiguration.config_key == config_key)
            .first()
        )

        if not record:
            record = AppConfiguration(
                config_key=config_key,
                schema_version=schema_version,
                overrides_json=self._dump_json(overrides_json),
                defaults_revision=defaults_revision,
                updated_by=updated_by,
                change_reason=change_reason,
                source=source,
            )
            self.session.add(record)
        else:
            record.schema_version = schema_version
            record.overrides_json = self._dump_json(overrides_json)
            record.defaults_revision = defaults_revision
            record.updated_by = updated_by
            record.change_reason = change_reason
            record.source = source

        self.session.flush()
        self.session.refresh(record)
        return self._to_read_dto(record)

    def add_history(
        self,
        *,
        config_key: str,
        schema_version: str,
        overrides_json: Dict[str, Any],
        effective_config_json: Dict[str, Any],
        changed_by: str | None,
        change_reason: str | None,
        source: str,
    ) -> AppConfigurationHistoryRead:
        """Persist an immutable historical snapshot."""
        record = AppConfigurationHistory(
            config_key=config_key,
            schema_version=schema_version,
            overrides_json=self._dump_json(overrides_json),
            effective_config_json=self._dump_json(effective_config_json),
            changed_by=changed_by,
            change_reason=change_reason,
            source=source,
        )
        self.session.add(record)
        self.session.flush()
        self.session.refresh(record)
        return self._history_to_read_dto(record)

    def _to_read_dto(self, record: AppConfiguration) -> AppConfigurationRead:
        return AppConfigurationRead(
            id=record.id,
            config_key=record.config_key,
            schema_version=record.schema_version,
            overrides_json=self._load_json(record.overrides_json),
            defaults_revision=record.defaults_revision,
            updated_by=record.updated_by,
            change_reason=record.change_reason,
            source=record.source,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _history_to_read_dto(
        self, record: AppConfigurationHistory
    ) -> AppConfigurationHistoryRead:
        return AppConfigurationHistoryRead(
            id=record.id,
            config_key=record.config_key,
            schema_version=record.schema_version,
            overrides_json=self._load_json(record.overrides_json),
            effective_config_json=self._load_json(record.effective_config_json),
            changed_by=record.changed_by,
            change_reason=record.change_reason,
            source=record.source,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _dump_json(self, payload: Dict[str, Any]) -> str:
        return json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)

    def _load_json(self, payload: str | None) -> Dict[str, Any]:
        if not payload:
            return {}
        return json.loads(payload)
