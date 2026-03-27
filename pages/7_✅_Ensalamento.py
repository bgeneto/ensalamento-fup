"""Room Allocation Page - Ensalamento FUP/UnB

Two-column layout page for allocating classroom demands to rooms.
Combines demand queue with smart room suggestions and allocation controls.
"""

import streamlit as st

from pages.components.alloc_queue import render_demand_queue
from pages.components.allocation_assistant import render_allocation_assistant
from pages.components.auth import initialize_page
from pages.components.ui import page_footer
from src.config.database import get_db_session
from src.utils.cache_helpers import get_semester_options
from src.utils.demand_filter_options import build_demand_filter_options
from src.utils.ui_feedback import display_session_feedback


def clear_deallocation_selection():
    """Clear the deallocation selection from session state."""
    st.session_state.pop("deallocation_selected_demand", None)
    st.rerun()


def clear_semester_deallocation_request():
    """Clear the semester deallocation dialog state."""
    st.session_state.pop("deallocation_selected_semester", None)
    st.session_state.pop("preserve_manual_allocations_on_semester_reset", None)
    st.rerun()


def clear_ensalamento_filters():
    """Reset local page filters to their default values."""
    st.session_state["demandas_filter"] = "all"
    st.session_state["ensalamento_disciplina_filter"] = "all"
    st.session_state["ensalamento_professor_filter"] = "all"


@st.dialog(
    "❓Remover Alocação",
    width="large",
    on_dismiss=clear_deallocation_selection,
)
def show_deallocation_dialog(selected_dealloc_demand_id):
    """
    Show a modal dialog for deallocation confirmation.
    """
    with get_db_session() as session:
        from src.repositories.alocacao import AlocacaoRepository
        from src.repositories.disciplina import DisciplinaRepository
        from src.repositories.sala import SalaRepository
        from src.services.manual_allocation_service import ManualAllocationService

        demanda_repo = DisciplinaRepository(session)
        alocacao_repo = AlocacaoRepository(session)
        sala_repo = SalaRepository(session)
        alloc_service = ManualAllocationService(session)

        demanda = demanda_repo.get_by_id(selected_dealloc_demand_id)
        if not demanda:
            st.error("Demanda não encontrada.")
            if st.button("Fechar", key="close_missing_demand"):
                st.rerun()
            return

        st.markdown("### ⚠️ **Confirmação de Desalocação**")

        st.markdown(
            f"**Disciplina:** {demanda.codigo_disciplina} - {demanda.nome_disciplina}"
        )
        st.markdown(f"**Turma:** {demanda.turma_disciplina}")

        # Get current allocation info
        allocations = alocacao_repo.get_by_demanda(selected_dealloc_demand_id)
        if not allocations:
            st.error("Esta demanda já não possui alocações.")
            if st.button("Fechar", key="close_no_allocations"):
                st.rerun()
            return

        # Get ALL unique rooms from allocations
        unique_room_ids = list(dict.fromkeys(a.sala_id for a in allocations))
        room_names = []
        for room_id in unique_room_ids:
            room_info = sala_repo.get_by_id(room_id)
            room_name = room_info.nome if room_info else f"Sala {room_id}"
            room_names.append(room_name)

        # Display room(s) info
        if len(room_names) > 1:
            st.markdown(f"**Salas atuais:** {', '.join(room_names)} 🔀")
        else:
            st.markdown(f"**Sala atual:** {room_names[0]}")
        st.markdown(f"**Número de alocações:** {len(allocations)}")

        st.warning("ℹ️ Esta ação irá remover a alocação da disciplina permanentemente.")

        col_cancel, col_confirm = st.columns(2)
        with col_cancel:
            if st.button("❌ Cancelar", width="stretch", key="cancel_dealloc_dialog"):
                # Clear the session state to close the dialog
                st.session_state.pop("deallocation_selected_demand", None)
                st.rerun()

        with col_confirm:
            if st.button(
                "✅ Confirmar Desalocação",
                type="primary",
                width="stretch",
                key="confirm_dealloc_dialog",
            ):
                # Execute deallocation first
                result = alloc_service.deallocate_demand(selected_dealloc_demand_id)

                # Set feedback based on deallocation result
                success = result.success
                message = result.error_message or "Desalocação realizada com sucesso"

                from src.utils.ui_feedback import set_session_feedback

                set_session_feedback("deallocation_result", success, message, ttl=6)

                # Clear the session state to dismiss the dialog BEFORE rerun
                st.session_state.pop("deallocation_selected_demand", None)

                # Force page refresh to show feedback and close dialog
                st.rerun()


