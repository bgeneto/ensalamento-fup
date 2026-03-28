"""Reusable component for displaying the demand queue in manual allocation."""

import unicodedata
from typing import Any, Dict, List, Optional

import streamlit as st

from src.config.database import get_db_session
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.sala import SalaRepository
from src.services.hybrid_discipline_service import REGULAR_CLASSROOM_TYPE_ID
from src.services.manual_allocation_service import ManualAllocationService
from src.utils.cache_helpers import get_sigaa_parser
from src.utils.hybrid_detection_runtime import get_hybrid_status_for_demand


def render_demand_queue(semester_id: int, filters: Optional[Dict[str, Any]] = None):
    """
    Render the demand queue with cards for demands based on allocation status filter.

    Args:
        semester_id: ID of the semester to show demands for
        filters: Optional filters to apply to the demand list

    Returns:
        bool: True if any allocation action was triggered (for page refresh)
    """
    st.header("📊 Status das Demandas")

    # Initialize filters if not provided
    if filters is None:
        filters = {}

    # Apply filters from UI controls (passed in filters dict)
    search_filter = filters.get("search_text", "")
    professor_filter = filters.get("professor_filter", "")
    course_filter = filters.get("course_filter", "")
    discipline_filter = filters.get("discipline_filter", "")
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
            st.metric("Pendentes", f"{progress['unallocated_demands']}")

        # Progress bar
        if progress["total_demands"] > 0:
            progress_pct = progress["allocation_percent"] / 100
            st.progress(progress_pct, text=f"{progress['allocation_percent']:.1f}%")

        # Get demands based on allocation status filter
        if allocation_status_filter == "allocated":
            demandas = alloc_service.get_allocated_demands(semester_id)
            header_prefix = "Demandas Alocadas"
        elif allocation_status_filter == "all":
            demandas = alloc_service.get_all_demands(semester_id)
            header_prefix = "Todas as Demandas"
        else:  # "unallocated" or default
            demandas = alloc_service.get_unallocated_demands(semester_id)
            header_prefix = "Demandas Pendentes"

        # Apply filters
        filtered_demands = _apply_filters(
            demandas,
            search_filter,
            professor_filter,
            course_filter,
            discipline_filter,
        )

        if not filtered_demands:
            st.warning("Nenhuma demanda encontrada com os filtros aplicados.", icon="⚠️")
            return False

        total_demands = len(demandas)
        filtered_count = len(filtered_demands)
        if filtered_count == total_demands:
            header_title = f"{header_prefix} ({total_demands})"
        else:
            header_title = f"{header_prefix} ({filtered_count} de {total_demands})"

        # Create allocation info mapping for all visible demands
        allocation_info_map = _get_allocation_info(
            filtered_demands, alocacao_repo, sala_repo
        )

        # Show count with appropriate title
        st.subheader(header_title)

        # Sort demands by priority (unallocated first, then by complexity)
        sorted_demands = _sort_demands_by_priority(
            filtered_demands, allocation_info_map
        )

        # Display as cards
        action_triggered = False
        for demanda in sorted_demands:
            demanda_id = getattr(demanda, "id")
            allocation_info = allocation_info_map.get(demanda_id)
            action_taken = _render_demand_card(
                demanda, prof_repo, allocation_info, context_id, semester_id
            )
            if action_taken:
                action_triggered = True

        return action_triggered


def _apply_filters(
    demandas: List[Any],
    search_text: str,
    professor_filter: str,
    course_filter: str,
    discipline_filter: str = "",
) -> List[Any]:
    """Apply text and category filters to demands."""
    filtered = demandas.copy()

    # Discipline filter
    if discipline_filter and discipline_filter != "all":
        selected_code = str(discipline_filter).strip().upper()
        filtered = [
            d
            for d in filtered
            if str(_get_demand_value(d, "codigo_disciplina", "")).strip().upper()
            == selected_code
        ]

    # Text search filter
    if search_text:
        search_lower = search_text.lower()
        filtered = [
            d
            for d in filtered
            if (
                search_lower
                in str(_get_demand_value(d, "codigo_disciplina", "")).lower()
                or search_lower
                in str(_get_demand_value(d, "nome_disciplina", "")).lower()
            )
        ]

    # Professor filter
    if professor_filter and professor_filter != "all":
        filtered = [
            d
            for d in filtered
            if professor_filter
            in str(_get_demand_value(d, "professores_disciplina", ""))
        ]

    # Course filter
    if course_filter:
        filtered = [
            d
            for d in filtered
            if course_filter == str(_get_demand_value(d, "codigo_curso", ""))
        ]

    return filtered


def _get_demand_value(demanda: Any, field_name: str, default: Any = "") -> Any:
    """Read a demand field from DTOs or plain dicts."""
    if isinstance(demanda, dict):
        return demanda.get(field_name, default)
    return getattr(demanda, field_name, default)


def _normalize_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).lower()


