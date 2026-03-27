"""Demand sync helpers for API snapshots and local overrides."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from sqlalchemy.orm import Session

from src.models.academic import Demanda
from src.models.base import utc_now_naive
from src.repositories.disciplina import DisciplinaRepository
from src.schemas.academic import DemandaCreate, DemandaRead

SNAPSHOT_FIELDS = (
    "codigo_curso",
    "codigo_disciplina",
    "nome_disciplina",
    "turma_disciplina",
    "vagas_disciplina",
    "professores_disciplina",
    "horario_sigaa_bruto",
)


class DemandaSyncService:
    """Encapsulates imported snapshot and local override behavior for demandas."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = DisciplinaRepository(session)

    def build_api_snapshot(self, source: dict[str, Any]) -> dict[str, Any]:
        """Normalize the imported API payload subset persisted as snapshot."""
        snapshot: dict[str, Any] = {}
        for field_name in SNAPSHOT_FIELDS:
            value = source.get(field_name)
            snapshot[field_name] = self._normalize_field_value(field_name, value)
        return snapshot

    def calculate_payload_hash(self, snapshot: dict[str, Any]) -> str:
        """Build a stable hash for the normalized snapshot payload."""
        normalized_snapshot = self.build_api_snapshot(snapshot)
        payload = json.dumps(
            normalized_snapshot,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def create_imported_demanda(self, demanda_data: dict[str, Any]) -> DemandaRead:
        """Create a demand imported from the API with snapshot metadata."""
        timestamp = utc_now_naive()
        snapshot = self.build_api_snapshot(demanda_data)
        dto_data = dict(demanda_data)
        dto_data.update(
            {
                "origem": "api",
                "sync_status": "active",
                "api_payload_hash": self.calculate_payload_hash(snapshot),
                "api_snapshot_json": snapshot,
                "local_overrides_json": {},
                "last_seen_in_api_at": timestamp,
                "last_synced_at": timestamp,
                "removed_from_api_at": None,
                "preservar_local_em_remocao_api": False,
                "revalidation_required": False,
            }
        )
        return self.repo.create(DemandaCreate(**dto_data))

    def create_manual_demanda(self, demanda_data: dict[str, Any]) -> DemandaRead:
        """Create a manual demand with explicit non-API sync semantics."""
        dto_data = dict(demanda_data)
        dto_data.update(
            {
                "origem": "manual",
                "sync_status": "manual",
                "api_payload_hash": None,
                "api_snapshot_json": {},
                "local_overrides_json": {},
                "last_seen_in_api_at": None,
                "last_synced_at": None,
                "removed_from_api_at": None,
                "preservar_local_em_remocao_api": False,
                "revalidation_required": False,
            }
        )
        return self.repo.create(DemandaCreate(**dto_data))

    def reconcile_imported_demanda(
        self, semestre_id: int, external_id: str, demanda_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create or update an imported demand while preserving local overrides."""
        source = dict(demanda_data)
        source["semestre_id"] = semestre_id
        source["id_oferta_externo"] = external_id

        existing = self.repo.get_by_semestre_and_external_id(semestre_id, external_id)
        if not existing:
            demanda = self.create_imported_demanda(source)
            return {
                "action": "created",
                "demanda": demanda,
                "revalidation_required": False,
            }

        demanda = self._get_demanda_or_raise(existing.id)
        previous_snapshot = demanda.api_snapshot_json or self._snapshot_from_demanda(
            demanda
        )
        new_snapshot = self.build_api_snapshot(source)
        new_hash = self.calculate_payload_hash(new_snapshot)
        was_removed = demanda.sync_status == "removed_in_api"
        had_allocations = self._has_allocations(demanda)
        critical_changed = self._critical_fields_changed(
            previous_snapshot, new_snapshot
        )

        if demanda.api_payload_hash == new_hash and not was_removed:
            timestamp = utc_now_naive()
            demanda.last_seen_in_api_at = timestamp
            demanda.last_synced_at = timestamp
            self.session.commit()
            self.session.refresh(demanda)
            return {
                "action": "unchanged",
                "demanda": self.repo.orm_to_dto(demanda),
                "revalidation_required": bool(demanda.revalidation_required),
            }

        updated = self.register_api_snapshot(demanda.id, source)
        demanda = self._get_demanda_or_raise(updated.id)

        if had_allocations and critical_changed:
            demanda.revalidation_required = True
            demanda.sync_status = "changed_in_api"
            self.session.commit()
            self.session.refresh(demanda)
            updated = self.repo.orm_to_dto(demanda)

        return {
            "action": "updated_from_api",
            "demanda": updated,
            "revalidation_required": bool(updated.revalidation_required),
        }

    def apply_manual_edit(
        self, demanda_id: int, changed_fields: dict[str, Any]
    ) -> DemandaRead:
        """Persist manual changes and maintain local overrides per field."""
        demanda = self._get_demanda_or_raise(demanda_id)
        snapshot = self.build_api_snapshot(
            demanda.api_snapshot_json or self._snapshot_from_demanda(demanda)
        )
        overrides = dict(demanda.local_overrides_json or {})

        for field_name, value in changed_fields.items():
            if not hasattr(demanda, field_name):
                continue

            normalized_value = self._normalize_field_value(field_name, value)
            setattr(demanda, field_name, normalized_value)

            if field_name in SNAPSHOT_FIELDS and demanda.origem == "api":
                api_value = snapshot.get(field_name)
                if normalized_value != api_value:
                    overrides[field_name] = normalized_value
                else:
                    overrides.pop(field_name, None)

        demanda.local_overrides_json = overrides
        demanda.sync_status = self._determine_sync_status(demanda, overrides)
        self.session.commit()
        self.session.refresh(demanda)
        return self.repo.orm_to_dto(demanda)

    def register_api_snapshot(
        self, demanda_id: int, snapshot_source: dict[str, Any]
    ) -> DemandaRead:
        """Update API snapshot and refresh effective values for non-overridden fields."""
        demanda = self._get_demanda_or_raise(demanda_id)
        timestamp = utc_now_naive()
        snapshot = self.build_api_snapshot(snapshot_source)
        overrides = dict(demanda.local_overrides_json or {})

        demanda.api_snapshot_json = snapshot
        demanda.api_payload_hash = self.calculate_payload_hash(snapshot)
        demanda.last_seen_in_api_at = timestamp
        demanda.last_synced_at = timestamp
        demanda.removed_from_api_at = None
        if demanda.sync_status == "removed_in_api":
            demanda.sync_status = "active"

        if demanda.origem != "manual":
            demanda.origem = "api"

        for field_name in SNAPSHOT_FIELDS:
            if field_name not in overrides:
                setattr(demanda, field_name, snapshot[field_name])

        demanda.sync_status = self._determine_sync_status(demanda, overrides)
        self.session.commit()
        self.session.refresh(demanda)
        return self.repo.orm_to_dto(demanda)

    def mark_missing_offers_as_removed(
        self, semestre_id: int, seen_external_ids: set[str]
    ) -> dict[str, int]:
        """Mark imported offers that disappeared from the API as logically removed."""
        timestamp = utc_now_naive()
        query = self.session.query(Demanda).filter(
            Demanda.semestre_id == semestre_id,
            Demanda.origem == "api",
            Demanda.id_oferta_externo.isnot(None),
        )
        if seen_external_ids:
            query = query.filter(~Demanda.id_oferta_externo.in_(seen_external_ids))

        removed_count = 0
        revalidation_count = 0

        for demanda in query.all():
            if demanda.sync_status == "removed_in_api":
                continue

            demanda.sync_status = "removed_in_api"
            demanda.removed_from_api_at = timestamp
            demanda.last_synced_at = timestamp
            if self._has_allocations(demanda):
                demanda.revalidation_required = True
                revalidation_count += 1
            removed_count += 1

        self.session.commit()
        return {
            "removed_in_api": removed_count,
            "revalidation_required": revalidation_count,
        }

    def get_effective_value(
        self, demanda: Demanda | DemandaRead, field_name: str
    ) -> Any:
        """Return the effective field value preferring explicit overrides."""
        overrides = getattr(demanda, "local_overrides_json", None) or {}
        if field_name in overrides:
            return overrides[field_name]
        snapshot = getattr(demanda, "api_snapshot_json", None) or {}
        if field_name in snapshot:
            return snapshot[field_name]
        return getattr(demanda, field_name)

    def _get_demanda_or_raise(self, demanda_id: int) -> Demanda:
        demanda = self.session.query(Demanda).filter(Demanda.id == demanda_id).first()
        if not demanda:
            raise ValueError(f"Demanda {demanda_id} não encontrada")
        return demanda

    def _determine_sync_status(
        self, demanda: Demanda, overrides: dict[str, Any] | Iterable[tuple[str, Any]]
    ) -> str:
        if demanda.sync_status == "removed_in_api" or demanda.removed_from_api_at:
            return "removed_in_api"
        if demanda.revalidation_required:
            return "changed_in_api"
        if demanda.origem == "manual":
            return "manual"
        overrides_dict = dict(overrides)
        return "manual_linked" if overrides_dict else "active"

    def _critical_fields_changed(
        self, previous_snapshot: dict[str, Any], new_snapshot: dict[str, Any]
    ) -> bool:
        previous = self.build_api_snapshot(previous_snapshot)
        current = self.build_api_snapshot(new_snapshot)
        critical_fields = {"horario_sigaa_bruto", "vagas_disciplina"}
        return any(
            previous.get(field) != current.get(field) for field in critical_fields
        )

    def _has_allocations(self, demanda: Demanda) -> bool:
        return bool(demanda.alocacoes)

    def _snapshot_from_demanda(self, demanda: Demanda) -> dict[str, Any]:
        return self.build_api_snapshot(
            {
                field_name: getattr(demanda, field_name, None)
                for field_name in SNAPSHOT_FIELDS
            }
        )

    def _normalize_field_value(self, field_name: str, value: Any) -> Any:
        if field_name in {
            "codigo_curso",
            "codigo_disciplina",
            "nome_disciplina",
            "turma_disciplina",
            "professores_disciplina",
            "horario_sigaa_bruto",
        }:
            return (value or "").strip()
        if field_name == "vagas_disciplina":
            try:
                return int(value or 0)
            except (TypeError, ValueError):
                return 0
        return value
