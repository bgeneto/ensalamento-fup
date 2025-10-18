"""
Demand management page for Sistema de Ensalamento FUP/UnB
Administrative interface for managing semester demands and course scheduling
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from src.services.semester_service import SemesterService
from src.services.inventory_service import InventoryService
from src.services.auth_service import is_current_user_admin
from src.services.mock_api_service import MockApiService
from models import DemandaCreate, DemandaUpdate, SemestreStatusEnum


def render_demandas_page():
    """Render demand management page"""
    st.title("📚 Gestão de Demandas Semestrais")
    st.caption("Gerencie demandas de disciplinas, horários e alocação de salas")

    # Check if user is admin
    if not is_current_user_admin():
        st.error("❌ Acesso negado. Esta página requer privilégios de administrador.")
        return

    # Create tabs for different operations
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📋 Lista de Demandas",
            "➕ Criar Demanda",
            "📊 Estatísticas",
            "🔄 Importar Dados",
            "⚠️ Conflitos",
        ]
    )

    with tab1:
        render_demand_list()

    with tab2:
        render_create_demand()

    with tab3:
        render_statistics()

    with tab4:
        render_data_import()

    with tab5:
        render_conflicts()


def render_demand_list():
    """Render list of all demands"""
    st.header("📋 Lista de Demandas")

    # Semester selection
    semestres = SemesterService.get_all_semestres()
    if not semestres:
        st.info("Nenhum semestre encontrado. Crie um semestre primeiro.")
        return

    # Find current semester
    current_semestre = SemesterService.get_current_semestre()
    current_semestre_id = current_semestre.id if current_semestre else semestres[0].id

    # Semester selector
    semester_options = {f"{sem.nome} ({semestre.status})": sem.id for sem in semestres}
    selected_semestre_id = st.selectbox(
        "Selecione o Semestre:",
        options=list(semester_options.keys()),
        index=(
            list(semester_options.values()).index(current_semestre_id)
            if current_semestre_id in semester_options.values()
            else 0
        ),
        help="Selecione o semestre para visualizar as demandas",
    )
    semestre_id = semester_options[selected_semestre_id]

    # Get semester info
    semestre = SemesterService.get_semestre_by_id(semestre_id)

    if not semestre:
        st.error("Semestre não encontrado.")
        return

    # Display semester info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Semestre", semestre.nome)
    with col2:
        st.metric("Status", semestre.status)
    with col3:
        # Status change buttons
        if semestre.status == SemestreStatusEnum.PLANEJAMENTO:
            if st.button("▶️ Iniciar Execução", type="primary"):
                if SemesterService.update_semestre_status(
                    semestre_id, SemestreStatusEnum.EXECUCAO
                ):
                    st.success("Status atualizado para Execução!")
                    st.rerun()
        elif semestre.status == SemestreStatusEnum.EXECUCAO:
            if st.button("✅ Finalizar Semestre", type="primary"):
                if SemesterService.update_semestre_status(
                    semestre_id, SemestreStatusEnum.FINALIZADO
                ):
                    st.success("Semestre finalizado!")
                    st.rerun()

    st.markdown("---")

    # Get demands for selected semester
    demandas = SemesterService.get_demandas_by_semestre(semestre_id)

    if not demandas:
        st.info(f"Nenhuma demanda encontrada para o semestre {semestre.nome}.")
        return

    # Display statistics
    stats = SemesterService.get_semester_statistics(semestre_id)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Demandas", stats["demandas"]["total"])
    with col2:
        st.metric("Disciplinas Únicas", stats["demandas"]["disciplinas_unicas"])
    with col3:
        st.metric("Conflitos", stats["demandas"]["conflitos_horario"])
    with col4:
        capacity_stats = SemesterService.get_capacity_requirements(semestre_id)
        st.metric("Capacidade Total", capacity_stats.get("capacidade_total", 0))

    st.markdown("---")

    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_discipline = st.text_input(
            "Filtrar por Disciplina:", placeholder="ex: FUP0001"
        )
    with col2:
        filter_professor = st.text_input(
            "Filtrar por Professor:", placeholder="ex: João Silva"
        )
    with col3:
        filter_turma = st.text_input("Filtrar por Turma:", placeholder="ex: A")

    # Apply filters
    filtered_demandas = demandas
    if filter_discipline:
        filtered_demandas = [
            d
            for d in filtered_demandas
            if filter_discipline.lower() in (d.codigo_disciplina or "").lower()
        ]
    if filter_professor:
        filtered_demandas = [
            d
            for d in filtered_demandas
            if filter_professor.lower() in (d.professores_disciplina or "").lower()
        ]
    if filter_turma:
        filtered_demandas = [
            d
            for d in filtered_demandas
            if filter_turma.upper() in (d.turma_disciplina or "").upper()
        ]

    if not filtered_demandas:
        st.info("Nenhuma demanda encontrada com os filtros selecionados.")
        return

    # Display demands
    for demanda in filtered_demandas:
        with st.expander(
            f"📚 {demanda.codigo_disciplina} - {demanda.nome_disciplina or 'Sem nome'} ({demanda.turma_disciplina or 'Sem turma'})"
        ):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(f"**Código:** {demanda.codigo_disciplina}")
                st.write(f"**Nome:** {demanda.nome_disciplina or 'Não especificado'}")
                st.write(
                    f"**Professor(es):** {demanda.professores_disciplina or 'Não especificado'}"
                )
                st.write(f"**Turma:** {demanda.turma_disciplina or 'Não especificada'}")
                st.write(f"**Vagas:** {demanda.vagas_disciplina or 0}")
                st.write(f"**Nível:** {demanda.nivel_disciplina or 'Não especificado'}")
                st.write(f"**Horário SIGAA:** `{demanda.horario_sigaa_bruto}`")

                # Parse and display schedule
                parsed_schedule = SemesterService.parse_demand_schedule(demanda)
                if parsed_schedule and parsed_schedule.get("horario_parseado"):
                    st.write("**Horário Detalhado:**")
                    for item in parsed_schedule["horario_parseado"]:
                        dia_nome = item.get(
                            "dia_semana_nome", f"Dia {item.get('dia_semana_id', '?')}"
                        )
                        st.write(
                            f"  • {dia_nome} - Bloco {item.get('codigo_bloco', '?')}"
                        )

            with col2:
                if st.button(f"Editar", key=f"edit_demand_{demanda.id}"):
                    st.session_state["editing_demand"] = demanda.id
                    st.rerun()

            with col3:
                if st.button(
                    f"Excluir", key=f"delete_demand_{demanda.id}", type="secondary"
                ):
                    if SemesterService.delete_demanda(demanda.id):
                        st.success(f"Demanda excluída com sucesso!")
                        st.rerun()

    # Check if there's a demand being edited
    if "editing_demand" in st.session_state:
        render_edit_demand_form(st.session_state["editing_demand"], semestre_id)


def render_create_demand():
    """Render create demand form"""
    st.header("➕ Criar Nova Demanda")

    # Get available semesters
    semestres = SemesterService.get_all_semestres()
    if not semestres:
        st.error("Nenhum semestre disponível. Crie um semestre primeiro.")
        return

    # Filter for planning semesters
    planning_semestres = [
        s
        for s in semestres
        if s.status in [SemestreStatusEnum.PLANEJAMENTO, SemestreStatusEnum.EXECUCAO]
    ]
    if not planning_semestres:
        st.info("Nenhum semestre em planejamento ou execução disponível.")
        return

    # Get room types for suggestions
    room_types = InventoryService.get_all_tipos_sala()

    with st.form("create_demand_form"):
        st.subheader("Informações da Demanda")

        col1, col2 = st.columns(2)

        with col1:
            # Semester selection
            semester_options = {
                f"{sem.nome} ({semestre.status})": sem.id for sem in planning_semestres
            }
            selected_semestre = st.selectbox(
                "Semestre:",
                options=list(semester_options.keys()),
                help="Selecione o semestre para esta demanda",
            )
            semestre_id = semester_options[selected_semestre]

            codigo_disciplina = st.text_input(
                "Código da Disciplina",
                placeholder="ex: FUP0001",
                help="Código da disciplina no sistema acadêmico",
            )

            nome_disciplina = st.text_area(
                "Nome da Disciplina",
                placeholder="ex: Fundamentos de Programação",
                help="Nome completo da disciplina",
            )

            turma_disciplina = st.text_input(
                "Turma", placeholder="ex: A", help="Código da turma"
            )

        with col2:
            vagas_disciplina = st.number_input(
                "Vagas",
                min_value=1,
                max_value=200,
                value=40,
                help="Número de vagas oferecidas",
            )

            professores_disciplina = st.text_area(
                "Professor(es)",
                placeholder="ex: João Silva, Maria Santos",
                help="Nome(s) do(s) professor(es) responsável(is)",
            )

            nivel_disciplina = st.text_input(
                "Nível",
                placeholder="ex: Graduação",
                help="Nível acadêmico da disciplina",
            )

        st.markdown("---")

        st.subheader("Horário SIGAA")
        st.info(
            """
        **Formato SIGAA:** Use o formato padrão do SIGAA para especificar horários.
        Exemplos:
        - `24M12` - Segunda-feira, Bloco M1-M2
        - `35T23` - Terça-feira, Bloco T2-T3
        - `65N12` - Sexta-feira, Bloco N1-N2
        - `24M12 44M34` - Múltiplos horários separados por espaço
        """
        )

        horario_sigaa_bruto = st.text_input(
            "Horário SIGAA",
            placeholder="ex: 24M12 44M34",
            help="Horário no formato SIGAA",
        )

        st.markdown("---")

        submitted = st.form_submit_button(
            "Criar Demanda", type="primary", use_container_width=True
        )

        if submitted:
            # Validate inputs
            if not codigo_disciplina:
                st.error("❌ Código da disciplina é obrigatório.")
                return

            # Create demand
            demanda_data = DemandaCreate(
                semestre_id=semestre_id,
                codigo_disciplina=codigo_disciplina,
                nome_disciplina=nome_disciplina if nome_disciplina else None,
                professores_disciplina=(
                    professores_disciplina if professores_disciplina else None
                ),
                turma_disciplina=turma_disciplina if turma_disciplina else None,
                vagas_disciplina=vagas_disciplina,
                horario_sigaa_bruto=horario_sigaa_bruto,
                nivel_disciplina=nivel_disciplina if nivel_disciplina else None,
            )

            new_demanda = SemesterService.create_demanda(demanda_data)
            if new_demanda:
                st.success(f"✅ Demanda '{codigo_disciplina}' criada com sucesso!")
                st.rerun()
            else:
                st.error(
                    f"❌ Falha ao criar demanda. Verifique os dados e o formato do horário SIGAA."
                )


def render_statistics():
    """Render semester statistics dashboard"""
    st.header("📊 Estatísticas do Semestre")

    # Semester selection
    semestres = SemesterService.get_all_semestres()
    if not semestres:
        st.info("Nenhum semestre encontrado.")
        return

    semester_options = {f"{sem.nome} ({semestre.status})": sem.id for sem in semestres}
    selected_semestre = st.selectbox(
        "Selecione o Semestre:",
        options=list(semester_options.keys()),
        help="Selecione o semestre para visualizar estatísticas",
    )
    semestre_id = semester_options[selected_semestre]

    # Get comprehensive statistics
    stats = SemesterService.get_semester_statistics(semestre_id)

    if not stats:
        st.error("Não foi possível carregar as estatísticas.")
        return

    st.subheader(f"📈 Estatísticas - {stats['semestre']['nome']}")

    # Overall metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Demandas", stats["demandas"]["total"])
    with col2:
        st.metric("Disciplinas Únicas", stats["demandas"]["disciplinas_unicas"])
    with col3:
        st.metric("Conflitos de Horário", stats["demandas"]["conflitos_horario"])

    st.markdown("---")

    # Distribution by level
    if stats.get("distribuicao", {}).get("por_nivel"):
        st.subheader("📚 Distribuição por Nível")
        nivel_data = stats["distribuicao"]["por_nivel"]
        if nivel_data:
            nivel_labels = list(nivel_data.keys())
            nivel_values = list(nivel_data.values())

            st.bar_chart(nivel_labels, nivel_values)

    st.markdown("---")

    # Distribution by vacancy ranges
    if stats.get("distribuicao", {}).get("por_faixa_vagas"):
        st.subheader("👥 Distribuição por Faixa de Vagas")
        vagas_data = stats["distribuicao"]["por_faixa_vagas"]
        if vagas_data:
            vagas_labels = list(vagas_data.keys())
            vagas_values = list(vagas_data.values())

            st.bar_chart(vagas_labels, vagas_values)

    st.markdown("---")

    # Capacity requirements
    capacity_stats = SemesterService.get_capacity_requirements(semestre_id)
    if capacity_stats:
        st.subheader("📊 Requisitos de Capacidade")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Mínimo", capacity_stats.get("min_capacidade", 0))
        with col2:
            st.metric("Máximo", capacity_stats.get("max_capacidade", 0))
        with col3:
            st.metric("Total", capacity_stats.get("capacidade_total", 0))
        with col4:
            st.metric("Média", capacity_stats.get("capacidade_media", 0))

    st.markdown("---")

    # Conflicts
    if stats.get("conflitos"):
        st.subheader("⚠️ Conflitos de Horário Detectados")

        if stats["conflitos"]:
            for i, conflict in enumerate(stats["conflitos"], 1):
                with st.expander(
                    f"Conflito {i}: Dia {conflict['dia_semana_id']}, Bloco {conflict['codigo_bloco']}"
                ):
                    for item in conflict["conflitos"]:
                        st.write(
                            f"• **{item['disciplina']}** - {item['nome_disciplina']}"
                        )
                        st.write(f"  Turma: {item['turma']}")
                        st.write(f"  Professor: {item['professor']}")
        else:
            st.success("✅ Nenhum conflito de horário detectado!")


def render_data_import():
    """Render data import interface"""
    st.header("🔄 Importação de Dados")
    st.caption("Importe dados de disciplinas e demandas usando dados mock ou arquivos")

    st.subheader("📋 Gerar Dados Mock")

    col1, col2 = st.columns(2)

    with col1:
        st.write(
            "Use os botões abaixo para gerar dados de exemplo para teste do sistema:"
        )

        if st.button("🎓 Gerar Professores Mock", type="primary"):
            with st.spinner("Gerando professores..."):
                created = MockApiService.create_mock_professors()
                if created:
                    st.success(f"✅ {len(created)} professores criados com sucesso!")
                    for prof in created[:3]:  # Show first 3
                        st.info(
                            f"• {prof['username']} - {prof['nome_completo']} (senha: {prof['senha_temp']})"
                        )
                    if len(created) > 3:
                        st.info(f"... e mais {len(created) - 3} professores")
                else:
                    st.error("❌ Falha ao gerar professores.")

        st.markdown("---")

        # Generate mock demands for current semester
        current_semestre = SemesterService.get_current_semestre()
        if current_semestre:
            if st.button("📚 Gerar Demandas Mock", type="primary"):
                with st.spinner("Gerando demandas..."):
                    mock_demands = MockApiService.create_mock_demands(
                        current_semestre.id, 10
                    )
                    st.info(f"Geradas {len(mock_demands)} demandas mock para teste.")

                    # Show some examples
                    for i, demanda in enumerate(mock_demands[:3], 1):
                        st.write(
                            f"{i}. **{demanda.codigo_disciplina}** - {demanda.nome_disciplina}"
                        )
                        st.write(f"   Horário: {demanda.horario_sigaa_bruto}")
                        st.write(f"   Vagas: {demanda.vagas_disciplina}")
                        st.write(f"   Professor: {demanda.professores_disciplina}")
                        st.write(f"   Turma: {demanda.turma_disciplina}")
                    if len(mock_demands) > 3:
                        st.write(f"... e {len(mock_demands) - 3} demandas mais.")
    with col2:
        st.subheader("📊 Estatísticas Disponíveis")

        # Display mock data statistics
        disciplines = MockApiService.generate_mock_disciplines()
        st.write(f"**Disciplinas Disponíveis:** {len(disciplines)}")
        st.write("**Padrões de Horário:** 5 padrões diferentes")
        st.write("**Turmas Padrão:** A, B, C, D, E")

        st.markdown("---")

        st.subheader("📁 Exportar Dados")

        export_format = st.selectbox(
            "Formato de Exportação:",
            options=["JSON", "CSV"],
            help="Selecione o formato para exportar os dados",
        )

        if st.button("📤 Exportar Dados Mock", type="secondary"):
            exported_data = MockApiService.export_mock_data(export_format.lower())
            if "error" in exported_data:
                st.error(f"❌ Erro na exportação: {exported_data['error']}")
            else:
                st.success(f"✅ Dados exportados em formato {export_format}!")
                st.json(exported_data)


def render_conflicts():
    """Render conflict detection and resolution"""
    st.header("⚠️ Detecção de Conflitos")
    st.caption("Identifique e resolva conflitos de horários nas demandas semestrais")

    # Semester selection
    semestres = SemesterService.get_all_semestres()
    if not semestres:
        st.info("Nenhum semestre encontrado.")
        return

    semester_options = {f"{sem.nome} ({semestre.status})": sem.id for sem in semestres}
    selected_semestre = st.selectbox(
        "Selecione o Semestre:",
        options=list(semester_options.keys()),
        help="Selecione o semestre para analisar conflitos",
    )
    semestre_id = semester_options[selected_semestre]

    # Get conflicts
    conflicts = SemesterService.get_schedule_conflicts(semestre_id)

    st.subheader(f"🔍 Análise de Conflitos - {selected_semestre}")

    if not conflicts:
        st.success("✅ Nenhum conflito de horário detectado!")
        st.info("Todas as demandas estão com horários compatíveis.")
        return

    # Conflict summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Conflitos", len(conflicts))
    with col2:
        # Count unique conflicts (different day/time combinations)
        unique_conflicts = len(
            set(f"{c['dia_semana_id']}_{c['codigo_bloco']}" for c in conflicts)
        )
        st.metric("Conflitos Únicos", unique_conflicts)

    st.markdown("---")

    # Display conflicts with details
    for i, conflict in enumerate(conflicts, 1):
        st.subheader(
            f"⚠️ Conflito {i}: Dia {conflict['dia_semana_id']}, Bloco {conflict['codigo_bloco']}"
        )

        st.write("**Demandas em Conflito:**")
        for j, item in enumerate(conflict["conflitos"], 1):
            st.write(f"{j}. **{item['disciplina']}** ({item['nome_disciplina']})")
            st.write(f"   - Turma: {item['turma']}")
            st.write(f"   - Professor: {item['professor']}")
            st.write(
                f"   - Vagas: {SemestreService.get_demanda_by_id(item['demanda_id']).vagas_disciplina}"
            )

        st.markdown("---")

        # Resolution suggestions
        st.write("💡 **Sugestões de Resolução:**")
        st.info(
            """
        Para resolver este conflito, considere:
        1. Alterar o horário de uma das disciplinas
        2. Mudar a sala para uma que possa acomodar múltiplas disciplinas
        3. Dividir turmas em diferentes horários
        4. Verificar se há salas disponíveis em outros horários
        """
        )

    st.markdown("---")

    # General recommendations
    st.subheader("📋 Recomendações Gerais")

    st.write("🔧 **Para evitar conflitos no futuro:**")
    st.write(
        "1. **Planejamento Antecipado:** Analise os horários antes de criar as demandas"
    )
    st.write("2. **Validação SIGAA:** Use o formato correto dos horários SIGAA")
    st.write(
        "3. **Verificação de Capacidade:** Confirme se as salas comportam as vagas necessárias"
    )
    st.write(
        "4. **Consulta de Conflitos:** Use esta ferramenta regularmente durante o planejamento"
    )


def render_edit_demand_form(demanda_id: int, semestre_id: int):
    """Render edit demand form"""
    demanda = SemesterService.get_demanda_by_id(demanda_id)

    if not demanda:
        st.error("Demanda não encontrada.")
        return

    st.subheader(f"✏️ Editar Demanda: {demanda.codigo_disciplina}")

    with st.form(f"edit_demand_form_{demanda_id}"):
        col1, col2 = st.columns(2)

        with col1:
            nome_disciplina = st.text_area(
                "Nome da Disciplina",
                value=demanda.nome_disciplina or "",
                help="Nome completo da disciplina",
            )

            professores_disciplina = st.text_area(
                "Professor(es)",
                value=demanda.professores_disciplina or "",
                help="Nome(s) do(s) professor(es) responsável(is)",
            )

            turma_disciplina = st.text_input(
                "Turma", value=demanda.turma_disciplina or "", help="Código da turma"
            )

        with col2:
            vagas_disciplina = st.number_input(
                "Vagas",
                min_value=1,
                max_value=200,
                value=demanda.vagas_disciplina or 0,
                help="Número de vagas oferecidas",
            )

            nivel_disciplina = st.text_input(
                "Nível",
                value=demanda.nivel_disciplina or "",
                help="Nível acadêmico da disciplina",
            )

        st.markdown("---")

        st.subheader("⏰ Horário SIGAA")
        st.info("Use o formato padrão SIGAA. Ex: 24M12, 35T23, etc.")

        horario_sigaa_bruto = st.text_input(
            "Horário SIGAA",
            value=demanda.horario_sigaa_bruto,
            help="Horário no formato SIGAA",
        )

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("�Salvar Alterações", type="primary")

        with col2:
            if st.form_submit_button("❌ Cancelar", type="secondary"):
                del st.session_state["editing_demand"]
                st.rerun()

        if submitted:
            # Validate inputs
            if not nome_disciplina:
                st.error("❌ Nome da disciplina é obrigatório.")
                return

            # Update demand
            demanda_data = DemandaUpdate(
                nome_disciplina=nome_disciplina,
                professores_disciplina=professores_disciplina,
                turma_disciplina=turma_disciplina,
                vagas_disciplina=vagas_disciplina,
                horario_sigaa_bruto=horario_sigaa_bruto,
                nivel_disciplina=nivel_disciplina,
            )

            updated_demanda = SemesterService.update_demanda(demanda_id, demanda_data)
            if updated_demanda:
                st.success(f"✅ Demanda atualizada com sucesso!")
                del st.session_state["editing_demand"]
                st.rerun()
            else:
                st.error(
                    "❌ Falha ao atualizar demanda. Verifique os dados e o formato do horário."
                )


def main():
    """Main entry point for the demands page"""
    render_demandas_page()


if __name__ == "__main__":
    main()