def _is_laboratory_type_name(tipo_sala_nome: Optional[str]) -> bool:
    return "laboratorio" in _normalize_text(tipo_sala_nome)


def _get_allocation_info(
    demandas, alocacao_repo: AlocacaoRepository, sala_repo: SalaRepository
) -> Dict[int, Dict]:
    """
    Get allocation information for a list of demands.

    Returns a dict mapping demanda_id to allocation info:
    {
        demanda_id: {
            'is_allocated': bool,
            'room_name': str or None,  # Comma-separated if multiple rooms
            'room_names': [str, ...],  # List of all room names
            'is_split': bool,  # True if allocated to multiple rooms
            'allocations': [allocation_dto, ...]
        }
    }
    """
    allocation_info_map = {}
    parser = get_sigaa_parser()

    for demanda in demandas:
        demanda_id = getattr(demanda, "id")
        allocations = alocacao_repo.get_by_demanda(demanda_id)
        total_blocks = len(
            set(parser.split_to_atomic_tuples(demanda.horario_sigaa_bruto))
        )
        allocated_blocks = {
            (alloc.codigo_bloco, alloc.dia_semana_id) for alloc in allocations
        }
        allocated_count = len(allocated_blocks)
        pending_blocks = max(total_blocks - allocated_count, 0)
        is_fully_allocated = total_blocks > 0 and pending_blocks == 0
        is_partially_allocated = allocated_count > 0 and pending_blocks > 0

        if allocations:
            from src.models.inventory import TipoSala

            # Get ALL unique room IDs from allocations
            unique_room_ids = list(dict.fromkeys(a.sala_id for a in allocations))

            # Get room names for all unique rooms
            room_names = []
            room_type_ids = []
            for room_id in unique_room_ids:
                room_info = sala_repo.get_by_id(room_id)
                room_name = room_info.nome if room_info else f"Sala {room_id}"
                room_names.append(room_name)
                room_type_id = (
                    getattr(room_info, "tipo_sala_id", None) if room_info else None
                )
                room_type_ids.append(room_type_id)

            resolved_room_type_names = []
            for room_type_id in room_type_ids:
                if room_type_id is None:
                    resolved_room_type_names.append(None)
                    continue
                room_type_name = (
                    sala_repo.session.query(TipoSala.nome)
                    .filter(TipoSala.id == room_type_id)
                    .scalar()
                )
                resolved_room_type_names.append(room_type_name)

            has_classroom_room = any(
                room_type_id == REGULAR_CLASSROOM_TYPE_ID
                for room_type_id in room_type_ids
            )
            has_laboratory_room = any(
                _is_laboratory_type_name(room_type_name)
                for room_type_name in resolved_room_type_names
            )
            has_specialized_room = any(
                room_type_id not in (None, REGULAR_CLASSROOM_TYPE_ID)
                for room_type_id in room_type_ids
            )

            # Join room names for display
            room_name_display = ", ".join(room_names)
            is_split = len(unique_room_ids) > 1

            allocation_info_map[demanda_id] = {
                "is_allocated": is_fully_allocated,
                "is_fully_allocated": is_fully_allocated,
                "is_partially_allocated": is_partially_allocated,
                "room_name": room_name_display,
                "room_names": room_names,
                "is_split": is_split,
                "room_type_ids": room_type_ids,
                "room_type_names": resolved_room_type_names,
                "has_classroom_room": has_classroom_room,
                "has_laboratory_room": has_laboratory_room,
                "has_specialized_room": has_specialized_room,
                "allocated_blocks": allocated_count,
                "pending_blocks": pending_blocks,
                "total_blocks": total_blocks,
                "allocations": allocations,
            }
        else:
            allocation_info_map[demanda_id] = {
                "is_allocated": False,
                "is_fully_allocated": False,
                "is_partially_allocated": False,
                "room_name": None,
                "room_names": [],
                "is_split": False,
                "room_type_ids": [],
                "room_type_names": [],
                "has_classroom_room": False,
                "has_laboratory_room": False,
                "has_specialized_room": False,
                "allocated_blocks": 0,
                "pending_blocks": total_blocks,
                "total_blocks": total_blocks,
                "allocations": [],
            }

    return allocation_info_map


