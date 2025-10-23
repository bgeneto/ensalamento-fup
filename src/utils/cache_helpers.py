"""
Streamlit caching helper functions for frequently-accessed reference data.

This module provides cached lookup functions to reduce database queries
for relatively static data like buildings, room types, characteristics, etc.

Cache Strategy:
- Reference data (buildings, types): 5-minute TTL
- Semester data: 10-minute TTL
- Singleton utility objects: @st.cache_resource (no TTL)

All functions are safe to call from any page without performance penalty.
"""

import streamlit as st
from typing import Dict, List, Tuple

from src.config.database import get_db_session
from src.repositories.predio import PredioRepository
from src.repositories.tipo_sala import TipoSalaRepository
from src.repositories.caracteristica import CaracteristicaRepository
from src.repositories.semestre import SemestreRepository
from src.utils.sigaa_parser import SigaaScheduleParser


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
