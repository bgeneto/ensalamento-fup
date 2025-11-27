"""Allocation assistant component for manual room selection and allocation."""

from typing import Dict, List, Optional

import streamlit as st

from src.config.database import get_db_session
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.sala import SalaRepository
from src.services.manual_allocation_service import ManualAllocationService
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

    Now supports partial/split allocation by allowing users to select
    specific block groups (days) and allocate them to different rooms.

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

        # ================================================================
        # NEW: Block Group Selection for Partial Allocation
        # ================================================================

        # Get allocation status and block groups
        alloc_status = alloc_service.get_allocation_status_for_demand(demanda_id)
        block_groups = alloc_status.get('block_groups', [])

        # Show allocation progress if partially allocated
        if alloc_status.get('is_partially_allocated'):
            allocated = alloc_status.get('allocated_blocks', 0)
            total = alloc_status.get('total_blocks', 0)
            st.warning(
                f"⚠️ **Alocação Parcial:** {allocated}/{total} blocos alocados. "
                f"Continue selecionando blocos para completar a alocação."
            )
        elif alloc_status.get('is_fully_allocated'):
            st.success("✅ **Totalmente Alocada:** Todos os blocos já estão alocados.")
            # Show allocated rooms
            for room_info in alloc_status.get('allocated_rooms', []):
                st.caption(f"📍 {room_info['room_name']}: {', '.join(room_info['blocks'])}")

            # Cancel button
            if st.button(
                "❌ Cancelar / Voltar",
                type="secondary",
                help="Voltar para fila",
            ):
                if "allocation_selected_demand" in st.session_state:
                    del st.session_state.allocation_selected_demand
                return {"action_taken": True}
            return None

        # ================================================================
        # Block Group Selection UI
        # ================================================================

        result = _render_block_group_selection(
            demanda_id, semester_id, block_groups, alloc_service, sala_repo, session
        )
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

        return None


def _render_block_group_selection(
    demanda_id: int,
    semester_id: int,
    block_groups: List[Dict],
    alloc_service: ManualAllocationService,
    sala_repo: SalaRepository,
    session,
) -> Optional[dict]:
    """
    Render block group selection with checkboxes for partial allocation.

    Users can select which day-groups to allocate to a specific room.
    """
    st.markdown("---")
    st.subheader("📅 Selecionar Blocos para Alocação")

    # Filter to show only unallocated block groups
    unallocated_groups = [g for g in block_groups if not g.get('is_allocated')]
    allocated_groups = [g for g in block_groups if g.get('is_allocated')]

    if not unallocated_groups:
        st.info("Todos os blocos já estão alocados.")
        return None

    # Show allocated groups (read-only)
    if allocated_groups:
        with st.expander(f"✅ Blocos já alocados ({len(allocated_groups)})", expanded=False):
            for group in allocated_groups:
                day_name = group.get('day_name', 'N/A')
                blocks = ', '.join(group.get('blocks', []))
                time_range = group.get('time_range', '')
                room_name = group.get('allocated_room_name', 'N/A')
                st.caption(f"📍 **{day_name}** ({blocks}) {time_range} → {room_name}")

    # Block group checkboxes for unallocated groups
    st.markdown("**Selecione os blocos a alocar:**")

    # Initialize session state for selected blocks if not exists
    session_key = f"selected_block_groups_{demanda_id}"
    if session_key not in st.session_state:
        # Default: select all unallocated groups
        st.session_state[session_key] = {g['day_id']: True for g in unallocated_groups}

    selected_day_ids = []

    # Create columns for block group checkboxes
    cols = st.columns(min(len(unallocated_groups), 4))

    for idx, group in enumerate(unallocated_groups):
        day_id = group.get('day_id')
        day_name = group.get('day_name', 'N/A')
        blocks = group.get('blocks', [])
        time_range = group.get('time_range', '')
        block_count = len(blocks)

        col_idx = idx % len(cols)
        with cols[col_idx]:
            # Checkbox for this block group
            checkbox_key = f"block_group_{demanda_id}_{day_id}"
            is_selected = st.checkbox(
                f"**{day_name}** ({block_count} blocos)",
                value=st.session_state[session_key].get(day_id, True),
                key=checkbox_key,
                help=f"{', '.join(blocks)} • {time_range}",
            )

            # Update session state
            st.session_state[session_key][day_id] = is_selected

            if is_selected:
                selected_day_ids.append(day_id)

            # Show blocks detail
            st.caption(f"{', '.join(blocks)}")
            st.caption(f"🕐 {time_range}")

    if not selected_day_ids:
        st.warning("⚠️ Selecione pelo menos um grupo de blocos para ver as sugestões.")
        return None

    # Show count of selected blocks
    selected_groups = [g for g in unallocated_groups if g['day_id'] in selected_day_ids]
    total_selected_blocks = sum(len(g.get('blocks', [])) for g in selected_groups)
    st.info(f"📊 **Selecionados:** {len(selected_day_ids)} dia(s), {total_selected_blocks} bloco(s)")

    # ================================================================
    # Room Suggestions for Selected Blocks
    # ================================================================

    st.markdown("---")
    st.subheader("🏆 Sugestões de Sala")

    # Get suggestions for the first selected day (they share similar scoring except historical)
    # For hybrid disciplines, user should allocate one day at a time for different rooms
    primary_day_id = selected_day_ids[0]

    suggestions = alloc_service.get_suggestions_for_block_group(
        demanda_id, primary_day_id, semester_id
    )

    if not suggestions:
        st.warning("Nenhuma sugestão encontrada para os blocos selecionados.")
    else:
        # Render top suggestions (top 5)
        top_suggestions = [s for s in suggestions if not s.get('has_conflict')][:5]

        if top_suggestions:
            for suggestion in top_suggestions:
                result = _render_block_group_room_card(
                    suggestion,
                    demanda_id,
                    selected_day_ids,
                    alloc_service,
                    session,
                )
                if result:
                    return result

        # Show conflicting rooms in expander
        conflicting = [s for s in suggestions if s.get('has_conflict')]
        if conflicting:
            with st.expander(f"⚠️ Salas com Conflitos ({len(conflicting)})", expanded=False):
                for room in conflicting[:5]:
                    _render_conflicting_room_brief(room)

    # ================================================================
    # Manual Selection (fallback)
    # ================================================================

    st.markdown("---")
    result = _render_manual_selection_partial(
        demanda_id, selected_day_ids, sala_repo, alloc_service, session
    )
    if result:
        return result

    return None


