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
    page_title="Alocação Manual - Sistema de Ensalamento",
    page_icon="🖱️",
    layout="wide",
    key_suffix="alloc_manual",
):
    st.stop()

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("🖱️ Alocação Manual de Salas")

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

st.subheader("🎯 Seleção de Semestre")

# Get available semesters using cached helper
semester_options_list = get_semester_options()

if not semester_options_list:
    st.error("❌ Nenhum semestre encontrado. Importe dados primeiro.")
    st.stop()

# Create options dict for selectbox
semester_options = {sem_id: sem_name for sem_id, sem_name in semester_options_list}
selected_semester = st.selectbox(
    "📅 Semestre:",
    options=list(semester_options.keys()),
    format_func=lambda x: semester_options.get(x, f"ID {x}"),
    index=0,  # Select first (most recent) by default
    key="semester_select_manual_alloc",
)

# ============================================================================
# MAIN LAYOUT - TWO COLUMN ALLOCATION INTERFACE
# ============================================================================

# Check if a demand is selected for allocation
selected_demand_id = st.session_state.get("allocation_selected_demand", None)

if selected_demand_id:
    # Two-column layout with allocation assistant visible
    col_queue, col_assistant = st.columns([1, 1])

    with col_queue:
        # Show compact demand queue (filters applied)
        with st.expander("📋 Fila de Demandas (Selecionada)", expanded=True):
            filters = {
                "semester_id": selected_semester,
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

else:
    # Single column layout showing full demand queue
    action_taken = render_demand_queue(selected_semester)
    if action_taken:
        st.rerun()  # Refresh page after selecting a demand

# ============================================================================
# ADDITIONAL CONTROLS AND INFO
# ============================================================================

st.markdown("---")

with st.expander("ℹ️ Sobre a Alocação Manual", expanded=False):
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
    - Alocações podem ser removidas na página de Ensalamento
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
        st.rerun()

# Page Footer
page_footer.show()
