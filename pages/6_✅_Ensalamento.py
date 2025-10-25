"""Manual Allocation Page - Ensalamento FUP/UnB

Two-column layout page for manually allocating classroom demands to rooms.
Combines demand queue with smart room suggestions and allocation controls.
"""

import streamlit as st
from typing import Dict, Any

from pages.components.auth import initialize_page
from pages.components.alloc_queue import render_demand_queue
from pages.components.allocation_assistant import render_allocation_assistant
from src.config.database import get_db_session
from src.utils.ui_feedback import display_session_feedback
from src.utils.cache_helpers import get_semester_options
from pages.components.ui import page_footer

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Alocação - Ensalamento",
    page_icon="✅",
    layout="wide",
    key_suffix="alloc_manual",
):
    st.stop()

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("✅ Ensalamento")

st.info(
    """
    ℹ️ INSTRUÇÕES

    - Selecione o semestre desejado no menu abaixo.
    - A lista de demandas pendentes será exibida. Se a lista estiver vazia (nenhuma demanda encontrada), verifique se os dados foram importados do Sistema de Oferta corretamente na página "👁️ Demanda" no menu ao lado.
    - Clique em "🎯 Alocar Sala" em qualquer demanda para abrir o assistente de alocação à direita.
    - Escolha uma sala sugerida ou use a seleção manual para alocar a demanda.
    """,
)

# Display any persisted feedback from allocation actions
display_session_feedback("allocation_result")

# ============================================================================
# FILTERS SECTION
# ============================================================================

# Validate current global semester exists - semester_badge component handles initialization
semester_options_list = get_semester_options()
if not semester_options_list:
    st.error("❌ Nenhum semestre encontrado. Importe dados primeiro.")
    st.stop()

semester_options = {sem_id: sem_name for sem_id, sem_name in semester_options_list}
current_semester_id = st.session_state.get("global_semester_id")

# Fallback to most recent if current semester is invalid (shouldn't happen due to badge initialization)
if current_semester_id not in semester_options:
    current_semester_id = semester_options_list[0][0]
    st.session_state.global_semester_id = current_semester_id

demandas_options = {
    "all": "Todas as demandas",
    "allocated": "Demandas alocadas",
    "unallocated": "Demandas pendentes",
}

col1, col2 = st.columns(2)

with col1:
    # Display readonly semester selector with help text
    st.selectbox(
        "📅 Semestre (Global):",
        options=[current_semester_id],
        format_func=lambda x: semester_options.get(x, f"ID {x}"),
        disabled=True,
        help="Para alterar o semestre, acesse a página Painel",
        key="readonly_semester_display_ensalamento",
    )

selected_semester = current_semester_id


with col2:
    selected_demandas = st.selectbox(
        "Demandas:",
        options=list(demandas_options.keys()),
        format_func=lambda x: demandas_options.get(x, f"ID {x}"),
        index=0,  # Default to "all"
        key="demandas_filter",
    )


# ============================================================================
# MAIN LAYOUT - TWO COLUMN ALLOCATION INTERFACE
# ============================================================================

# Check if a demand is selected for allocation or deallocation
selected_demand_id = st.session_state.get("allocation_selected_demand", None)
selected_dealloc_demand_id = st.session_state.get("deallocation_selected_demand", None)

# Auto-scroll to top when switching to assistant/confirmation mode
if selected_demand_id or selected_dealloc_demand_id:
    import streamlit.components.v1 as components

    # Execute JavaScript to scroll to top when assistant/confirmation loads
    components.html(
        """
        <script>
            // Wait for page to load, then scroll to top
            window.addEventListener('load', function() {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });

            // Also try immediately in case load event already fired
            setTimeout(function() {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }, 300);
        </script>
        """,
        height=0,
    )

if selected_demand_id:
    # Two-column layout with allocation assistant visible
    col_queue, col_assistant = st.columns([1, 1])

    with col_queue:
        # Show compact demand queue (filters applied)
        with st.expander("📋 Fila de Demandas (Selecionada)", expanded=True):
            filters = {
                "semester_id": selected_semester,
                "allocation_status": selected_demandas,
                "context_id": "allocation_selected",
                # Could add more filters here if needed
            }
            action_taken = render_demand_queue(selected_semester, filters)

    with col_assistant:
        # Show allocation assistant for selected demand
        result = render_allocation_assistant(selected_demand_id, selected_semester)

        # Handle allocation results and feedback
        if result and isinstance(result, dict):
            if result.get("action_taken"):
                # Set feedback based on allocation result
                if "allocation_success" in result:
                    success = result["allocation_success"]
                    message = result["feedback_message"]
                    ttl = 6 if success else 8

                    from src.utils.ui_feedback import set_session_feedback

                    set_session_feedback(
                        "allocation_result",
                        success,
                        message,
                        ttl=ttl,
                    )

                # Refresh page after any action
                st.rerun()