def _render_block_group_room_card(
    suggestion: Dict,
    demanda_id: int,
    selected_day_ids: List[int],
    alloc_service: ManualAllocationService,
    session,
) -> Optional[dict]:
    """Render a room suggestion card for block-group allocation."""
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])

        with col1:
            room_name = suggestion.get('room_name', 'N/A')
            building = suggestion.get('building_name', 'N/A')
            capacity = suggestion.get('room_capacity', 0)
            room_type = suggestion.get('room_type', 'N/A')
            score = suggestion.get('score', 0)

            st.markdown(f"**{building}: {room_name}** (Cap: {capacity})")
            st.caption(f"Tipo: {room_type} | Andar: 0")

            # Score display
            score_color = "🟢" if score >= 20 else "🟡" if score >= 5 else "🔴"
            st.caption(f"{score_color} Pontuação: {score}")

            # Detailed breakdown
            breakdown = suggestion.get('breakdown', {})
            if breakdown:
                with st.expander("📊 Detalhes da Pontuação", expanded=False):
                    col_a, col_b = st.columns(2)

                    with col_a:
                        st.markdown("**Capacidade:**")
                        if breakdown.get('capacity_satisfied', False):
                            st.success(f"✅ Adequada (+{breakdown.get('capacity_points', 0)})")
                        else:
                            st.error(f"❌ Insuficiente (+{breakdown.get('capacity_points', 0)})")

                        st.markdown("**Regras Obrigatórias:**")
                        hard_rules = breakdown.get('hard_rules_satisfied', [])
                        if hard_rules:
                            st.success(f"✅ Atendidas (+{breakdown.get('hard_rules_points', 0)})")
                        else:
                            st.error(f"❌ Não atendidas (+{breakdown.get('hard_rules_points', 0)})")

                    with col_b:
                        st.markdown("**Preferências Professor:**")
                        soft_prefs = breakdown.get('soft_preferences_satisfied', [])
                        if soft_prefs:
                            st.success(f"✅ Atendidas (+{breakdown.get('soft_preference_points', 0)})")
                        else:
                            st.info(f"⏸️ Não verificadas (+{breakdown.get('soft_preference_points', 0)})")

                        st.markdown("**Frequência Histórica:**")
                        hist_count = breakdown.get('historical_allocations', 0)
                        if hist_count > 0:
                            st.info(f"📈 Alocada {hist_count}x aqui (+{breakdown.get('historical_frequency_points', 0)})")
                        else:
                            st.info(f"📉 Nunca alocada (+{breakdown.get('historical_frequency_points', 0)})")

                    st.markdown(f"**Total: {score} pontos**")

        with col2:
            room_id = suggestion.get('room_id')
            button_key = f"alloc_partial_{demanda_id}_{room_id}"

            if st.button(
                "✅ Alocar Aqui",
                key=button_key,
                type="primary",
                help="Alocar blocos selecionados nesta sala",
            ):
                # Execute partial allocation
                result = alloc_service.allocate_demand_partial(
                    demanda_id,
                    room_id,
                    day_ids=selected_day_ids,
                )

                # Clear selection state
                session_key = f"selected_block_groups_{demanda_id}"
                if session_key in st.session_state:
                    del st.session_state[session_key]

                room_display = f"{suggestion.get('building_name', '')}: {suggestion.get('room_name', '')}"

                if result.success:
                    feedback_message = (
                        f"✅ Alocação parcial realizada! {len(result.allocated_blocks)} blocos alocados em '{room_display}'"
                    )
                    if result.remaining_blocks:
                        feedback_message += f". Restam {len(result.remaining_blocks)} blocos pendentes."
                else:
                    feedback_message = f"❌ Falha na alocação: {result.message}"

                return {
                    "action_taken": True,
                    "allocation_success": result.success,
                    "feedback_message": feedback_message,
                }

    return None


