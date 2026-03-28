"""
Streamlit caching helper functions for frequently-accessed reference data.

This module provides cached lookup functions to reduce database queries
for relatively static data like buildings, room types, characteristics, etc.

Cache Strategy:
- Reference data (buildings, types): 5-minute TTL
- Semester data: 10-minute TTL
- Schedule snapshots for visualization pages: 1-minute TTL
- Singleton utility objects: @st.cache_resource (no TTL)

All functions are safe to call from any page without performance penalty.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from src.config.database import get_db_session
from src.integrations.sigaa import SigaaPublicTurmasClient
from src.models.academic import Semestre
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.caracteristica import CaracteristicaRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.predio import PredioRepository
from src.repositories.reserva_ocorrencia import ReservaOcorrenciaRepository
from src.repositories.sala import SalaRepository
from src.repositories.semestre import SemestreRepository
from src.repositories.tipo_sala import TipoSalaRepository
from src.services.sigaa_discrepancy_service import SigaaDiscrepancyService
from src.utils.sigaa_parser import SigaaScheduleParser

SCHEDULE_SNAPSHOT_TTL_SECONDS = 60


# ============================================================================
# SINGLETON UTILITY OBJECTS (Stateless, never expires)
# ============================================================================


@st.cache_resource
def get_sigaa_parser() -> SigaaScheduleParser:
    """
    Get singleton SigaaScheduleParser instance (cached).

    This parser contains static lookup dictionaries and is safe to reuse
    across all pages and sessions.

    Returns:
        SigaaScheduleParser: Singleton parser instance

    Example:
        parser = get_sigaa_parser()
        readable = parser.parse_to_human_readable("24M12")
    """
    return SigaaScheduleParser()


@st.cache_resource
def get_sigaa_public_turmas_client() -> SigaaPublicTurmasClient:
    """
    Get singleton SigaaPublicTurmasClient instance (cached).

    The SIGAA public client owns HTTP/session resources and should be reused
    across comparison actions instead of being recreated on every click.

    Returns:
        SigaaPublicTurmasClient: Singleton client instance
    """
    return SigaaPublicTurmasClient()


@st.cache_resource
def get_sigaa_discrepancy_service() -> SigaaDiscrepancyService:
    """
    Get singleton SigaaDiscrepancyService instance (cached).

    The service is stateless and depends on cached SIGAA utilities, so it is
    safe and cheaper to reuse across pages and reruns.

    Returns:
        SigaaDiscrepancyService: Singleton comparison service instance
    """
    return SigaaDiscrepancyService(
        client=get_sigaa_public_turmas_client(),
        schedule_parser=get_sigaa_parser(),
    )


# ============================================================================
# REFERENCE DATA LOOKUPS (5-minute TTL - changes infrequently)
# ============================================================================


@st.cache_data(ttl=300)
def get_predio_options() -> Dict[int, str]:
    """
    Get building ID->name mapping (cached for 5 minutes).

    Returns:
        Dict mapping predio_id to predio name

    Example:
        options = get_predio_options()
        building_name = options.get(predio_id, "Unknown")
    """
    with get_db_session() as session:
        predios = PredioRepository(session).get_all()
        return {p.id: p.nome for p in predios}


@st.cache_data(ttl=300)
def get_tipo_sala_options() -> Dict[int, str]:
    """
    Get room type ID->name mapping (cached for 5 minutes).

    Returns:
        Dict mapping tipo_sala_id to room type name

    Example:
        options = get_tipo_sala_options()
        type_name = options.get(tipo_sala_id, "Unknown")
    """
    with get_db_session() as session:
        tipos = TipoSalaRepository(session).get_all()
        return {t.id: t.nome for t in tipos}


@st.cache_data(ttl=300)
def get_caracteristica_options() -> Dict[int, str]:
    """
    Get characteristic ID->name mapping (cached for 5 minutes).

    Returns:
        Dict mapping caracteristica_id to characteristic name

    Example:
        options = get_caracteristica_options()
        char_name = options.get(caracteristica_id, "Unknown")
    """
    with get_db_session() as session:
        caracteristicas = CaracteristicaRepository(session).get_all()
        return {c.id: c.nome for c in caracteristicas}


@st.cache_data(ttl=600)
def get_semester_options() -> List[Tuple[int, str]]:
    """
    Get semester options as (id, name) tuples (cached for 10 minutes).

    Semesters change very infrequently, so longer TTL is acceptable.

    Returns:
        List of (semester_id, semester_name) tuples, sorted by ID descending
        (most recent first)

    Example:
        semesters = get_semester_options()
        for sem_id, sem_name in semesters:
            st.selectbox(sem_name, ...)
    """
    with get_db_session() as session:
        semestres = SemestreRepository(session).get_all()
        # Sort by ID descending (most recent first)
        sorted_semesters = sorted(semestres, key=lambda s: s.id, reverse=True)
        return [(s.id, s.nome) for s in sorted_semesters]


@st.cache_data(ttl=SCHEDULE_SNAPSHOT_TTL_SECONDS, show_spinner=False)
def get_active_semester_snapshot() -> Optional[Dict[str, Any]]:
    """Get the current active semester metadata for public read-only pages."""
    with get_db_session() as session:
        active_semester = session.query(Semestre).filter(Semestre.status).first()
        if not active_semester:
            return None

        return {
            "id": active_semester.id,
            "nome": active_semester.nome,
            "data_inicial": active_semester.data_inicial,
            "data_final": active_semester.data_final,
        }


@st.cache_data(ttl=300, show_spinner=False)
def get_room_display_metadata() -> Dict[str, Any]:
    """Get room DTOs plus display metadata used by the visualization pages."""
    with get_db_session() as session:
        salas = SalaRepository(session).get_all()
        predios = PredioRepository(session).get_all()

        predios_options = {predio.id: predio.nome for predio in predios}
        salas_options = {
            sala.id: f"{predios_options.get(sala.predio_id, 'Prédio desconhecido')}: {sala.nome}"
            for sala in salas
        }
        room_to_predio = {sala.id: sala.predio_id for sala in salas}

        return {
            "salas": salas,
            "salas_options": salas_options,
            "predios_options": predios_options,
            "room_to_predio": room_to_predio,
        }


@st.cache_data(ttl=SCHEDULE_SNAPSHOT_TTL_SECONDS, show_spinner=False)
def get_semester_demands_snapshot(semester_id: int) -> List[Any]:
    """Get semester demands for filter and report generation."""
    with get_db_session() as session:
        return DisciplinaRepository(session).get_by_semestre(semester_id)


def _build_semester_reservation_allocations(
    occurrences: List[Any],
) -> Dict[int, List[Dict[str, Any]]]:
    """Aggregate semester-long reservations into weekly room slots."""
    reservations_by_room: Dict[int, List[Dict[str, Any]]] = {}
    seen_slots = set()

    for occurrence in occurrences:
        evento = occurrence.evento
        if not evento:
            continue

        recurrence_rule = evento.get_regra_recorrencia()
        if recurrence_rule.get("tipo") != "semestre_inteiro":
            continue

        try:
            day_id = (
                datetime.strptime(occurrence.data_reserva, "%Y-%m-%d").weekday() + 2
            )
        except ValueError:
            continue

        if day_id < 2 or day_id > 7:
            continue

        slot_key = (
            evento.sala_id,
            day_id,
            occurrence.codigo_bloco,
            evento.titulo_evento,
        )
        if slot_key in seen_slots:
            continue

        seen_slots.add(slot_key)
        reservations_by_room.setdefault(evento.sala_id, []).append(
            {
                "type": "semester_reservation",
                "titulo": evento.titulo_evento,
                "day_id": day_id,
                "codigo_bloco": occurrence.codigo_bloco,
            }
        )

    return reservations_by_room


@st.cache_data(ttl=SCHEDULE_SNAPSHOT_TTL_SECONDS, show_spinner=False)
def get_semester_schedule_snapshot(
    semester_id: int, include_semester_reservations: bool = False
) -> Dict[str, Any]:
    """Get cached schedule data used by the Home and Visualização pages."""
    with get_db_session() as session:
        aloc_repo = AlocacaoRepository(session)
        semestre_repo = SemestreRepository(session)
        ocorrencia_repo = ReservaOcorrenciaRepository(session)

        selected_semester = semestre_repo.get_by_id(semester_id)
        allocacoes = aloc_repo.get_by_semestre(semester_id)

        semester_reservation_allocations: Dict[int, List[Dict[str, Any]]] = {}
        if (
            include_semester_reservations
            and selected_semester
            and selected_semester.data_inicial
            and selected_semester.data_final
        ):
            reservation_occurrences = ocorrencia_repo.get_ocorrencias_by_date_range(
                selected_semester.data_inicial,
                selected_semester.data_final,
                room_ids=None,
            )
            semester_reservation_allocations = _build_semester_reservation_allocations(
                reservation_occurrences
            )

        return {
            "allocations": allocacoes,
            "semester_reservation_allocations": semester_reservation_allocations,
        }


# ============================================================================
# CACHE MANAGEMENT UTILITIES
# ============================================================================


def clear_all_caches():
    """
    Clear all Streamlit caches (data and resource).

    Use this when reference data has been updated and you need
    immediate cache invalidation.

    Example:
        # In admin page after adding new building
        if st.button("Clear Cache"):
            clear_all_caches()
            st.success("Cache cleared!")
            st.rerun()
    """
    st.cache_data.clear()
    st.cache_resource.clear()


def clear_reference_data_cache():
    """
    Clear only reference data caches (buildings, types, characteristics).

    More targeted than clear_all_caches() - preserves singleton objects.
    """
    # Clear specific cached functions
    get_predio_options.clear()
    get_tipo_sala_options.clear()
    get_caracteristica_options.clear()
    get_semester_options.clear()
    get_room_display_metadata.clear()


def clear_schedule_snapshot_cache():
    """Clear cached semester schedule payloads used by read-only visualization pages."""
    get_active_semester_snapshot.clear()
    get_semester_demands_snapshot.clear()
    get_semester_schedule_snapshot.clear()