@st.dialog(
    "↩️ Desfazer Ensalamento do Semestre",
    width="large",
    on_dismiss=clear_semester_deallocation_request,
)
def show_semester_deallocation_dialog(selected_semester_id):
    """Show a modal dialog for clearing all allocations in a semester."""
    with get_db_session() as session:
        from src.repositories.alocacao import AlocacaoRepository
        from src.services.manual_allocation_service import ManualAllocationService
        from src.utils.ui_feedback import set_session_feedback

        alloc_service = ManualAllocationService(session)
        alocacao_repo = AlocacaoRepository(session)

        allocations = alocacao_repo.get_by_semestre(selected_semester_id)
        if not allocations:
            st.info("Este semestre não possui alocações para desfazer.")
            if st.button("Fechar", key="close_empty_semester_deallocation"):
                clear_semester_deallocation_request()
            return

        manual_allocations = [
            alloc for alloc in allocations if alloc.origem_alocacao == "manual"
        ]
        autonomous_allocations = [
            alloc for alloc in allocations if alloc.origem_alocacao != "manual"
        ]
        preserve_manual_allocations = st.checkbox(
            "Manter alocações manuais existentes",
            value=True,
            key="preserve_manual_allocations_on_semester_reset",
            help="Quando marcado, remove apenas alocações com origem autônoma.",
        )
        allocations_to_remove = (
            autonomous_allocations if preserve_manual_allocations else allocations
        )
        affected_demands_count = len(
            {alloc.demanda_id for alloc in allocations_to_remove}
        )

        st.markdown("### ⚠️ **Confirmar Desfazer Ensalamento**")
        st.markdown(
            f"**Semestre:** {semester_options.get(selected_semester_id, f'ID {selected_semester_id}')}"
        )
        st.markdown(f"**Total de alocações no semestre:** {len(allocations)}")
        st.markdown(f"**Alocações autônomas:** {len(autonomous_allocations)}")
        st.markdown(f"**Alocações manuais:** {len(manual_allocations)}")
        st.markdown(f"**Alocações que serão removidas:** {len(allocations_to_remove)}")
        st.markdown(f"**Demandas afetadas:** {affected_demands_count}")
        st.warning(
            "ℹ️ Esta ação removerá apenas as alocações do semestre atual. As demandas importadas serão preservadas."
        )
        if preserve_manual_allocations:
            st.info(
                f"{len(manual_allocations)} alocação(ões) manual(is) serão mantidas."
            )

        col_cancel, col_confirm = st.columns(2)
        with col_cancel:
            if st.button(
                "❌ Cancelar",
                width="stretch",
                key="cancel_semester_deallocation_dialog",
            ):
                clear_semester_deallocation_request()

        with col_confirm:
            if st.button(
                "✅ Desfazer Ensalamento Vigente",
                type="primary",
                width="stretch",
                key="confirm_semester_deallocation_dialog",
            ):
                result = alloc_service.deallocate_semester(
                    selected_semester_id,
                    preserve_manual_allocations=preserve_manual_allocations,
                )

                success = result.success
                message = result.error_message
                if success:
                    if result.deleted_allocations_count == 0 and (
                        result.preserved_manual_allocations_count > 0
                    ):
                        message = (
                            "Nenhuma alocação autônoma foi removida. "
                            f"{result.preserved_manual_allocations_count} alocação(ões) manual(is) "
                            "foram preservadas."
                        )
                    else:
                        message = (
                            "Ensalamento desfeito com sucesso: "
                            f"{result.deleted_allocations_count} alocação(ões) removida(s) "
                            f"de {result.affected_demands_count} demanda(s)."
                        )
                        if result.preserved_manual_allocations_count > 0:
                            message += (
                                f" {result.preserved_manual_allocations_count} alocação(ões) "
                                "manual(is) foram mantidas."
                            )

                set_session_feedback(
                    "semester_deallocation_result",
                    success,
                    message or "Erro ao desfazer ensalamento",
                    ttl=8 if success else 10,
                )

                st.session_state.pop("deallocation_selected_semester", None)
                st.session_state.pop("allocation_selected_demand", None)
                st.session_state.pop("deallocation_selected_demand", None)
                st.session_state.pop("autonomous_allocation_pdf", None)
                st.session_state.pop("autonomous_allocation_pdf_filename", None)
                st.rerun()


# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Alocação - Ensalamento",
    page_icon="✅",
    layout="wide",
    key_suffix="ensalamento",
):
    st.stop()

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("✅ Ensalamento")

st.info(
    """
    ℹ️ INSTRUÇÕES

    - Antes de realizar o ensalamento, verifique se a **🧭 Demanda** já foi importada (menu lateral).
    - Selecione o semestre (menu lateral) para o qual deseja realizar o ensalamento.
    - Use **🚀 Executar Alocação Autônoma** para rodar o motor de alocação automática inteligente baseado em regras e histórico.
    - A lista de demandas pendentes será exibida. Se a lista estiver vazia (nenhuma demanda encontrada), verifique se os dados foram previamente importados na página **🧭 Demanda**.
    - Clique em **🎯 Alocar Sala** em qualquer demanda para alocar manualmente uma sala à demanda. O assistente de alocação abrirá automaticamente à direita.
    - Escolha uma sala sugerida por pontuação ou use a seleção manual (no final da página) para alocar a demanda selecionada.
    """,
)

# Display any persisted feedback from allocation actions
display_session_feedback("allocation_result")
display_session_feedback("autonomous_allocation_result")
display_session_feedback("deallocation_result")
display_session_feedback("semester_deallocation_result")

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

# Default selected semester is the current global semester
selected_semester = current_semester_id

with get_db_session() as session:
    from src.repositories.disciplina import DisciplinaRepository

    disciplina_repo = DisciplinaRepository(session)
    semester_demands = disciplina_repo.get_by_semestre(selected_semester)
    discipline_options, professor_options = build_demand_filter_options(
        semester_demands
    )

if st.session_state.get("ensalamento_disciplina_filter") not in discipline_options:
    st.session_state["ensalamento_disciplina_filter"] = "all"
if st.session_state.get("ensalamento_professor_filter") not in professor_options:
    st.session_state["ensalamento_professor_filter"] = "all"

col1, col2 = st.columns(2)

with col1:
    # Display readonly semester selector with help text
    st.selectbox(
        "📅 Semestre (Global):",
        options=[current_semester_id],
        format_func=lambda x: semester_options.get(x, f"ID {x}"),
        disabled=True,
        help="Para alterar o semestre, use o menu lateral.",
        key="readonly_semester_display_ensalamento",
    )

    selected_professor = st.selectbox(
        "Filtrar por Professor:",
        options=list(professor_options.keys()),
        format_func=lambda x: professor_options.get(x, f"Professor {x}"),
        key="ensalamento_professor_filter",
        help="Exibe rapidamente as demandas associadas a um professor específico.",
    )

    run_autonomous_allocation = st.button(
        "🚀 **Executar Alocação Autônoma**",
        type="primary",
        width="stretch",
        help="Executa o motor de alocação automática inteligente baseado em regras obrigatórias, preferências e histórico de alocações",
    )


