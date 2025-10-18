"""
Semester management page for Sistema de Ensalamento FUP/UnB
Administrative interface for managing semesters and semester lifecycle
"""

import streamlit as st
from typing import Optional
from src.services.semester_service import SemesterService
from src.services.auth_service import is_current_user_admin
from models import SemestreStatusEnum


def render_semestres_page():
    """Render semester management page"""
    st.title("📅 Gestão de Semestres")
    st.caption("Gerencie semestres e ciclo de vida acadêmico")

    # Check if user is admin
    if not is_current_user_admin():
        st.error("❌ Acesso negado. Esta página requer privilégios de administrador.")
        return

    # Create tabs for different operations
    tab1, tab2, tab3 = st.tabs(
        ["📋 Lista de Semestres", "➕ Criar Semestre", "📈 Gestão do Semestre"]
    )

    with tab1:
        render_semestre_list()

    with tab2:
        render_create_semestre()

    with tab3:
        render_semestre_management()


def render_semestre_list():
    """Render list of all semesters"""
    st.header("📋 Lista de Semestres")

    semestres = SemesterService.get_all_semestres()

    if not semestres:
        st.info("Nenhum semestre encontrado no sistema.")
        return

    # Display semester statistics
    total_semestres = len(semestres)
    planning_semestres = len(
        [
            s
            for s in semestres
            if s.status
            in [SemestreStatusEnum.PLANEJAMENTO, SemestreStatusEnum.EXECUCAO]
        ]
    )
    execution_semestres = len(
        [s for s in semestres if s.status == SemestreStatusEnum.EXECUCAO]
    )
    completed_semestres = len(
        [s for s in semestres if s.status == SemestreStatusEnum.FINALIZADO]
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Semestres", total_semestres)
    with col2:
        st.metric("Em Planejamento", planning_semestres)
    with col3:
        st.metric("Em Execução", execution_semestres)
    with col4:
        st.metric("Finalizados", completed_semestres)

    st.markdown("---")

    # Display semesters with status indicators
    for semestre in semestres:
        status_icon = {
            SemestreStatusEnum.PLANEJAMENTO: "📋",
            SemestreStatusEnum.EXECUCAO: "🚀",
            SemestreStatusEnum.FINALIZADO: "✅",
        }.get(semestre.status, "📋")

        with st.expander(f"{status_icon} {semestre.nome} ({semestre.status})"):
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.write(f"**ID:** {semestre.id}")
                st.write(f"**Nome:** {semestre.nome}")
                st.write(f"**Status:** {semestre.status}")
                st.write(
                    f"**Data de Criação:** {semestre.data_criacao.strftime('%d/%m/%Y %H:%M') if semestre.data_criacao else 'Não definida'}"
                )

            with col2:
                demandas_count = len(
                    SemesterService.get_demandas_by_semestre(semestre.id)
                )
                st.write(f"**Demandas:** {demandas_count}")
                capacity_stats = SemesterService.get_capacity_requirements(semestre.id)
                st.write(
                    f"**Capacidade Total:** {capacity_stats.get('capacidade_total', 0)}"
                )
                conflicts = SemesterService.get_schedule_conflicts(semestre.id)
                st.write(f"**Conflitos:** {len(conflicts)}")

            with col3:
                if st.button(
                    f"Editar",
                    key=f"edit_semestre_{semestre.id}",
                    use_container_width=True,
                ):
                    st.session_state["editing_semestre"] = semestre.id
                    st.rerun()

                # Status change buttons based on current status
                if semestre.status == SemestreStatusEnum.PLANEJAMENTO:
                    if st.button(
                        "▶️ Iniciar Execução", type="primary", use_container_width=True
                    ):
                        if SemesterService.update_semestre_status(
                            semestre.id, SemestreStatusEnum.EXECUCAO
                        ):
                            st.success(
                                f"✅ Semestre {semestre.nome} iniciado para execução!"
                            )
                            st.rerun()
                elif semestre.status == SemestreStatusEnum.EXECUCAO:
                    if st.button(
                        "✅ Finalizar Semestre",
                        type="primary",
                        use_container_width=True,
                    ):
                        if SemesterService.update_semestre_status(
                            semestre.id, SemestreStatusEnum.FINALIZADO
                        ):
                            st.success(
                                f"✅ Semestre {semestre.nome} finalizado com sucesso!"
                            )
                            st.rerun()
                elif semestre.status == SemestreStatusEnum.FINALIZADO:
                    st.info("Este semestre está finalizado e não pode ser modificado.")

                if st.button(
                    f"Excluir",
                    key=f"delete_semestre_{semestre.id}",
                    type="secondary",
                    use_container_width=True,
                ):
                    if len(SemesterService.get_demandas_by_semestre(semestre.id)) > 0:
                        st.error(
                            "❌ Não é possível excluir um semestre com demandas associadas."
                        )
                    else:
                        if SemesterService.delete_semestre(semestre.id):
                            st.success(
                                f"Semestre {semestre.nome} excluído com sucesso!"
                            )
                            st.rerun()
                        else:
                            st.error("❌ Falha ao excluir semestre.")

    # Check if there's a semester being edited
    if "editing_semestre" in st.session_state:
        render_edit_semestre_form(st.session_state["editing_semestre"])


def render_create_semestre():
    """Render create semester form"""
    st.header("➕ Criar Novo Semestre")

    with st.form("create_semestre_form"):
        st.subheader("Informações do Semestre")

        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome do Semestre",
                placeholder="ex: 2025.1",
                help="Formato: YYYY.N (ex: 2025.1 para primeiro semestre)",
                max_length=10,
            )

            status = st.selectbox(
                "Status do Semestre",
                options=[
                    SemestreStatusEnum.PLANEJAMENTO,
                    SemestreStatusEnum.EXECUCAO,
                    SemestreStatusEnum.FINALIZADO,
                ],
                index=0,
                help="Selecione o status inicial do semestre",
            )

        with col2:
            descricao = st.text_area(
                "Descrição do Semestre",
                placeholder="Ex: Semestre letivo 2025.1 com foco em...",
                help="Descrição detalhada sobre o semestre (opcional)",
                max_length=500,
            )

        st.markdown("---")

        submitted = st.form_submit_button(
            "Criar Semestre", type="primary", use_container_width=True
        )

        if submitted:
            # Validate inputs
            if not nome:
                st.error("❌ Nome do semestre é obrigatório.")
                return

            if len(nome) < 5 or len(nome) > 10:
                st.error(
                    "❌ Nome do semestre deve ter entre 5 e 10 caracteres (formato YYYY.N)."
                )
                return

            # Validate semester name format
            import re

            pattern = r"^\d{4}\.\d{1}$"
            if not re.match(pattern, nome):
                st.error("❌ Formato inválido. Use o formato YYYY.N (ex: 2025.1)")
                return

            # Create semester
            new_semestre = SemesterService.create_semestre(nome, status)
            if new_semestre:
                st.success(f"✅ Semestre '{nome}' criado com sucesso!")
                st.rerun()
            else:
                st.error(f"❌ Falha ao criar semestre. Nome já pode estar em uso.")