def _render_conflicting_room_brief(room: Dict):
    """Render a brief view of a conflicting room."""
    room_name = room.get('room_name', 'N/A')
    building = room.get('building_name', 'N/A')
    conflicts = room.get('conflict_details', [])

    st.caption(f"**{building}: {room_name}** - {', '.join(conflicts[:2])}")


def _render_manual_selection_partial(
    demanda_id: int,
    selected_day_ids: List[int],
    sala_repo: SalaRepository,
    alloc_service: ManualAllocationService,
    session,
) -> Optional[dict]:
    """Render manual room selection for partial allocation."""
    st.subheader("🎯 Seleção Manual de Sala")

    with st.expander("Selecionar Sala Manualmente", expanded=False):
        st.write(
            "⚠️ **Atenção:** Esta seleção manual não verifica as regras de alocação automaticamente."
        )

        # Get all rooms for selection
        all_rooms = sala_repo.get_all()
        room_options = {}

        for room in all_rooms:
            predio_name = _get_predio_name_from_id(room.predio_id, session)
            room_options[room.id] = f"{predio_name}: {room.nome}"

        selected_room_id = st.selectbox(
            "Escolher sala:",
            options=[None] + list(room_options.keys()),
            format_func=lambda x: room_options.get(x, "Selecionar sala..."),
            key=f"manual_room_select_partial_{demanda_id}",
        )

        if selected_room_id:
            selected_room = next(
                (r for r in all_rooms if r.id == selected_room_id), None
            )
            if selected_room:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Capacidade", selected_room.capacidade or 0)
                with col2:
                    tipo_sala_name = _get_tipo_sala_name_from_id(
                        selected_room.tipo_sala_id, session
                    )
                    st.metric("Tipo", tipo_sala_name)
                with col3:
                    st.metric("Andar", selected_room.andar or "N/A")

                # Allocation button
                if st.button(
                    "🔧 Alocar Manualmente",
                    type="primary",
                    key=f"manual_allocate_partial_{demanda_id}",
                ):
                    result = alloc_service.allocate_demand_partial(
                        demanda_id,
                        selected_room_id,
                        day_ids=selected_day_ids,
                    )

                    # Clear selection state
                    session_key = f"selected_block_groups_{demanda_id}"
                    if session_key in st.session_state:
                        del st.session_state[session_key]

                    predio_name = _get_predio_name_from_id(
                        selected_room.predio_id, session
                    )

                    if result.success:
                        feedback_message = (
                            f"✅ Alocação manual realizada! {len(result.allocated_blocks)} blocos em '{predio_name}: {selected_room.nome}'"
                        )
                        if result.remaining_blocks:
                            feedback_message += f". Restam {len(result.remaining_blocks)} blocos pendentes."
                    else:
                        feedback_message = f"❌ Falha: {result.message}"

                    return {
                        "action_taken": True,
                        "allocation_success": result.success,
                        "feedback_message": feedback_message,
                    }

    return None


# ================================================================
# LEGACY FUNCTIONS (kept for backward compatibility)
# ================================================================