with col2:
    selected_demandas = st.selectbox(
        "Filtrar Demandas:",
        options=list(demandas_options.keys()),
        format_func=lambda x: demandas_options.get(x, f"ID {x}"),
        index=0,  # Default to "all"
        key="demandas_filter",
    )

    selected_disciplina = st.selectbox(
        "Filtrar por Disciplina:",
        options=list(discipline_options.keys()),
        format_func=lambda x: discipline_options.get(x, f"Código {x}"),
        key="ensalamento_disciplina_filter",
        help="Exibe rapidamente as alocações ou pendências de uma disciplina específica.",
    )

    st.button(
        "🧹 Limpar Filtros",
        width="stretch",
        help="Restaura os filtros de demandas, disciplina e professor.",
        on_click=clear_ensalamento_filters,
    )

    # Show download button if PDF report is available from previous allocation
    if st.session_state.get("autonomous_allocation_pdf"):
        pdf_data = st.session_state["autonomous_allocation_pdf"]
        pdf_filename = st.session_state.get(
            "autonomous_allocation_pdf_filename", "relatorio_alocacao.pdf"
        )

        st.download_button(
            label="📄 Relatório PDF da Alocação",
            data=pdf_data,
            file_name=pdf_filename,
            mime="application/pdf",
            help="Baixe o relatório detalhado em PDF com todas as decisões de alocação",
            type="primary",
        )

    if st.button(
        "↩️ Desfazer Ensalamento do Semestre",
        width="stretch",
        help="Remove todas as alocações do semestre ativo sem excluir as demandas.",
    ):
        st.session_state["deallocation_selected_semester"] = selected_semester
        st.rerun()

if run_autonomous_allocation:
    # Execute autonomous allocation
    with st.spinner(
        "🧠 Executando alocação autônoma. Isso pode levar alguns minutos..."
    ):
        with get_db_session() as session:
            from src.services.optimized_autonomous_allocation_service import (
                OptimizedAutonomousAllocationService as AutonomousAllocationService,
            )

            autonomous_service = AutonomousAllocationService(session)
            # Use partial allocation to enable per-day scoring and split room
            # allocation for hybrid disciplines (e.g., lab on Mon, classroom on Wed)
            result = autonomous_service.execute_autonomous_allocation_partial(
                selected_semester
            )

            if result["success"]:
                # Use only toast-style feedback system (no st.success/st.info/st.metric)

                from src.utils.ui_feedback import set_session_feedback

                # Check if this is the "no demands" case or full results
                if "message" in result:
                    # No unallocated demands to process
                    set_session_feedback(
                        "autonomous_allocation_result",
                        True,
                        f"Alocação autônoma: {result['message']}",
                        ttl=8,
                    )
                else:
                    # Store PDF report in session state for download
                    if "pdf_report" in result:
                        st.session_state["autonomous_allocation_pdf"] = result[
                            "pdf_report"
                        ]
                        st.session_state["autonomous_allocation_pdf_filename"] = (
                            result.get("pdf_filename", "relatorio_alocacao.pdf")
                        )

                        # Save PDF report to data/reports folder automatically
                        import os

                        pdf_filename = result.get(
                            "pdf_filename", "relatorio_alocacao.pdf"
                        )
                        reports_dir = "data/reports"
                        os.makedirs(reports_dir, exist_ok=True)
                        pdf_path = os.path.join(reports_dir, pdf_filename)

                        with open(pdf_path, "wb") as f:
                            f.write(result["pdf_report"])

                        # Log successful save
                        print(f"PDF report saved to: {pdf_path}")

                    # Full allocation results (partial mode)
                    allocations_done = result["allocations_completed"]
                    split_demands = result.get("demands_with_split_rooms", 0)
                    total_conflicts = result["phase1_hard_rules"][
                        "conflicts"
                    ] + result.get("conflicts_found", 0)
                    execution_time = result.get("execution_time", 0)

                    # Build feedback message including split allocation info
                    msg = f"Alocação autônoma concluída: {allocations_done} alocações em {execution_time:.2f}s"
                    if split_demands > 0:
                        msg += f" ({split_demands} disciplinas híbridas com salas divididas)"

                    set_session_feedback(
                        "autonomous_allocation_result",
                        True,
                        msg,
                        ttl=10,
                    )

                st.rerun()
            else:
                st.error(
                    f"❌ **Erro na alocação autônoma**: {result.get('error', 'Erro desconhecido')}"
                )


# ============================================================================
# MAIN LAYOUT - TWO COLUMN ALLOCATION INTERFACE
# ============================================================================

