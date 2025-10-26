"""Reusable component for displaying the demand queue in manual allocation."""

import streamlit as st
from typing import List, Dict, Any, Optional
import pandas as pd

from src.config.database import get_db_session
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.sala import SalaRepository
from src.services.manual_allocation_service import ManualAllocationService
from src.utils.cache_helpers import get_sigaa_parser


def render_demand_queue(semester_id: int, filters: Optional[Dict[str, Any]] = None):
    """
    Render the demand queue with cards for demands based on allocation status filter.

    Args:
        semester_id: ID of the semester to show demands for
        filters: Optional filters to apply to the demand list

    Returns:
        bool: True if any allocation action was triggered (for page refresh)
    """
    st.header(f"📊 Status das Demandas")

    # Initialize filters if not provided
    if filters is None:
        filters = {}

    # Apply filters from UI controls (passed in filters dict)
    search_filter = filters.get("search_text", "")
    professor_filter = filters.get("professor_filter", "")
    course_filter = filters.get("course_filter", "")
    allocation_status_filter = filters.get("allocation_status", "unallocated")

    # Unique context identifier to avoid duplicate keys
    context_id = filters.get("context_id", f"queue_{allocation_status_filter}")

    with get_db_session() as session:
        alloc_service = ManualAllocationService(session)
        prof_repo = ProfessorRepository(session)
        sala_repo = SalaRepository(session)
        alocacao_repo = AlocacaoRepository(session)

        # Get allocation progress
        progress = alloc_service.get_allocation_progress(semester_id)

        # Progress bar and metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Demandas", f"{progress['total_demands']}")
        with col2:
            st.metric("Alocadas", f"{progress['allocated_demands']}")
        with col3:
            st.metric("Slots Pendentes", f"{progress['unallocated_demands']}")

        # Progress bar
        if progress["total_demands"] > 0:
            progress_pct = progress["allocation_percent"] / 100
            st.progress(progress_pct, text=f"{progress['allocation_percent']:.1f}%")

        # Get demands based on allocation status filter
        if allocation_status_filter == "allocated":
            demandas = alloc_service.get_allocated_demands(semester_id)
            header_title = f"Demandas Alocadas ({len(demandas)})"
        elif allocation_status_filter == "all":
            demandas = alloc_service.get_all_demands(semester_id)
            header_title = f"Todas as Demandas ({len(demandas)})"
        else:  # "unallocated" or default
            demandas = alloc_service.get_unallocated_demands(semester_id)
            header_title = f"Demandas Pendentes ({len(demandas)})"

        # Apply filters
        filtered_demands = _apply_filters(
            demandas, search_filter, professor_filter, course_filter
        )

        if not filtered_demands:
            st.warning("Nenhuma demanda encontrada com os filtros aplicados.", icon="⚠️")
            return False

        # Create allocation info mapping for all visible demands
        allocation_info_map = _get_allocation_info(
            filtered_demands, alocacao_repo, sala_repo
        )

        # Show count with appropriate title
        st.subheader(header_title)

        # Display as cards
        action_triggered = False
        for demanda in filtered_demands:
            demanda_id = getattr(demanda, "id")
            allocation_info = allocation_info_map.get(demanda_id)
            action_taken = _render_demand_card(
                demanda, prof_repo, allocation_info, context_id
            )
            if action_taken:
                action_triggered = True

        return action_triggered


def _apply_filters(
    demandas: List[Dict], search_text: str, professor_filter: str, course_filter: str
) -> List[Dict]:
    """Apply text and category filters to demands."""
    filtered = demandas.copy()

    # Text search filter
    if search_text:
        search_lower = search_text.lower()
        filtered = [
            d
            for d in filtered
            if (
                search_lower in str(d.get("codigo_disciplina", "")).lower()
                or search_lower in str(d.get("nome_disciplina", "")).lower()
            )
        ]

    # Professor filter
    if professor_filter:
        filtered = [
            d
            for d in filtered
            if professor_filter in str(d.get("professores_disciplina", ""))
        ]

    # Course filter
    if course_filter:
        filtered = [
            d for d in filtered if course_filter == str(d.get("codigo_curso", ""))
        ]

    return filtered