elif selected_dealloc_demand_id:
    # Two-column layout with deallocation confirmation visible
    col_queue, col_confirm = st.columns([1, 1])

    with col_queue:
        # Show compact demand queue
        with st.expander("📋 Fila de Demandas", expanded=True):
            filters = {
                "allocation_status": selected_demandas,
                "context_id": "deallocation_confirmation",
            }
            action_taken = render_demand_queue(selected_semester, filters)

    with col_confirm:
        # Show deallocation confirmation
        st.markdown("### ⚠️ **Confirmação de Desalocação**")

        # Get demand details for confirmation
        with get_db_session() as session:
            from src.repositories.disciplina import DisciplinaRepository
            from src.repositories.alocacao import AlocacaoRepository
            from src.repositories.sala import SalaRepository
            from src.services.manual_allocation_service import ManualAllocationService

            demanda_repo = DisciplinaRepository(session)
            alocacao_repo = AlocacaoRepository(session)
            sala_repo = SalaRepository(session)
            alloc_service = ManualAllocationService(session)

            demanda = demanda_repo.get_by_id(selected_dealloc_demand_id)
            if demanda:
                st.markdown(
                    f"**Disciplina:** {demanda.codigo_disciplina} - {demanda.nome_disciplina}"
                )
                st.markdown(f"**Turma:** {demanda.turma_disciplina}")

                # Get current allocation info
                allocations = alocacao_repo.get_by_demanda(selected_dealloc_demand_id)
                if allocations:
                    room_id = allocations[0].sala_id
                    room_info = sala_repo.get_by_id(room_id)
                    room_name = room_info.nome if room_info else f"Sala {room_id}"
                    st.markdown(f"**Sala atual:** {room_name}")
                    st.markdown(f"**Número de alocações:** {len(allocations)}")

                    st.warning(
                        "ℹ️ Esta ação irá remover a alocação da disciplina permanentemente."
                    )

                    col_cancel, col_confirm = st.columns(2)
                    with col_cancel:
                        if st.button("❌ Cancelar", key="cancel_dealloc"):
                            del st.session_state["deallocation_selected_demand"]
                            st.rerun()

                    with col_confirm:
                        if st.button("✅ Confirmar Desalocação", key="confirm_dealloc"):
                            # Execute deallocation
                            result = alloc_service.deallocate_demand(
                                selected_dealloc_demand_id
                            )

                            # Set feedback based on deallocation result
                            success = result.success
                            message = result.error_message or "Erro desconhecido"

                            from src.utils.ui_feedback import set_session_feedback

                            set_session_feedback(
                                "deallocation_result", success, message, ttl=6
                            )

                            # Don't clear session state yet - do it after feedback is shown
                            st.rerun()
                else:
                    st.error("Esta demanda já não possui alocações.")
                    if st.button("Voltar"):
                        del st.session_state["deallocation_selected_demand"]
                        st.rerun()
            else:
                st.error("Demanda não encontrada.")
                if st.button("Voltar"):
                    del st.session_state["deallocation_selected_demand"]
                    st.rerun()

# Display and clear deallocation feedback after rerun
if "deallocation_result" in st.session_state:
    feedback_result = display_session_feedback("deallocation_result")
    if feedback_result:
        # Clear the deallocation session state once feedback is displayed
        st.session_state.pop("deallocation_selected_demand", None)
        # Keep feedback in session state until it expires naturally via TTL
elif not selected_demand_id and not selected_dealloc_demand_id:
    # Single column layout showing full demand queue (only when neither allocation nor deallocation is active)
    filters = {
        "allocation_status": selected_demandas,
        "context_id": "main_queue",
    }
    action_taken = render_demand_queue(selected_semester, filters)
    if action_taken:
        st.rerun()  # Refresh page after selecting a demand

# ============================================================================
# ADDITIONAL CONTROLS AND INFO
# ============================================================================

st.markdown("---")

with st.expander("ℹ️ Sobre a Alocação", expanded=False):
    st.markdown(
        """
    ### Como Funciona

    1. **Fila de Demandas**: Visualize todas as disciplinas não-alocadas para o semestre selecionado
    2. **Seleção**: Clique em "Alocar" para escolher uma demanda específica
    3. **Sugestões Automáticas**: O sistema calcula pontuações baseadas em:
       - ✅ **Regras obrigatórias** (tipo de sala, restrições de acessibilidade)
       - 🤔 **Preferências** (salas preferidas do professor, características)
       - 📅 **Disponibilidade** (evitando conflitos de horário)

    4. **Alocação**: Clique em "✅ Alocar Aqui" nas sugestões ou use seleção manual

    ### Algoritmo de Pontuação
    - **4 pontos**: Cada regra obrigatória atendida
    - **2 pontos**: Prefereências do professor atendidas
    - **1 ponto**: Capacidade adequada para a turma

    ### Conflitos Detectados
    - Salas são marcadas como indisponíveis se já têm alocações nos mesmos horários atômicos
    - Prioriza evitar qualquer sobreposição de horário
    """
    )

# ============================================================================
# QUICK STATS SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("### 📊 Estatísticas Rápidas")

    if selected_semester:
        with get_db_session() as session:
            from src.services.manual_allocation_service import ManualAllocationService

            alloc_service = ManualAllocationService(session)
            progress = alloc_service.get_allocation_progress(selected_semester)

            if progress:
                st.metric(
                    "Progresso Geral",
                    f"{progress['allocation_percent']:.1f}%",
                    help="Demandas alocadas vs total",
                )

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Alocadas", progress["allocated_demands"])
                with col2:
                    st.metric("Pendentes", progress["unallocated_demands"])

    st.markdown("---")

    # Quick help
    st.markdown(
        """
    ### 💡 Dicas
    - **Regras obrigatórias** têm prioridade máxima
    - Verifique horários com **conflitos** antes de alocar
    - Use seleção manual quando regras são flexíveis
    """
    )

# ============================================================================
# UTILITY CONTROLS
# ============================================================================

# Add refresh button in case data gets stale
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    if st.button(
        "🔄 Atualizar Dados", help="Recarregar dados do banco", use_container_width=True
    ):
        if "allocation_selected_demand" in st.session_state:
            del st.session_state.allocation_selected_demand
        if "deallocation_selected_demand" in st.session_state:
            del st.session_state.deallocation_selected_demand
        st.rerun()

# Page Footer
page_footer.show()
