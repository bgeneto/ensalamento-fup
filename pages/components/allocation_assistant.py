"""Allocation assistant component for manual room selection and allocation."""

import streamlit as st
from typing import Optional, Dict, Any
import pandas as pd

from src.config.database import get_db_session
from src.services.manual_allocation_service import ManualAllocationService
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.sala import SalaRepository
from src.utils.cache_helpers import get_sigaa_parser


def _get_predio_name_from_id(predio_id: int, session) -> str:
    """Get building name from ID."""
    from sqlalchemy import text

    stmt = text("SELECT nome FROM predios WHERE id = :pid")
    row = session.execute(stmt, {"pid": predio_id}).fetchone()
    return row[0] if row else "N/A"


def _get_tipo_sala_name_from_id(tipo_sala_id: int, session) -> str:
    """Get room type name from ID."""
    from sqlalchemy import text

    stmt = text("SELECT nome FROM tipos_sala WHERE id = :tid")
    row = session.execute(stmt, {"tid": tipo_sala_id}).fetchone()
    return row[0] if row else "N/A"


def render_allocation_assistant(demanda_id: int, semester_id: int) -> Optional[dict]:
    """
    Render the allocation assistant panel for a selected demand.

    Returns:
        dict with keys:
            - action_taken: bool - True if user performed allocation or cancelled
            - allocation_success: bool - True if allocation succeeded
            - feedback_message: str - Feedback message to display (if allocation_success is not None)
        None if no action was taken (just displaying)
    """
    st.header("🖱️ Assistente de Alocação")

    with get_db_session() as session:
        demanda_repo = DisciplinaRepository(session)
        sala_repo = SalaRepository(session)
        alloc_service = ManualAllocationService(session)

        # Get demand details
        demanda = demanda_repo.get_by_id(demanda_id)
        if not demanda:
            st.error("❌ Demanda não encontrada.")
            return False

        # Show demand summary
        st.subheader(f"📚 Alocando: {demanda.nome_disciplina}")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Código", demanda.codigo_disciplina or "N/A")

        with col2:
            st.metric("Turma", f"T{demanda.turma_disciplina or 'N/A'}")

        with col3:
            st.metric("Vagas", demanda.vagas_disciplina or 0)

        # Show schedule
        if demanda.horario_sigaa_bruto:
            parser = get_sigaa_parser()
            horario_readable = parser.parse_to_human_readable(
                demanda.horario_sigaa_bruto
            )
            st.info(f"📅 **Horário:** {horario_readable}")

            # Show atomic blocks
            atomic_blocks = parser.split_to_atomic_tuples(demanda.horario_sigaa_bruto)
            blocks_display = ", ".join(
                [f"{dia}{bloco}" for bloco, dia in atomic_blocks]
            )
            st.caption(f"Blocos atômicos: {blocks_display}")

        # Get suggestions
        suggestions = alloc_service.get_suggestions_for_demand(demanda_id, semester_id)

        if not suggestions.top_suggestions:
            st.warning("Nenhuma sugestão de sala encontrada.", icon="⚠️")

        # Display top suggestions
        if suggestions.top_suggestions:
            result = _render_suggestions_section(
                "🏆 Sugestões Principais",
                suggestions.top_suggestions,
                demanda_id,
                alloc_service,
                semester_id,
            )
            if result:
                return result

        # Display other available rooms
        if suggestions.other_available:
            with st.expander(
                f"📋 Outras Salas Disponíveis ({len(suggestions.other_available)})",
                expanded=len(suggestions.top_suggestions) == 0,
            ):
                result = _render_suggestions_section(
                    "Salas disponíveis com pontuação menor",
                    suggestions.other_available,
                    demanda_id,
                    alloc_service,
                    semester_id,
                )
                if result:
                    return result

        # Display conflicting rooms
        if suggestions.conflicting_rooms:
            with st.expander(
                f"⚠️ Salas Adequadas mas Indisponíveis ({len(suggestions.conflicting_rooms)})"
            ):
                _render_conflicting_rooms_section(suggestions.conflicting_rooms)

        # Manual selection option
        st.markdown("---")
        result = _render_manual_selection(demanda, sala_repo, alloc_service, session)
        if result:
            return result

        # Cancel button
        if st.button(
            "❌ Cancelar Alocação",
            type="secondary",
            help="Limpar seleção e voltar para fila",
        ):
            if "allocation_selected_demand" in st.session_state:
                del st.session_state.allocation_selected_demand
            return {"action_taken": True}  # Trigger refresh