# Check if a demand is selected for allocation or deallocation
selected_demand_id = st.session_state.get("allocation_selected_demand", None)
selected_dealloc_demand_id = st.session_state.get("deallocation_selected_demand", None)
selected_dealloc_semester_id = st.session_state.get("deallocation_selected_semester")

if selected_dealloc_semester_id:
    show_semester_deallocation_dialog(selected_dealloc_semester_id)
    with st.expander("📋 Fila de Demandas", expanded=True):
        filters = {
            "allocation_status": selected_demandas,
            "discipline_filter": selected_disciplina,
            "professor_filter": selected_professor,
            "context_id": "semester_deallocation_dialog",
        }
        action_taken = render_demand_queue(selected_semester, filters)

elif selected_demand_id:
    # Two-column layout with allocation assistant visible
    col_queue, col_assistant = st.columns([1, 1])

    with col_queue:
        # Show compact demand queue (filters applied)
        with st.expander("📋 Fila de Demandas (Selecionada)", expanded=True):
            filters = {
                "semester_id": selected_semester,
                "allocation_status": selected_demandas,
                "discipline_filter": selected_disciplina,
                "professor_filter": selected_professor,
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
    # Show the deallocation confirmation dialog
    show_deallocation_dialog(selected_dealloc_demand_id)

    # Show the demand queue below the dialog
    with st.expander("📋 Fila de Demandas", expanded=True):
        filters = {
            "allocation_status": selected_demandas,
            "discipline_filter": selected_disciplina,
            "professor_filter": selected_professor,
            "context_id": "deallocation_dialog",
        }
        action_taken = render_demand_queue(selected_semester, filters)

else:
    # Single column layout showing full demand queue (only when neither allocation nor deallocation is active)
    filters = {
        "allocation_status": selected_demandas,
        "discipline_filter": selected_disciplina,
        "professor_filter": selected_professor,
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

    1. **Fila de Demandas**: Visualize todas as demandas/disciplinas não-alocadas para o semestre ativo
    2. **Seleção**: Clique em **🎯 Alocar Sala** para escolher uma sala para a disciplina desejada
    3. **Sugestões Automáticas**: O sistema calcula pontuações baseadas nos critérios abaixo e sugere as melhores salas:
       - ✅ **Regras obrigatórias:** Salas especificadas, tipos de sala, restrições de acessibilidade
       - 🤔 **Preferências:** Salas preferidas do professor, características preferidas
       - 📊 **Frequência:** Quantidade de vezes que a disciplina já foi alocada em determinada sala.
       - 👥 **Capacidade:** Adequação da capacidade da sala ao tamanho da turma (vagas)
       - 📅 **Disponibilidade:** Evita conflitos de horário

    4. **Alocação**: Clique em "🎯 Alocar Sala" nas sugestões ou use seleção manual

    ### Algoritmo de Pontuação
    - **+4 pontos**: Cada regra obrigatória atendida
    - **+2 pontos**: Preferências do professor atendidas
    - **+1 ponto**: Capacidade adequada para a turma
    - **+1 ponto**: Por cada alocação histórica bem-sucedida na sala

    ### Conflitos Detectados
    - Salas são marcadas como indisponíveis se já têm alocações nos mesmos horários
    - Prioriza evitar qualquer sobreposição de horário
    """
    )

# ============================================================================
# QUICK STATS SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("---")
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
    1. Importe a **🧭 Demanda** de disciplinas primeiramente;
    2. Execute a **🚀 Alocação Autônoma**;
    3. Verifique se restou demandas pendentes;
    4. Use o botão **🎯 Alocar Sala** para alocar manualmente as demandas pendentes
    5. Revise e imprima o ensalamento completo na página de **👁️ Visualização**
    """
    )

# ============================================================================
# UTILITY CONTROLS
# ============================================================================

# Add refresh button in case data gets stale
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    if st.button(
        "🔄 Atualizar Dados", help="Recarregar dados do banco", width="stretch"
    ):
        if "allocation_selected_demand" in st.session_state:
            del st.session_state.allocation_selected_demand
        if "deallocation_selected_demand" in st.session_state:
            del st.session_state.deallocation_selected_demand
        st.rerun()

# Page Footer
page_footer.show()
