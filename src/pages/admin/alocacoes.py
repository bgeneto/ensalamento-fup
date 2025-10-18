"""
Room allocation management page for Sistema de Ensalamento FUP/UnB
Administrative interface for managing room allocations and scheduling
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from src.services.allocation_service import AllocationService
from src.services.semester_service import SemesterService
from src.services.inventory_service import InventoryService
from src.services.auth_service import is_current_user_admin
import pandas as pd


def render_alocacoes_page():
    """Render allocation management page"""
    st.title("🏢 Gestão de Alocações")
    st.caption("Gerencie alocações de salas e otimização de utilização")

    # Check if user is admin
    if not is_current_user_admin():
        st.error("❌ Acesso negado. Esta página requer privilégios de administrador.")
        return

    # Create tabs for different operations
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📊 Dashboard de Alocações",
            "🤖 Alocação Automática",
            "📋 Gerenciar Alocações",
            "📈 Análise de Utilização",
            "⚙️ Regras de Alocação",
        ]
    )

    with tab1:
        render_allocation_dashboard()

    with tab2:
        render_auto_allocation()

    with tab3:
        render_allocation_management()

    with tab4:
        render_utilization_analysis()

    with tab5:
        render_allocation_rules()


def render_allocation_dashboard():
    """Render allocation statistics dashboard"""
    st.header("📊 Dashboard de Alocações")

    # Semester selection
    semestres = SemesterService.get_all_semestres()
    if not semestres:
        st.info("Nenhum semestre encontrado. Crie um semestre primeiro.")
        return

    semester_options = {f"{sem.nome} ({semestre.status})": sem.id for sem in semestres}
    selected_semestre = st.selectbox(
        "Selecione o Semestre:",
        options=list(semester_options.keys()),
        help="Selecione o semestre para visualizar alocações",
    )
    semestre_id = semester_options[selected_semestre]

    # Get allocation statistics
    stats = AllocationService.get_allocation_statistics(semestre_id)

    if not stats:
        st.error("Não foi possível carregar estatísticas de alocação.")
        return

    st.subheader(f"📈 Estatísticas - {stats['semestre']['nome']}")

    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Demandas", stats["demandas"]["total"])
    with col2:
        st.metric("Demandas Alocadas", stats["demandas"]["alocadas"])
    with col3:
        st.metric("Taxa de Alocação", f"{stats['demandas']['taxa_alocacao']:.1f}%")
    with col4:
        st.metric("Total Alocações", stats["alocacoes"]["total"])

    st.markdown("---")

    # Utilization metrics
    st.subheader("📊 Utilização de Recursos")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Salas Utilizadas:** {stats['alocacoes']['salas_utilizadas']}")
        st.write(
            f"**Média de Utilização:** {stats['utilizacao']['media_capacidade']:.1f}%"
        )

        # Room usage chart
        if stats["utilizacao"]["uso_salas"]:
            st.subheader("📈 Uso por Sala")
            room_usage = stats["utilizacao"]["uso_salas"]

            # Get room names for better visualization
            room_names = {}
            for room_id in room_usage.keys():
                room = InventoryService.get_sala_by_id(room_id)
                if room:
                    room_names[room_id] = room.nome

            if room_names:
                usage_data = {
                    room_names.get(room_id, f"Sala {room_id}"): count
                    for room_id, count in room_usage.items()
                }

                st.bar_chart(usage_data)

    with col2:
        # Room efficiency analysis
        st.subheader("🎯 Eficiência das Alocações")

        efficiency_data = []
        allocations = stats["alocacoes"]["total"]

        if allocations > 0:
            # Get room capacity details
            from database import DatabaseSession, AlocacaoSemestral, Sala, Demanda

            with DatabaseSession() as session:
                allocation_details = (
                    session.query(AlocacaoSemestral)
                    .filter(AlocacaoSemestral.semestre_id == semestre_id)
                    .all()
                )

                for allocation in allocation_details:
                    room = (
                        session.query(Sala)
                        .filter(Sala.id == allocation.sala_id)
                        .first()
                    )
                    demanda = (
                        session.query(Demanda)
                        .filter(Demanda.id == allocation.demanda_id)
                        .first()
                    )

                    if room and demanda:
                        vagas = demanda.vagas_disciplina or 0
                        capacidade = room.capacidade or 1
                        utilization = (vagas / capacidade) * 100

                        efficiency_data.append(
                            {
                                "sala": room.nome,
                                "disciplina": demanda.codigo_disciplina,
                                "utilizacao": utilization,
                                "vagas": vagas,
                                "capacidade": capacidade,
                                "eficiencia": (
                                    "Ótima"
                                    if 80 <= utilization <= 90
                                    else (
                                        "Boa"
                                        if 70 <= utilization < 80
                                        else (
                                            "Regular"
                                            if 50 <= utilization < 70
                                            else "Ruim"
                                        )
                                    )
                                ),
                            }
                        )

        if efficiency_data:
            # Create efficiency analysis table
            st.write("Análise de Eficiência por Alocação:")

            for item in efficiency_data[:10]:  # Show first 10 items
                efficiency_color = {
                    "Ótima": "🟢",
                    "Boa": "🟡",
                    "Regular": "🟠",
                    "Ruim": "🔴",
                }.get(item["eficiencia"], "⚪")

                st.write(
                    f"{efficiency_color} **{item['sala']}** - {item['disciplina']}"
                )
                st.write(
                    f"   Utilização: {item['utilização']:.1f}% ({item['vagas']}/{item['capacidade']})"
                )
                st.write(f"   Eficiência: {item['eficiencia']}")
                st.markdown("---")

    st.markdown("---")

    # Recent allocations
    st.subheader("📅 Alocações Recentes")

    # Show recent allocations with details
    recent_allocations = []
    from database import (
        DatabaseSession,
        AlocacaoSemestral,
        Demanda,
        Sala,
        DiaSemana,
        HorarioBloco,
    )

    with DatabaseSession() as session:
        allocations = (
            session.query(AlocacaoSemestral)
            .filter(AlocacaoSemestral.semestre_id == semestre_id)
            .limit(10)
            .all()
        )

        for allocation in allocations:
            demanda = (
                session.query(Demanda)
                .filter(Demanda.id == allocation.demanda_id)
                .first()
            )
            sala = session.query(Sala).filter(Sala.id == allocation.sala_id).first()
            dia_semana = (
                session.query(DiaSemana)
                .filter(DiaSemana.id_sigaa == allocation.dia_semana_id)
                .first()
            )
            horario = (
                session.query(HorarioBloco)
                .filter(HorarioBloco.codigo_bloco == allocation.codigo_bloco)
                .first()
            )

            if demanda and sala and dia_semana and horario:
                recent_allocations.append(
                    {
                        "demanda": demanda.codigo_disciplina,
                        "sala": sala.nome,
                        "dia_semana": dia_semana.nome,
                        "horario": f"{horario.horario_inicio.strftime('%H:%M')} - {horario.horario_fim.strftime('%H:%M')}",
                        "professor": demanda.professores_disciplina,
                        "vagas": demanda.vagas_disciplina,
                        "capacidade": sala.capacidade,
                    }
                )

    if recent_allocations:
        st.dataframe(pd.DataFrame(recent_allocations))
    else:
        st.info("Nenhuma alocação encontrada para este semestre.")


def render_auto_allocation():
    """Render automatic allocation interface"""
    st.header("🤖 Alocação Automática")
    st.caption("Alocação inteligente de salas baseada em regras e otimização")

    # Semester selection
    semestres = SemesterService.get_all_semestres()
    if not semestres:
        st.warning("Nenhum semestre disponível para alocação.")
        return

    # Filter semestres in planning or execution status
    available_semestres = [
        s for s in semestres if s.status in ["Planejamento", "Execução"]
    ]
    if not available_semestres:
        st.info(
            "Todos os semestres estão finalizados. Crie um novo semestre para alocações."
        )
        return

    semester_options = {
        f"{sem.nome} ({semestre.status})": sem.id for sem in available_semestres
    }
    selected_semestre = st.selectbox(
        "Selecione o Semestre:",
        options=list(semester_options.keys()),
        help="Selecione o semestre para alocação automática",
    )
    semestre_id = semester_options[selected_semestre]

    st.subheader(f"🔧 Configuração de Alocação - {selected_semestre}")

    # Allocation strategy
    col1, col2 = st.columns(2)

    with col1:
        allocation_strategy = st.selectbox(
            "Estratégia de Alocação:",
            options=[
                "Priorizar Ocupação (80-90%)",
                "Priorizar Menor Excesso de Capacidade",
                "Prioritar Salas Próximas",
                "Balance Geral (Padrão)",
            ],
            help="Selecione a estratégia de alocação preferencial",
        )

        overwrite_existing = st.checkbox(
            "Sobreescrever Alocações Existentes",
            value=False,
            help="Marque para limpar alocações existentes antes de alocar novamente",
        )

    with col2:
        include_unallocated = st.checkbox(
            "Incluir Demandas Parcialmente Alocadas",
            value=True,
            help="Tente alocar mesmo que alguns horários não consiguem sala",
        )

        max_failed_slots = st.number_input(
            "Máximo de Horários Falhados",
            min_value=0,
            max_value=10,
            value=3,
            help="Número máximo de horários que podem falhar por demanda",
        )

    st.markdown("---")

    # Get unallocated demands
    demandas = SemesterService.get_demandas_by_semestre(semestre_id)

    if not demandas:
        st.info(f"Nenhuma demanda encontrada para o semestre {selected_semestre}.")
        return

    # Filter already allocated demands
    allocated_demands = set()
    from database import DatabaseSession, AlocacaoSemestral

    with DatabaseSession() as session:
        allocations = (
            session.query(AlocacaoSemestral)
            .filter(AlocacaoSemestral.semestre_id == semestre_id)
            .all()
        )
        allocated_demands = set(alloc.demanda_id for alloc in allocations)

    unallocated_demandas = [
        d for d in demandas if d.id not in allocated_demands or overwrite_existing
    ]

    if not unallocated_demandas:
        st.success("✅ Todas as demandas já estão alocadas!")
        return

    st.subheader(f"📋 Demandas para Alocação ({len(unallocated_demandas)})")

    # Show unallocated demands summary
    for i, demanda in enumerate(unallocated_demandas[:5], 1):
        with st.expander(f"📚 {demanda.codigo_disciplina} - {demanda.nome_disciplina}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**Código:** {demanda.codigo_disciplina}")
                st.write(f"**Nome:** {demanda.nome_disciplina}")
                st.write(f"**Turma:** {demanda.turma_disciplina}")
                st.write(f"**Professor:** {demanda.professores_disciplina}")
                st.write(f"**Vagas:** {demanda.vagas_disciplina}")

            with col2:
                st.write(f"**Horário:** {demanda.horario_sigaa_bruto}")

                # Show suitable rooms preview
                suitable_rooms = AllocationService.find_suitable_rooms(
                    demanda, exclude_allocated=True
                )
                if suitable_rooms:
                    st.write(f"**Salas Disponíveis:** {len(suitable_rooms)}")
                    st.write(f"**Melhor Opção:** {suitable_rooms[0]['room'].nome}")
                    st.write(f"**Score:** {suitable_rooms[0]['score']:.1f}")
                else:
                    st.error("❌ Nenhuma sala adequada encontrada")

            with col3:
                if st.button(
                    f"🤖 Alocar Agora",
                    key=f"allocate_single_{demanda.id}",
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner(f"Alocando {demanda.codigo_disciplina}..."):
                        result = AllocationService.auto_allocate_demanda(demanda.id)

                        if result["success"]:
                            st.success(
                                f"✅ {demanda.codigo_disciplina} alocado com sucesso!"
                            )
                            st.rerun()
                        else:
                            st.error(
                                f"❌ Falha na alocação: {result.get('error', 'Erro desconhecido')}"
                            )
                            if result.get("failed_slots"):
                                st.write(
                                    f"**Horários não alocados:** {', '.join(result['failed_slots'])}"
                                )

    if len(unallocated_demandas) > 5:
        st.info(f"... e mais {len(unallocated_demandas) - 5} demandas")

    st.markdown("---")

    # Auto allocation for all demands
    st.subheader("🚀 Alocação em Lote")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button(
            "🤖 Alocar Todas as Demandas", type="primary", use_container_width=True
        ):
            with st.spinner("Alocando todas as demandas..."):
                if overwrite_existing:
                    st.info("Limpando alocações existentes...")
                    AllocationService.clear_all_allocations(semestre_id)
                    st.rerun()
                else:
                    result = AllocationService.auto_allocate_semestre(semestre_id)

                    if result["success"]:
                        st.success(f"✅ Alocação em lote concluída!")
                        st.write(f"**Demandas Totais:** {result['total_demandas']}")
                        st.write(
                            f"**Sucesso Total:** {result['successful_allocations']}"
                        )
                        st.write(
                            f"**Alocações Parciais:** {result['partial_allocations']}"
                        )
                        st.write(f"**Falhas:** {result['failed_allocations']}")

                        # Show summary of results
                        if result["results"]:
                            st.write("\n📊 **Resultados Detalhados:**")
                            for res in result["results"]:
                                status_emoji = (
                                    "✅"
                                    if res["success"]
                                    else (
                                        "⚠️"
                                        if res.get("allocated_slots", 0) > 0
                                        else "❌"
                                    )
                                )
                                st.write(
                                    f"{status_emoji} **{res['demanda_codigo']}** ({res['demanda_nome']})"
                                )
                                if not res["success"] and res.get("failed_slots"):
                                    st.write(
                                        f"   Horários não alocados: {', '.join(res['failed_slots'])}"
                                    )
                                st.write(
                                    f"   Horários alocados: {res.get('allocated_slots', 0)}/{res.get('total_slots', 0)}"
                                )

                        st.rerun()
                    else:
                        st.error(
                            f"❌ Falha na alocação: {result.get('error', 'Erro desconhecido')}"
                        )

    with col2:
        if st.button(
            "🔄 Recalcular Estatísticas", type="secondary", use_container_width=True
        ):
            st.info("Recalculando estatísticas...")
            st.rerun()

    with col3:
        st.write("💡 **Dicas de Alocação:**")
        st.write("- Revise as regras de alocação para melhores resultados")
        st.write("- Verifique a disponibilidade de salas antes de alocar")
        st.write("- Considere otimizar a utilização das salas existentes")
        st.write("- Priorize disciplinas com requisitos específicos")


def render_allocation_management():
    """Render allocation management interface"""
    st.header("📋 Gerenciar Alocações")
    st.caption("Gerencie alocações individuais e ajustes manuais")

    # Semester selection
    semestres = SemesterService.get_all_semestres()
    if not semestres:
        st.info("Nenhum semestre encontrado.")
        return

    semester_options = {f"{sem.nome} ({semestre.status})": sem.id for sem in semestres}
    selected_semestre = st.selectbox(
        "Selecione o Semestre:",
        options=list(semester_options.keys()),
        help="Selecione o semestre para gerenciar alocações",
    )
    semestre_id = semester_options[selected_semestre]

    # Get allocations
    from database import DatabaseSession, AlocacaoSemestral

    with DatabaseSession() as session:
        allocations = (
            session.query(AlocacaoSemestral)
            .filter(AlocacaoSemestral.semestre_id == semestre_id)
            .all()
        )

    if not allocations:
        st.info(f"Nenhuma alocação encontrada para o semestre {selected_semestre}.")
        return

    st.subheader(f"📋 Alocações Existentes ({len(allocations)})")

    # Filter options
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_room = st.text_input("Filtrar por Sala:", placeholder="ex: Lab 101")
    with col2:
        filter_discipline = st.text_input(
            "Filtrar por Disciplina:", placeholder="ex: FUP0001"
        )
    with col3:
        filter_professor = st.text_input(
            "Filtrar por Professor:", placeholder="ex: João Silva"
        )

    # Display allocations
    for allocation in allocations:
        # Get related data
        from database import DatabaseSession, Demanda, Sala, DiaSemana, HorarioBloco

        with DatabaseSession() as session:
            demanda = (
                session.query(Demanda)
                .filter(Demanda.id == allocation.demanda_id)
                .first()
            )
            room = session.query(Sala).filter(Sala.id == allocation.sala_id).first()
            dia_semana = (
                session.query(DiaSemana)
                .filter(DiaSemana.id_sigaa == allocation.dia_semana_id)
                .first()
            )
            horario_bloco = (
                session.query(HorarioBloco)
                .filter(HorarioBloco.codigo_bloco == allocation.codigo_bloco)
                .first()
            )

        if not all([demanda, room, dia_semana, horario_bloco]):
            continue

        # Apply filters
        if filter_room and filter_room.lower() not in (room.nome or "").lower():
            continue
        if (
            filter_discipline
            and filter_discipline.lower()
            not in (demanda.codigo_disciplina or "").lower()
        ):
            continue
        if (
            filter_professor
            and filter_professor.lower()
            not in (demanda.professores_disciplina or "").lower()
        ):
            continue

        # Display allocation
        with st.expander(
            f"📚 {demanda.codigo_disciplina} - {room.nome} ({dia_semana.nome} {horario_bloco.codigo_bloco})"
        ):
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.write(
                    f"**Disciplina:** {demanda.codigo_disciplina} - {demanda.nome_disciplina}"
                )
                st.write(f"**Turma:** {demanda.turma_disciplina}")
                st.write(f"**Professor:** {demanda.professores_disciplina}")
                st.write(f"**Vagas:** {demanda.vagas_disciplina}")

                # Efficiency analysis
                vagas = demanda.vagas_disciplina or 0
                capacidade = room.capacidade or 1
                utilization = (vagas / capacidade) * 100

                efficiency_label = (
                    "Ótima"
                    if 80 <= utilization <= 90
                    else (
                        "Boa"
                        if 70 <= utilization < 80
                        else "Regular" if 50 <= utilization < 70 else "Ruim"
                    )
                )
                efficiency_color = (
                    "🟢"
                    if utilization >= 80
                    else (
                        "🟡"
                        if utilization >= 70
                        else "🟠" if utilization >= 50 else "🔴"
                    )
                )

                st.write(
                    f"**Utilização:** {efficiency_color} {utilization:.1f}% ({vagas}/{capacidade})"
                )
                st.write(f"**Eficiência:** {efficiency_label}")

            with col2:
                st.write(f"**Sala:** {room.nome}")
                st.write(
                    f"**Tipo:** {room.tipo_sala.nome if room.tipo_sala else 'Não definido'}"
                )
                st.write(f"**Capacidade:** {room.capacidade}")
                st.write(f"**Andar:** {room.andar or 'Térreo'}")
                st.write(f"**Horário:** {dia_semana.nome} {horario_bloco.codigo_bloco}")
                st.write(
                    f"**Tempo:** {horario_bloco.horario_inicio.strftime('%H:%M')} - {horario_bloco.horario_fim.strftime('%H:%M')}"
                )

            with col3:
                if st.button(
                    f"Editar",
                    key=f"edit_alloc_{allocation.id}",
                    use_container_width=True,
                ):
                    st.session_state[f"editing_allocation_{allocation.id}"] = True
                    st.rerun()

                if st.button(
                    f"Remover",
                    key=f"remove_alloc_{allocation.id}",
                    type="secondary",
                    use_container_width=True,
                ):
                    if AllocationService.remove_allocation(allocation.id):
                        st.success(f"Alocação removida com sucesso!")
                        st.rerun()
                    else:
                        st.error("Falha ao remover alocação.")

    # Check for editing state
    for allocation in allocations:
        if st.session_state.get(f"editing_allocation_{allocation.id}"):
            render_edit_allocation_form(allocation, semestre_id)
            break


def render_utilization_analysis():
    """Render utilization analysis interface"""
    st.header("📈 Análise de Utilização")
    st.caption("Análise detalhada da utilização de salas e eficiência das alocações")

    # Semester selection
    semestres = SemesterService.get_all_semestres()
    if not semestres:
        st.info("Nenhum semestre encontrado.")
        return

    semester_options = {f"{sem.nome} ({semestre.status})": sem.id for sem in semestres}
    selected_semestre = st.selectbox(
        "Selecione o Semestre:",
        options=list(semester_options.keys()),
        help="Selecione o semestre para análise",
    )
    semestre_id = semester_options[selected_semestre]

    # Room selection filter
    rooms = InventoryService.get_all_salas()
    if not rooms:
        st.error("Nenhuma sala encontrada no sistema.")
        return

    room_options = {f"{room.nome} (Cap: {room.capacidade})": room.id for room in rooms}
    selected_room = st.selectbox(
        "Selecione a Sala:",
        options=["Todas as Salas"] + list(room_options.keys()),
        help="Selecione uma sala específica ou analise todas",
    )

    room_id = None if selected_room == "Todas as Salas" else room_options[selected_room]

    st.subheader(f"📊 Análise de Utilização - {selected_room}")

    if room_id:
        # Single room analysis
        render_single_room_analysis(room_id, semestre_id)
    else:
        # Overall analysis
        render_overall_utilization_analysis(semestre_id)


def render_single_room_analysis(room_id: int, semestre_id: int):
    """Render analysis for a single room"""
    room = InventoryService.get_sala_by_id(room_id)
    if not room:
        st.error("Sala não encontrada.")
        return

    # Get room schedule
    schedule = AllocationService.get_room_schedule(room_id, semestre_id)

    if not schedule:
        st.info(f"Nenhuma alocação encontrada para a sala {room.nome}.")
        return

    st.write(f"### 📅 Horário da Sala: {room.nome}")
    st.write(f"**Capacidade:** {room.capacidade}")
    st.write(f"**Tipo:** {room.tipo_sala.nome if room.tipo_sala else 'Não definido'}")
    st.write(f"**Andar:** {room.andar or 'Térreo'}")

    # Create schedule visualization
    schedule_df = pd.DataFrame(schedule)
    st.dataframe(schedule_df, use_container_width=True)

    # Calculate utilization
    total_time_blocks = len(schedule)
    total_capacity_used = sum(s["vagas"] for s in schedule)
    avg_utilization = (
        (total_capacity_used / (total_time_blocks * room.capacidade)) * 100
        if total_time_blocks > 0 and room.capacidade > 0
        else 0
    )

    st.write(f"**Blocos de Tempo Alocados:** {total_time_blocks}")
    st.write(f"**Utilização Média:** {avg_utilization:.1f}%")

    # Time block utilization chart
    time_blocks = [s["codigo_bloco"] for s in schedule]
    block_usage = {}

    for block in time_blocks:
        block_usage[block] = block_usage.get(block, 0) + 1

    if block_usage:
        st.subheader("📊 Utilização por Bloco de Tempo")
        st.bar_chart(block_usage)

    # Day-based analysis
    days = list(set(s["dia_semana"] for s in schedule))
    day_usage = {}

    for day in days:
        day_allocations = [s for s in schedule if s["dia_semana"] == day]
        day_usage[day] = len(day_allocations)

    if day_usage:
        st.subheader("📅 Utilização por Dia da Semana")
        st.bar_chart(day_usage)


def render_overall_utilization_analysis(semestre_id: int):
    """Render overall utilization analysis for the semester"""
    # Get all rooms with allocations
    stats = AllocationService.get_allocation_statistics(semestre_id)

    if not stats:
        st.error("Não foi possível carregar estatísticas de utilização.")
        return

    st.write(f"### 📈 Análise Geral - {stats['semestre']['nome']}")

    # Room utilization ranking
    room_usage = stats["utilizacao"]["uso_salas"]
    if room_usage:
        st.subheader("🏆 Ranking de Utilização das Salas")

        # Get room names and calculate metrics
        room_metrics = []
        for room_id, usage_count in room_usage.items():
            room = InventoryService.get_sala_by_id(room_id)
            if room:
                room_metrics.append(
                    {
                        "room_name": room.nome,
                        "usage_count": usage_count,
                        "capacity": room.capacidade,
                        "efficiency": usage_count * 100,  # Simplified efficiency metric
                        "type": (
                            room.tipo_sala.nome if room.tipo_sala else "Não definido"
                        ),
                    }
                )

        # Sort by efficiency
        room_metrics.sort(key=lambda x: x["efficiency"], reverse=True)

        # Create ranking table
        ranking_df = pd.DataFrame(room_metrics)
        st.dataframe(ranking_df, use_container_width=True)

        # Efficiency distribution
        st.subheader("📊 Distribuição de Eficiência")

        efficiency_ranges = {
            "Excelente (>100 blocos)": len(
                [r for r in room_metrics if r["efficiency"] > 100]
            ),
            "Bom (50-100 blocos)": len(
                [r for r in room_metrics if 50 <= r["efficiency"] <= 100]
            ),
            "Regular (<50 blocos)": len(
                [r for r in room_metrics if r["efficiency"] < 50]
            ),
        }

        st.bar_chart(efficiency_ranges)

    # Capacity utilization analysis
    st.subheader("📊 Análise de Capacidade")

    # Get detailed capacity data
    from database import DatabaseSession, AlocacaoSemestral, Sala, Demanda

    with DatabaseSession() as session:
        allocations = (
            session.query(AlocacaoSemestral)
            .filter(AlocacaoSemestral.semestre_id == semestre_id)
            .all()
        )

        capacity_data = []
        for allocation in allocations:
            room = session.query(Sala).filter(Sala.id == allocation.sala_id).first()
            demanda = (
                session.query(Demanda)
                .filter(Demanda.id == allocation.demanda_id)
                .first()
            )

            if room and demanda:
                vagas = demanda.vagas_disciplina or 0
                capacidade = room.capacidade or 1
                utilization = (vagas / capacidade) * 100

                capacity_data.append(
                    {
                        "sala": room.nome,
                        "capacidade": capacidade,
                        "vagas_alocadas": vagas,
                        "utilizacao": utilization,
                        "eficiencia": (
                            "Ótima"
                            if 80 <= utilization <= 90
                            else (
                                "Boa"
                                if 70 <= utilization < 80
                                else "Regular" if 50 <= utilization < 70 else "Ruim"
                            )
                        ),
                    }
                )

    if capacity_data:
        capacity_df = pd.DataFrame(capacity_data)

        # Create capacity distribution chart
        efficiency_counts = {
            "Ótima (80-90%)": len(
                [c for c in capacity_data if 80 <= c["utilizacao"] <= 90]
            ),
            "Boa (70-80%)": len(
                [c for c in capacity_data if 70 <= c["utilizacao"] < 80]
            ),
            "Regular (50-70%)": len(
                [c for c in capacity_data if 50 <= c["utilizacao"] < 70]
            ),
            "Ruim (<50%)": len([c for c in capacity_data if c["utilizacao"] < 50]),
        }

        st.write("Distribuição de Eficiência de Capacidade:")
        st.bar_chart(efficiency_counts)

        st.write("Detalhes de Utilização:")
        st.dataframe(capacity_df, use_container_width=True)


def render_allocation_rules():
    """Render allocation rules management"""
    st.header("⚙️ Regras de Alocação")
    st.caption("Configure e gerencie regras para alocação automática de salas")

    # Get existing rules
    rules = AllocationService.get_allocation_rules()

    st.subheader("📋 Regras de Alocação Existentes")

    if not rules:
        st.info("Nenhuma regra de alocação encontrada.")
    else:
        for i, rule in enumerate(rules, 1):
            with st.expander(f"📋 {rule.descricao} (Prioridade: {rule.prioridade})"):
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.write(f"**ID:** {rule.id}")
                    st.write(f"**Tipo:** {rule.tipo_regra}")
                    st.write(f"**Prioridade:** {rule.prioridade}")
                    st.write(f"**Descrição:** {rule.descricao}")

                with col2:
                    try:
                        import json

                        config = json.loads(rule.config_json)
                        st.write("**Configuração:**")
                        st.json(config)
                    except:
                        st.write("**Configuração:**")
                        st.code(rule.config_json)

                with col3:
                    if st.button(
                        f"Editar", key=f"edit_rule_{rule.id}", use_container_width=True
                    ):
                        st.session_state[f"editing_rule_{rule.id}"] = True
                        st.rerun()

                    if st.button(
                        f"Excluir",
                        key=f"delete_rule_{rule.id}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        # Note: Implement delete functionality
                        st.warning("Função de exclusão de regras em desenvolvimento.")

    st.markdown("---")

    # Create new rule form
    st.subheader("➕ Criar Nova Regra de Alocação")

    with st.form("create_allocation_rule"):
        col1, col2 = st.columns(2)

        with col1:
            rule_description = st.text_area(
                "Descrição da Regra",
                placeholder="Ex: Priorizar salas com capacidade entre 80-90% das vagas",
                max_length=500,
            )

            rule_type = st.selectbox(
                "Tipo de Regra:",
                options=[
                    "Capacidade",
                    "Tipo de Sala",
                    "Professor Específico",
                    "Disciplina Específica",
                    "Andar Preferencial",
                ],
                help="Selecione o tipo de regra de alocação",
            )

            priority = st.number_input(
                "Prioridade",
                min_value=1,
                max_value=10,
                value=1,
                help="Prioridade da regra (1 = mais alta, 10 = mais baixa)",
            )

        with col2:
            # Create sample configuration based on rule type
            sample_configs = {
                "Capacidade": '{"min_utilization": 0.8, "max_utilization": 0.9, "penalty_excess": 20}',
                "Tipo de Sala": '{"mapping": {"FUP": "sala_de_aula", "LAB": "laboratorio"}}',
                "Professor Específico": '{"joao.silva": {"sala_preferida": "Sala 101"}}',
                "Disciplina Específica": '{"FUP0001": {"tipo_sala": "laboratório"}}',
                "Andar Preferencial": '{"prefer_térreo": true, "penalty_andar": 10}',
            }

            config_json = st.text_area(
                "Configuração (JSON)",
                value=sample_configs.get(rule_type, "{}"),
                help="Configuração em formato JSON",
                height=150,
            )

        st.markdown("---")

        submitted = st.form_submit_button(
            "Criar Regra", type="primary", use_container_width=True
        )

        if submitted:
            if not rule_description:
                st.error("❌ Descrição da regra é obrigatória.")
                return

            # Create rule
            new_rule = AllocationService.create_allocation_rule(
                descricao=rule_description,
                tipo_regra=rule_type,
                config_json=config_json,
                prioridade=priority,
            )

            if new_rule:
                st.success(f"✅ Regra '{rule_description}' criada com sucesso!")
                st.rerun()
            else:
                st.error("❌ Falha ao criar regra. Verifique os dados.")


def render_edit_allocation_form(allocation, semestre_id: int):
    """Render edit allocation form"""
    st.subheader(f"✏️ Editar Alocação - ID: {allocation.id}")

    with st.form(f"edit_allocation_form_{allocation.id}"):
        # Get current allocation details
        from database import DatabaseSession, Demanda, Sala

        with DatabaseSession() as session:
            demanda = (
                session.query(Demanda)
                .filter(Demanda.id == allocation.demanda_id)
                .first()
            )
            room = session.query(Sala).filter(Sala.id == allocation.sala_id).first()

        if not demanda or not room:
            st.error("Dados da alocação não encontrados.")
            return

        # Get available rooms and time blocks
        from database import DatabaseSession, DiaSemana, HorarioBloco

        with DatabaseSession() as session:
            dias_semana = session.query(DiaSemana).all()
            horarios = session.query(HorarioBloco).all()

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Informações da Demanda:**")
            st.write(
                f"- **Disciplina:** {demanda.codigo_disciplina} - {demanda.nome_disciplina}"
            )
            st.write(f"- **Professor:** {demanda.professores_disciplina}")
            st.write(f"- **Turma:** {demanda.turma_disciplina}")
            st.write(f"- **Vagas:** {demanda.vagas_disciplina}")
            st.write(f"- **Horário SIGAA:** {demanda.horario_sigaa_bruto}")

        with col2:
            # Room selection
            available_rooms = InventoryService.get_all_salas()
            room_options = {
                f"{room.nome} (Cap: {room.capacidade})": room.id
                for room in available_rooms
            }

            selected_room = st.selectbox(
                "Nova Sala:",
                options=list(room_options.keys()),
                index=(
                    list(room_options.values()).index(allocation.sala_id)
                    if allocation.sala_id in room_options.values()
                    else 0
                ),
                help="Selecione a nova sala para esta alocação",
            )

            new_room_id = room_options[selected_room]

            # Time block selection
            dia_options = {f"{dia.nome}": dia.id_sigaa for dia in dias_semana}
            selected_dia = st.selectbox(
                "Dia da Semana:",
                options=list(dia_options.keys()),
                index=(
                    list(dia_options.values()).index(allocation.dia_semana_id)
                    if allocation.dia_semana_id in dia_options.values()
                    else 0
                ),
                help="Selecione o dia da semana",
            )

            new_dia_id = dia_options[selected_dia]

            time_options = {
                f"{bloco.codigo_bloco} ({bloco.horario_inicio.strftime('%H:%M')} - {bloco.horario_fim.strftime('%H:%M')})": bloco.codigo_bloco
                for bloco in horarios
            }
            selected_time = st.selectbox(
                "Bloco de Tempo:",
                options=list(time_options.keys()),
                index=(
                    list(time_options.values()).index(allocation.codigo_bloco)
                    if allocation.codigo_bloco in time_options.values()
                    else 0
                ),
                help="Selecione o bloco de tempo",
            )

            new_bloco = time_options[selected_time].split(" ")[0]

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("💾 Salvar Alterações", type="primary")

        with col2:
            if st.form_submit_button("❌ Cancelar", type="secondary"):
                # Clear editing state
                for key in list(st.session_state.keys()):
                    if key.startswith("editing_allocation_"):
                        del st.session_state[key]
                st.rerun()

        if submitted:
            # Validate inputs
            try:
                # Remove old allocation
                AllocationService.remove_allocation(allocation.id)

                # Create new allocation
                new_allocation = AllocationService.allocate_room(
                    demanda_id=allocation.demanda_id,
                    sala_id=new_room_id,
                    dia_semana_id=new_dia_id,
                    codigo_bloco=new_bloco,
                )

                if new_allocation:
                    st.success("✅ Alocação atualizada com sucesso!")
                    # Clear editing state
                    for key in list(st.session_state.keys()):
                        if key.startswith("editing_allocation_"):
                            del st.session_state[key]
                    st.rerun()
                else:
                    st.error("❌ Falha ao atualizar alocação.")
            except Exception as e:
                st.error(f"❌ Erro ao atualizar alocação: {e}")


def render_edit_rule_form(rule_id: int):
    """Render edit rule form"""
    st.subheader(f"✏️ Editar Regra de Alocação - ID: {rule_id}")

    # Get current rule
    rules = AllocationService.get_allocation_rules()
    current_rule = next((r for r in rules if r.id == rule_id), None)

    if not current_rule:
        st.error("Regra não encontrada.")
        return

    with st.form(f"edit_rule_form_{rule_id}"):
        col1, col2 = st.columns(2)

        with col1:
            description = st.text_area(
                "Descrição da Regra", value=current_rule.descricao, max_length=500
            )

            rule_type = st.selectbox(
                "Tipo de Regra:",
                options=[
                    "Capacidade",
                    "Tipo de Sala",
                    "Professor Específico",
                    "Disciplina Específica",
                    "Andar Preferencial",
                ],
                index=(
                    [
                        "Capacidade",
                        "Tipo de Sala",
                        "Professor Específico",
                        "Disciplina Específica",
                        "Andar Preferencial",
                    ].index(current_rule.tipo_regra)
                    if current_rule.tipo_regra
                    in [
                        "Capacidade",
                        "Tipo de Sala",
                        "Professor Específico",
                        "Disciplina Específica",
                        "Andar Preferencial",
                    ]
                    else 0
                ),
            )

            priority = st.number_input(
                "Prioridade",
                min_value=1,
                max_value=10,
                value=current_rule.prioridade,
                help="Prioridade da regra (1 = mais alta, 10 = mais baixa)",
            )

        with col2:
            config_json = st.text_area(
                "Configuração (JSON)", value=current_rule.config_json, height=150
            )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("💾 Salvar Alterações", type="primary")

        with col2:
            if st.form_submit_button("❌ Cancelar", type="secondary"):
                # Clear editing state
                if f"editing_rule_{rule_id}" in st.session_state:
                    del st.session_state[f"editing_rule_{rule_id}"]
                st.rerun()

        if submitted:
            # Update rule (Note: Implement update functionality in service)
            st.info("Função de atualização de regras em desenvolvimento.")
            st.info("Por enquanto, delete a regra existente e crie uma nova.")


def main():
    """Main entry point for the allocations page"""
    render_alocacoes_page()


if __name__ == "__main__":
    main()