def render_semestre_management():
    """Render semester management interface"""
    st.header("🏛️ Gestão do Semestre")

    semestres = SemesterService.get_all_semestres()
    if not semestres:
        st.warning("Nenhum semestre encontrado. Crie um semestre primeiro.")
        return

    # Select semester for management
    semester_options = {f"{sem.nome} ({semestre.status})": sem.id for sem in semestres}
    selected_semestre = st.selectbox(
        "Selecione o Semestre para Gerenciar:",
        options=list(semester_options.keys()),
        help="Selecione um semestre para gerenciamento",
    )
    semestre_id = semester_options[selected_semestre]
    semestre = SemesterService.get_semestre_by_id(semestre_id)

    if not semestre:
        st.error("Semestre não encontrado.")
        return

    st.subheader(f"🔧 Gerenciamento do Semestre: {semestre.nome}")

    # Display current semester details
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informações Atuais")
        st.write(f"**Status:** {semestre.status}")
        st.write(f"**Nome:** {semestre.nome}")
        st.write(f"**ID:** {semestre.id}")
        st.write(
            f"**Data de Criação:** {semestre.data_criacao.strftime('%d/%m/%Y %H:%M') if semestre.data_criacao else 'Não definida'}"
        )

        # Get related statistics
        demandas = SemesterService.get_demandas_by_semestre(semestre_id)
        conflicts = SemesterService.get_schedule_conflicts(semestre_id)
        capacity_stats = SemesterService.get_capacity_requirements(semestre_id)

        st.write(f"**Demandas:** {len(demandas)}")
        st.write(f"**Conflitos de Horário:** {len(conflicts)}")
        st.write(f"**Capacidade Total:** {capacity_stats.get('capacidade_total', 0)}")

        if conflicts:
            st.warning(f"⚠️ {len(conflicts)} conflitos detectados neste semestre!")
            st.write("Use a aba '⚠️ Conflitos' para detalhes e resolução.")

    with col2:
        st.subheader("Ações Rápidas")

        # Status management
        if semestre.status == SemestreStatusEnum.PLANEJAMENTO:
            st.info("📋 O semestre está em fase de planejamento.")
            if st.button(
                "▶️ Iniciar Execução", type="primary", use_container_width=True
            ):
                if SemesterService.update_semestre_status(
                    semestre_id, SemestreStatusEnum.EXECUCAO
                ):
                    st.success(f"✅ Semestre {semestre.nome} iniciado para execução!")
                    st.rerun()
        elif semestre.status == SemestreStatusEnum.EXECUCAO:
            st.info("🚀 O semestre está em execução ativa.")
            if st.button(
                "✅ Finalizar Semestre", type="primary", use_container_width=True
            ):
                if SemesterService.update_semestre_status(
                    semestre_id, SemestreStatusEnum.FINALIZADO
                ):
                    st.success(f"✅ Semestre {semestre.nome} finalizado com sucesso!")
                    st.rerun()
        elif semestre.status == SemestreStatusEnum.FINALIZADO:
            st.success("✅ Semestre já finalizado.")

        st.markdown("---")

        # Quick actions
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(
                "📄 Ver Relatório Completo", type="secondary", use_container_width=True
            ):
                st.info("Relatórios semestrais (em desenvolvimento)")

        with col2:
            if st.button(
                "📊 Verificar Capacidades", type="secondary", use_container_width=True
            ):
                st.info("Verificação de capacidade (em desenvolvimento)")

        with col3:
            if st.button(
                "📅 Gerar Relatório PDF", type="secondary", use_container_width=True
            ):
                st.info("Relatórios em PDF (em desenvolvimento)")


