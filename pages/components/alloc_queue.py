"""Reusable component for displaying the demand queue in manual allocation."""

import streamlit as st
from typing import List, Dict, Any, Optional
import pandas as pd

from src.config.database import get_db_session
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.professor import ProfessorRepository
from src.services.manual_allocation_service import ManualAllocationService
from src.utils.cache_helpers import get_sigaa_parser


def render_demand_queue(semester_id: int, filters: Optional[Dict[str, Any]] = None):
    """
    Render the demand queue with cards for unallocated demands.

    Args:
        semester_id: ID of the semester to show demands for
        filters: Optional filters to apply to the demand list

    Returns:
        bool: True if any allocation action was triggered (for page refresh)
    """
    st.header(f"📋 Fila de Demandas Pendentes")

    # Initialize filters if not provided
    if filters is None:
        filters = {}

    # Apply filters from UI controls (passed in filters dict)
    search_filter = filters.get("search_text", "")
    professor_filter = filters.get("professor_filter", "")
    course_filter = filters.get("course_filter", "")

    with get_db_session() as session:
        alloc_service = ManualAllocationService(session)
        prof_repo = ProfessorRepository(session)

        # Get allocation progress
        progress = alloc_service.get_allocation_progress(semester_id)

        # Progress bar and metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Demandas", f"{progress['total_demands']}")
        with col2:
            st.metric("Alocadas", f"{progress['allocated_demands']}")
        with col3:
            st.metric("Pendentes", f"{progress['unallocated_demands']}")

        # Progress bar
        if progress["total_demands"] > 0:
            progress_pct = progress["allocation_percent"] / 100
            st.progress(progress_pct, text=f"{progress['allocation_percent']:.1f}%")

        # Get unallocated demands
        unallocated_demandas = alloc_service.get_unallocated_demands(semester_id)

        # Apply filters
        filtered_demands = _apply_filters(
            unallocated_demandas, search_filter, professor_filter, course_filter
        )

        if not filtered_demands:
            st.info("ℹ️ Nenhuma demanda encontrada com os filtros aplicados.")
            return False

        # Show count
        st.subheader(f"Demandas para Alocar ({len(filtered_demands)})")

        # Display as cards
        action_triggered = False
        for demanda in filtered_demands:
            action_taken = _render_demand_card(demanda, prof_repo)
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


def _render_demand_card(demanda, prof_repo: ProfessorRepository) -> bool:
    """
    Render a single demand card.

    Returns True if allocation action was triggered.
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
            # Allocation button - this sets session state for the main page
            demanda_id = getattr(demanda, "id")
            button_key = f"alloc_demand_{demanda_id}"

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