def _render_suggestions_section(
    title: str,
    room_suggestions,
    demanda_id: int,
    alloc_service: ManualAllocationService,
    semester_id: int,
) -> bool:
    """Render a section of room suggestions. (Legacy - kept for compatibility)"""
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
    """Render a single room suggestion card with allocation button. (Legacy)"""
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
                        "📊 Detalhes da Pontuação", expanded=False
                    ):
                        breakdown = suggestion.scoring_breakdown

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
                                rules_details = " • ".join(hard_rules)
                                st.success(
                                    f"✅ Atendidas (+{breakdown.get('hard_rules_points', 0)}) • {rules_details}"
                                )
                            else:
                                st.error(
                                    f"❌ Não atendidas (+{breakdown.get('hard_rules_points', 0)})"
                                )

                        with col2:
                            st.markdown("**Preferências Professor:**")
                            soft_prefs = breakdown.get("soft_preferences_satisfied", [])
                            if soft_prefs:
                                prefs_details = " • ".join(soft_prefs)
                                st.success(
                                    f"✅ Atendidas (+{breakdown.get('soft_preference_points', 0)}) • {prefs_details}"
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

                        st.markdown("---")
                        st.markdown(
                            f"**Total: {suggestion.compatibility_score} pontos**"
                        )
                else:
                    st.caption(suggestion.motivation_reason)

            # Show rule violations
            if suggestion.rule_violations:
                valid_violations = []
                for v in suggestion.rule_violations:
                    if not v or not v.strip():
                        continue
                    v_stripped = v.strip()
                    if v_stripped in ["🔒 Obrigatório:", "⚠️", "❌"]:
                        continue
                    if v_stripped.endswith(":") and len(v_stripped) < 20:
                        continue
                    valid_violations.append(v_stripped)

                if valid_violations:
                    st.warning("⚠️ Violações: " + "; ".join(valid_violations))

        with col2:
            button_key = f"alloc_{suggestion.sala_id}"
            button_label = (
                "✅ Alocar Aqui" if not suggestion.has_conflicts else "❌ Conflito"
            )

            if suggestion.has_conflicts:
                st.button(
                    button_label,
                    disabled=True,
                    key=button_key,
                    width="stretch",
                )

                if suggestion.conflict_details:
                    for conflict in suggestion.conflict_details[:3]:
                        st.caption(f"🔴 {conflict}")
            else:
                if st.button(
                    button_label,
                    key=button_key,
                    width="stretch",
                    type="primary",
                    help="Alocar demanda nesta sala",
                ):
                    result = alloc_service.allocate_demand(
                        demanda_id, suggestion.sala_id
                    )

                    if "allocation_selected_demand" in st.session_state:
                        del st.session_state.allocation_selected_demand

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
    """Render section showing rooms with conflicts. (Legacy)"""
    if not conflicting_rooms:
        st.write("Nenhum conflito encontrado.")
        return

    for room in conflicting_rooms[:5]:
        with st.container(border=True):
            st.markdown(f"**{room.nome_sala}** (Cap: {room.capacidade})")
            st.caption(f"Motivo: {room.motivation_reason}")

            if room.conflict_details:
                for conflict in room.conflict_details[:3]:
                    st.caption(f":red[• {conflict}]")


def _render_manual_selection(
    demanda, sala_repo: SalaRepository, alloc_service: ManualAllocationService, session
):
    """Render manual room selection option. (Legacy)"""
    st.subheader("🎯 Seleção Manual de Sala")

    with st.expander("Selecionar Sala Manualmente", expanded=False):
        st.write(
            "⚠️ **Atenção:** Esta seleção manual não verifica as regras de alocação automaticamente."
        )

        all_rooms = sala_repo.get_all()
        room_options = {}

        for room in all_rooms:
            predio_name = _get_predio_name_from_id(room.predio_id, session)
            room_options[room.id] = f"{predio_name}: {room.nome}"

        selected_room_id = st.selectbox(
            "Escolher sala:",
            options=[None] + list(room_options.keys()),
            format_func=lambda x: room_options.get(x, "Selecionar sala..."),
            key="manual_room_select",
        )

        if selected_room_id:
            selected_room = next(
                (r for r in all_rooms if r.id == selected_room_id), None
            )
            if selected_room:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Capacidade", selected_room.capacidade or 0)
                with col2:
                    tipo_sala_name = _get_tipo_sala_name_from_id(
                        selected_room.tipo_sala_id, session
                    )
                    st.metric("Tipo", tipo_sala_name)
                with col3:
                    st.metric("Andar", selected_room.andar or "N/A")

                if st.button(
                    "🔧 Alocar Manualmente", type="primary", key="manual_allocate_btn"
                ):
                    if st.checkbox("⚠️ Confirmar alocação manual - pode violar regras"):
                        result = alloc_service.allocate_demand(
                            demanda.id, selected_room_id
                        )

                        if "allocation_selected_demand" in st.session_state:
                            del st.session_state.allocation_selected_demand

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