def render_edit_semestre_form(semestre_id: int):
    """Render edit semester form"""
    semestre = SemesterService.get_semestre_by_id(semestre_id)

    if not semestre:
        st.error("Semestre não encontrado.")
        return

    st.subheader(f"✏️ Editar Semestre: {semestre.nome}")

    with st.form(f"edit_semestre_form_{semestre_id}"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome do Semestre",
                value=semestre.nome,
                max_length=10,
                help="Formato: YYYY.N (ex: 2025.1)",
            )

            descricao = st.text_area(
                "Descrição do Semestre", value=semestre.descricao or "", max_length=500
            )

        with col2:
            status = st.selectbox(
                "Status do Semestre",
                options=[
                    SemestreStatusEnum.PLANEJAMENTO,
                    SemestreStatusEnum.EXECUCAO,
                    SemestreStatusEnum.FINALIZADO,
                ],
                index=list(
                    [
                        SemestreStatusEnum.PLANEJAMENTO,
                        SemestreStatusEnum.EXECUCAO,
                        SemestreStatusEnum.FINALIZADO,
                    ]
                ).index(semestre.status),
                help="Selecione o status do semestre",
            )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("💾 Salvar Alterações", type="primary")

        with col2:
            if st.form_submit_button("❌ Cancelar", type="secondary"):
                del st.session_state["editing_semestre"]
                st.rerun()

        if submitted:
            # Validate inputs
            if not nome:
                st.error("❌ Nome do semestre é obrigatório.")
                return

            if len(nome) < 5 or len(nome) > 10:
                st.error(
                    "❌ Nome do semestre deve ter entre 5 e 10 caracteres (formato YYYY.N)."
                )
                return

            # Validate semester name format
            import re

            pattern = r"^\d{4}\.\d{1}$"
            if not re.match(pattern, nome):
                st.error("❌ Formato inválido. Use o formato YYYY.N (ex: 2025.1)")
                return

            # Update semester status
            updated_semestre = SemesterService.update_semestre_status(
                semestre_id, status
            )
            if updated_semestre:
                st.success(f"✅ Semestre '{nome}' atualizado com sucesso!")
                del st.session_state["editing_semestre"]
                st.rerun()
            else:
                st.error(f"❌ Falha ao atualizar semestre '{nome}'.")


def main():
    """Main entry point for the semesters page"""
    render_semestres_page()


if __name__ == "__main__":
    main()
