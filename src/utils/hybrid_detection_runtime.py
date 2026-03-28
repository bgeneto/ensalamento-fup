"""Shared runtime access to hybrid-discipline detection results.

This module gives Streamlit UI components access to the same hybrid detection
payload produced by the allocation engine, instead of re-implementing smaller
heuristics in each component.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from src.config.database import get_db_session
from src.services.hybrid_discipline_service import HybridDisciplineDetectionService
from src.utils.cache_helpers import get_sigaa_parser

HYBRID_RUNTIME_CACHE_KEY = "hybrid_detection_runtime_cache"


def _normalize_turma(turma_disciplina: Optional[str]) -> str:
    raw = str(turma_disciplina or "").strip()
    if not raw:
        return ""
    return raw.lstrip("0") or "0"


def build_offering_key(
    codigo_disciplina: str, turma_disciplina: Optional[str] = None
) -> str:
    code = str(codigo_disciplina or "").strip().upper()
    turma = _normalize_turma(turma_disciplina)
    return f"{code}::{turma}" if turma else code


def set_hybrid_detection_runtime_cache(
    current_semester_id: int,
    detection_summary: Dict[str, Any],
) -> None:
    """Persist the exact hybrid-detection payload for the current UI session."""
    cache = st.session_state.setdefault(HYBRID_RUNTIME_CACHE_KEY, {})
    cache[current_semester_id] = detection_summary


def get_hybrid_detection_runtime_cache(
    current_semester_id: int,
) -> Optional[Dict[str, Any]]:
    """Return cached hybrid detection payload for the semester, if available."""
    cache = st.session_state.get(HYBRID_RUNTIME_CACHE_KEY, {})
    if not isinstance(cache, dict):
        return None
    payload = cache.get(current_semester_id)
    return payload if isinstance(payload, dict) else None


def load_hybrid_detection_runtime_cache(
    current_semester_id: int,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """Load hybrid detection payload from shared session cache or recompute it once."""
    if not force_refresh:
        cached = get_hybrid_detection_runtime_cache(current_semester_id)
        if cached is not None:
            return cached

    with get_db_session() as session:
        hybrid_service = HybridDisciplineDetectionService(session)
        detection_semester_id = hybrid_service.resolve_detection_semester(
            current_semester_id
        )
        hybrid_service.detect_hybrid_disciplines(detection_semester_id)
        payload = hybrid_service.get_detection_summary()

    set_hybrid_detection_runtime_cache(current_semester_id, payload)
    return payload


def get_hybrid_status_for_demand(
    demanda: Any,
    current_semester_id: Optional[int],
) -> Dict[str, Any]:
    """Return the shared hybrid classification and slot requirements for a demand."""
    codigo_disciplina = getattr(demanda, "codigo_disciplina", "")
    turma_disciplina = getattr(demanda, "turma_disciplina", None)
    horario_sigaa_bruto = getattr(demanda, "horario_sigaa_bruto", "")
    offering_key = build_offering_key(codigo_disciplina, turma_disciplina)

    if not current_semester_id:
        return {
            "is_hybrid": False,
            "offering_key": offering_key,
            "current_slot_requirements": {},
            "all_slot_requirements": {},
            "detection_semester_id": None,
        }

    payload = load_hybrid_detection_runtime_cache(current_semester_id)
    details = payload.get("details", {}) if isinstance(payload, dict) else {}
    detail = details.get(offering_key)

    if not isinstance(detail, dict):
        return {
            "is_hybrid": False,
            "offering_key": offering_key,
            "current_slot_requirements": {},
            "all_slot_requirements": {},
            "detection_semester_id": payload.get("detection_semester_id"),
        }

    all_slot_requirements = detail.get("slot_requirements", {}) or {}
    parser = get_sigaa_parser()
    current_groups = parser.get_block_groups_with_names_and_turno(horario_sigaa_bruto)

    current_slot_requirements: Dict[str, str] = {}
    for group in current_groups:
        slot_key = f"{group['day_id']}_{group['turno']}"
        requirement = all_slot_requirements.get(slot_key)
        if requirement:
            current_slot_requirements[slot_key] = requirement

    return {
        "is_hybrid": True,
        "offering_key": offering_key,
        "current_slot_requirements": current_slot_requirements,
        "all_slot_requirements": all_slot_requirements,
        "detection_semester_id": payload.get("detection_semester_id"),
        "detail": detail,
    }