def _render_demand_card(
    demanda,
    prof_repo: ProfessorRepository,
    allocation_info: Optional[Dict] = None,
    context_id: str = "",
    semester_id: Optional[int] = None,
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
            if allocation_info and (
                allocation_info.get("is_fully_allocated")
                or allocation_info.get("is_partially_allocated")
            ):
                room_name = allocation_info.get("room_name", "N/A")
                is_split = allocation_info.get("is_split", False)
                allocated_blocks = allocation_info.get("allocated_blocks", 0)
                total_blocks = allocation_info.get("total_blocks", 0)

                if allocation_info.get("is_partially_allocated"):
                    st.caption(
                        f"🏢 **Alocação Parcial:** {room_name} ({allocated_blocks}/{total_blocks} blocos)"
                    )
                elif is_split:
                    # Multiple rooms - show with split indicator
                    st.caption(f"🏢 **Salas Alocadas:** {room_name} 🔀")
                else:
                    st.caption(f"🏢 **Sala Alocada:** {room_name}")

            # Schedule info
            horario_bruto = getattr(demanda, "horario_sigaa_bruto", "")
            if horario_bruto:
                parser = get_sigaa_parser()
                horario_readable = parser.parse_to_human_readable(horario_bruto)
                st.caption(f"📅 **Horário:** {horario_readable}")
            else:
                st.caption("📅 **Horário:** N/A")

            # Rule warnings (simplified - would need more logic in real implementation)
            # Could check for hard rules that apply to this discipline
            rule_warnings = _check_rule_warnings(demanda, semester_id, allocation_info)
            if rule_warnings:
                st.warning("⚠️ " + "; ".join(rule_warnings))

        with col_action:
            demanda_id = getattr(demanda, "id")
            is_fully_allocated = allocation_info and allocation_info.get(
                "is_fully_allocated", False
            )
            is_partially_allocated = allocation_info and allocation_info.get(
                "is_partially_allocated", False
            )

            if is_fully_allocated:
                # Show deallocation button for allocated demands
                button_key = f"dealloc_demand_{demanda_id}_{context_id}"
                if st.button(
                    "Remover",
                    icon="❌",
                    key=button_key,
                    help=f"Remover alocação de {discipline_code}",
                    width="stretch",
                ):
                    # Set session state for deallocation
                    st.session_state.deallocation_selected_demand = demanda_id
                    return True
            else:
                # Show allocation button for unallocated or partially allocated demands
                button_key = f"alloc_demand_{demanda_id}_{context_id}"
                if st.button(
                    "Continuar" if is_partially_allocated else "Alocar Sala",
                    icon="🎯",
                    key=button_key,
                    help=(
                        f"Continuar alocação para {discipline_code}"
                        if is_partially_allocated
                        else f"Iniciar alocação para {discipline_code}"
                    ),
                    width="stretch",
                ):
                    # Set session state to show allocation assistant
                    st.session_state.allocation_selected_demand = demanda_id
                    return True

    return False


def _check_rule_warnings(
    demanda,
    semester_id: Optional[int] = None,
    allocation_info: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Check for rule-related warnings for this demand.

    Checks for:
    - Disciplines requiring specific room types (from hybrid detection)
    - Laboratory requirements (from discipline name regex)
    - Professor accessibility requirements
    - High enrollment requirements
    """
    warnings = []

    professors = str(getattr(demanda, "professores_disciplina", "")).lower()
    discipline_name = str(getattr(demanda, "nome_disciplina", "")).lower()
    hybrid_status = get_hybrid_status_for_demand(demanda, semester_id)

    # Check for accessibility needs (simplified)
    if any(term in professors for term in ["baixa mobilidade", "cadeira de rodas"]):
        warnings.append("Professor com restrição de mobilidade")

    if hybrid_status["is_hybrid"]:
        warnings.append("🧪 Disciplina HÍBRIDA detectada")
    else:
        # Soft check for laboratory requirements (regex-based, less certain)
        if any(
            term in discipline_name for term in ["laboratório", "prático", "prática"]
        ):
            warnings.append("Disciplina pode necessitar de laboratório")

    # Check for high enrollment (may need larger rooms)
    vagas = getattr(demanda, "vagas_disciplina", 0)
    if vagas and vagas > 60:
        warnings.append("Alta demanda - verificar capacidade da sala")

    return warnings


def _sort_demands_by_priority(demandas, allocation_info_map) -> List:
    """
    Sort demands by allocation priority for better user experience.

    Priority order:
    1. Unallocated demands with hard rules
    2. Unallocated demands with high enrollment
    3. Other unallocated demands
    4. Allocated demands
    """

    def get_priority_score(demanda):
        demanda_id = getattr(demanda, "id")
        allocation_info = allocation_info_map.get(demanda_id, {})

        # Already allocated - lowest priority
        if allocation_info.get("is_fully_allocated"):
            return (0, 0, 0)

        # Unallocated - calculate priority
        score = 100  # Base score for unallocated

        # High enrollment gets higher priority (up to +20 points)
        # Formula: +1 point per 10 students, capped at 20
        vagas = getattr(demanda, "vagas_disciplina", 0)
        enrollment_priority = min((vagas // 10), 20)

        # Laboratory courses get priority
        discipline_name = str(getattr(demanda, "nome_disciplina", "")).lower()
        lab_priority = (
            15
            if any(
                term in discipline_name for term in ["laboratório", "lab", "prático"]
            )
            else 0
        )

        return (score, lab_priority, enrollment_priority)

    return sorted(demandas, key=get_priority_score, reverse=True)