def _render_suggestions_section(
    title: str,
    room_suggestions,
    demanda_id: int,
    alloc_service: ManualAllocationService,
    semester_id: int,
) -> bool:
    """Render a section of room suggestions."""
    action_taken = False

    for suggestion in room_suggestions:
        action_taken = _render_room_suggestion_card(
            suggestion, demanda_id, alloc_service
        )
        if action_taken:
            break

    return action_taken


def _render_room_suggestion_card(
    suggestion, demanda_id: int, alloc_service: ManualAllocationService
) -> Optional[dict]:
    """Render a single room suggestion card with allocation button."""
    with st.container(border=True):
        # Room header
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**{suggestion.nome_sala}** (Cap: {suggestion.capacidade})")
            st.caption(f"Tipo: {suggestion.tipo_sala_nome} | Andar: {suggestion.andar}")

            # Show compatibility score and reasons
            if suggestion.compatibility_score > 0:
                score_color = "🟢" if suggestion.compatibility_score >= 5 else "🟡"
                st.caption(f"{score_color} Pontuação: {suggestion.compatibility_score}")

                # Show detailed breakdown if available
                if suggestion.scoring_breakdown:
                    with st.expander(
                        "📊 Detalhes da Pontuação", expanded=False, width="stretch"
                    ):
                        breakdown = suggestion.scoring_breakdown

                        # Display scoring categories with points
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("**Capacidade:**")
                            if breakdown.get("capacity_satisfied", False):
                                st.success(
                                    f"✅ Adequada (+{breakdown.get('capacity_points', 0)})"
                                )
                            else:
                                st.error(
                                    f"❌ Insuficiente (+{breakdown.get('capacity_points', 0)})"
                                )

                            st.markdown("**Regras Obrigatórias:**")
                            hard_rules = breakdown.get("hard_rules_satisfied", [])
                            if hard_rules:
                                rules_details = "<br>• ".join(hard_rules)
                                st.success(
                                    f"✅ Atendidas (+{breakdown.get('hard_rules_points', 0)})<br>• {rules_details}"
                                )
                            else:
                                st.error(
                                    f"❌ Não atendidas (+{breakdown.get('hard_rules_points', 0)})"
                                )

                        with col2:
                            st.markdown("**Preferências Professor:**")
                            soft_prefs = breakdown.get("soft_preferences_satisfied", [])
                            if soft_prefs:
                                prefs_details = "<br>• ".join(soft_prefs)
                                st.success(
                                    f"✅ Atendidas (+{breakdown.get('soft_preference_points', 0)})<br>• {prefs_details}"
                                )
                            else:
                                st.info(
                                    f"⏸️ Não verificadas (+{breakdown.get('soft_preference_points', 0)})"
                                )

                            st.markdown("**Frequência Histórica:**")
                            hist_count = breakdown.get("historical_allocations", 0)
                            if hist_count > 0:
                                st.info(
                                    f"📈 Alocada {hist_count}x aqui (+{breakdown.get('historical_frequency_points', 0)})"
                                )
                            else:
                                st.info(
                                    f"📉 Nunca alocada (+{breakdown.get('historical_frequency_points', 0)})"
                                )

                        # Total summary
                        st.markdown("---")
                        st.markdown(
                            f"**Total: {suggestion.compatibility_score} pontos**"
                        )
                else:
                    # Fallback to simple motivation display
                    st.caption(suggestion.motivation_reason)

            # Show rule violations
            if suggestion.rule_violations:
                st.warning("⚠️ Violações: " + "; ".join(suggestion.rule_violations))

        with col2:
            button_key = f"alloc_{suggestion.sala_id}"
            button_label = (
                "✅ Alocar Aqui" if not suggestion.has_conflicts else "❌ Conflito"
            )

            if suggestion.has_conflicts:
                # Disabled button for conflicting rooms
                st.button(
                    button_label,
                    disabled=True,
                    key=button_key,
                    width="stretch",
                )

                # Show conflict details
                if suggestion.conflict_details:
                    for conflict in suggestion.conflict_details[:3]:  # Limit to 3
                        st.caption(f"🔴 {conflict}")
            else:
                # Enabled allocation button
                if st.button(
                    button_label,
                    key=button_key,
                    width="stretch",
                    type="primary",
                    help=f"Alocar demanda nesta sala",
                ):
                    # Execute allocation
                    result = alloc_service.allocate_demand(
                        demanda_id, suggestion.sala_id
                    )

                    # Clear selection and return action result
                    if "allocation_selected_demand" in st.session_state:
                        del st.session_state.allocation_selected_demand

                    # Return structured data instead of boolean
                    feedback_message = (
                        f"Alocação realizada! {result.allocated_blocks_count} blocos criados na sala '{suggestion.nome_sala}'"
                        if result.success
                        else f"❌ Falha na alocação: {result.error_message}"
                    )

                    return {
                        "action_taken": True,
                        "allocation_success": result.success,
                        "feedback_message": feedback_message,
                    }

    return False