def _get_allocation_info(
    demandas, alocacao_repo: AlocacaoRepository, sala_repo: SalaRepository
) -> Dict[int, Dict]:
    """
    Get allocation information for a list of demands.

    Returns a dict mapping demanda_id to allocation info:
    {
        demanda_id: {
            'is_allocated': bool,
            'room_name': str or None,
            'allocations': [allocation_dto, ...]
        }
    }
    """
    allocation_info_map = {}

    for demanda in demandas:
        demanda_id = getattr(demanda, "id")
        allocations = alocacao_repo.get_by_demanda(demanda_id)

        if allocations:
            # Get room name from first allocation (assuming single room allocation)
            room_id = allocations[0].sala_id
            room_info = sala_repo.get_by_id(room_id)
            room_name = room_info.nome if room_info else f"Sala {room_id}"

            allocation_info_map[demanda_id] = {
                "is_allocated": True,
                "room_name": room_name,
                "allocations": allocations,
            }
        else:
            allocation_info_map[demanda_id] = {
                "is_allocated": False,
                "room_name": None,
                "allocations": [],
            }

    return allocation_info_map


def _render_demand_card(
    demanda,
    prof_repo: ProfessorRepository,
    allocation_info: Optional[Dict] = None,
    context_id: str = "",
) -> bool:
    """
    Render a single demand card.

    Args:
        demanda: Demand object
        prof_repo: Professor repository for professor info
        allocation_info: Allocation info dict (from _get_allocation_info)

    Returns:
        bool: True if allocation action was triggered.
    """
    with st.container(border=True):
        col_info, col_action = st.columns([3, 1])

        with col_info:
            # Header with discipline info
            discipline_name = getattr(demanda, "nome_disciplina", "N/A")
            discipline_code = getattr(demanda, "codigo_disciplina", "N/A")
            turma = getattr(demanda, "turma_disciplina", "N/A")

            st.markdown(f"**{discipline_code} - {discipline_name}** (T{turma})")

            # Secondary info
            professors = getattr(demanda, "professores_disciplina", "N/A")
            capacity = getattr(demanda, "vagas_disciplina", 0)

            st.caption(f"👨‍🏫 **Professores:** {professors}")
            st.caption(f"👥 **Vagas:** {capacity}")

            # Room allocation info for allocated demands
            if allocation_info and allocation_info.get("is_allocated"):
                room_name = allocation_info.get("room_name", "N/A")
                st.caption(f"🏢 **Sala Alocada:** {room_name}")

            # Schedule info
            horario_bruto = getattr(demanda, "horario_sigaa_bruto", "")
            if horario_bruto:
                parser = get_sigaa_parser()
                horario_readable = parser.parse_to_human_readable(horario_bruto)
                st.caption(f"📅 **Horário:** {horario_readable}")

            # Rule warnings (simplified - would need more logic in real implementation)
            # Could check for hard rules that apply to this discipline
            rule_warnings = _check_rule_warnings(demanda)
            if rule_warnings:
                st.warning("⚠️ " + "; ".join(rule_warnings))

        with col_action:
            demanda_id = getattr(demanda, "id")
            is_allocated = allocation_info and allocation_info.get(
                "is_allocated", False
            )

            if is_allocated:
                # Show deallocation button for allocated demands
                button_key = f"dealloc_demand_{demanda_id}_{context_id}"
                if st.button(
                    "Remover",
                    icon="❌",
                    key=button_key,
                    help=f"Remover alocação de {discipline_code}",
                    use_container_width=True,
                ):
                    # Set session state for deallocation
                    st.session_state.deallocation_selected_demand = demanda_id
                    return True
            else:
                # Show allocation button for unallocated demands
                button_key = f"alloc_demand_{demanda_id}_{context_id}"
                if st.button(
                    "Alocar Sala",
                    icon="🎯",
                    key=button_key,
                    help=f"Iniciar alocação para {discipline_code}",
                    use_container_width=True,
                ):
                    # Set session state to show allocation assistant
                    st.session_state.allocation_selected_demand = demanda_id
                    return True

    return False


def _check_rule_warnings(demanda) -> List[str]:
    """
    Check for rule-related warnings for this demand.

    In a full implementation, this would query rules and check for:
    - Disciplines requiring specific room types
    - Professor accessibility requirements
    - Equipment requirements
    """
    warnings = []

    # Example placeholder logic - would be replaced with actual rule checking
    # This is simplified for the demonstration

    professors = str(getattr(demanda, "professores_disciplina", "")).lower()

    # Check for accessibility needs (simplified)
    if any(term in professors for term in ["baixa mobilidade", "cadeira de rodas"]):
        warnings.append("Professor com restrição de mobilidade")

    return warnings