def _render_conflicting_rooms_section(conflicting_rooms):
    """Render section showing rooms with conflicts."""
    if not conflicting_rooms:
        st.write("Nenhum conflito encontrado.")
        return

    for room in conflicting_rooms[:5]:  # Limit display
        with st.container(border=True):
            st.markdown(f"**{room.nome_sala}** (Cap: {room.capacidade})")
            st.caption(f"Motivo: {room.motivation_reason}")

            # Show conflicts
            if room.conflict_details:
                for conflict in room.conflict_details[:3]:
                    st.caption(f":red[• {conflict}]")


def _render_manual_selection(
    demanda, sala_repo: SalaRepository, alloc_service: ManualAllocationService, session
):
    """Render manual room selection option."""
    st.subheader("🎯 Seleção Manual de Sala")

    # Allow manual selection even if suggestions exist
    # This respects the "fully manual" requirement

    with st.expander("Selecionar Sala Manualmente", expanded=False):
        st.write(
            "⚠️ **Atenção:** Esta seleção manual não verifica as regras de alocação automaticamente."
        )

        # Get all rooms for selection
        all_rooms = sala_repo.get_all()
        room_options = {}

        # Build room options with proper building name lookup
        for room in all_rooms:
            # Use helper function to get building name since SalaRead DTO only has predio_id
            predio_name = _get_predio_name_from_id(room.predio_id, session)
            room_options[room.id] = f"{predio_name}: {room.nome}"

        selected_room_id = st.selectbox(
            "Escolher sala:",
            options=[None] + list(room_options.keys()),
            format_func=lambda x: room_options.get(x, "Selecionar sala..."),
            key="manual_room_select",
        )

        if selected_room_id:
            # Show room details
            selected_room = next(
                (r for r in all_rooms if r.id == selected_room_id), None
            )
            if selected_room:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Capacidade", selected_room.capacidade or 0)
                with col2:
                    # Get room type name since SalaRead DTO only has tipo_sala_id
                    tipo_sala_name = _get_tipo_sala_name_from_id(
                        selected_room.tipo_sala_id, session
                    )
                    st.metric("Tipo", tipo_sala_name)
                with col3:
                    st.metric("Andar", selected_room.andar or "N/A")

                # Allocation button with confirmation dialog
                if st.button(
                    "🔧 Alocar Manualmente", type="primary", key="manual_allocate_btn"
                ):
                    # Confirmation dialog
                    if st.checkbox("⚠️ Confirmar alocação manual - pode violar regras"):
                        result = alloc_service.allocate_demand(
                            demanda.id, selected_room_id
                        )

                        # Clear selection and return action result
                        if "allocation_selected_demand" in st.session_state:
                            del st.session_state.allocation_selected_demand

                        # Return structured data instead of boolean
                        predio_name = _get_predio_name_from_id(
                            selected_room.predio_id, session
                        )
                        feedback_message = (
                            f"✅ Alocação manual realizada! {result.allocated_blocks_count} blocos criados em '{predio_name}: {selected_room.nome}'"
                            if result.success
                            else f"❌ Falha na alocação: {result.error_message}"
                        )

                        return {
                            "action_taken": True,
                            "allocation_success": result.success,
                            "feedback_message": feedback_message,
                        }
