"""
Room Reservations Page

Display and manage sporadic/recurrent room reservations with calendar-like interface.
Supports recurring reservations using Parent/Instance design pattern.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple, Optional
from st_aggrid import AgGrid, GridOptionsBuilder
from pages.components.auth import initialize_page

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Reservas - Ensalamento",
    page_icon="📅",
    layout="wide",
    key_suffix="reservas",
):
    st.stop()

# ============================================================================
# IMPORTS
# ============================================================================

from src.config.database import get_db_session
from src.models.allocation import ReservaEvento, ReservaOcorrencia
from src.schemas.allocation import (
    ReservaEventoCreate,
    ReservaEventoUpdate,
    ReservaEventoRead,
    ReservaOcorrenciaRead,
    RegraUnica,
    RegraDiaria,
    RegraSemanal,
    RegraMensalDia,
    RegraMensalPosicao,
    RegraRecorrencia,
)
from src.repositories.reserva_evento import ReservaEventoRepository
from src.repositories.reserva_ocorrencia import ReservaOcorrenciaRepository
from src.repositories.sala import SalaRepository
from src.repositories.semestre import SemestreRepository
from src.repositories.alocacao import AlocacaoRepository
from src.services.reserva_evento_service import ReservaEventoService
from src.utils.ui_feedback import set_session_feedback, display_session_feedback
from src.utils.cache_helpers import get_predio_options, get_tipo_sala_options

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Reservas de Salas",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Display any session feedback
display_session_feedback("reservas_feedback")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def format_bloco_horario(bloco_codigo: str) -> str:
    """Format block code for display"""
    bloco_map = {
        "M1": "07:00-07:50",
        "M2": "07:50-08:40",
        "M3": "08:50-09:40",
        "M4": "09:40-10:30",
        "M5": "10:40-11:30",
        "T1": "11:30-12:20",
        "T2": "13:00-13:50",
        "T3": "13:50-14:40",
        "T4": "14:50-15:40",
        "T5": "15:40-16:30",
        "T6": "16:40-17:30",
        "N1": "17:30-18:20",
        "N2": "18:20-19:10",
        "N3": "19:20-20:10",
        "N4": "20:10-21:00",
    }
    return f"{bloco_codigo} ({bloco_map.get(bloco_codigo, 'N/A')})"


def format_recurrence_pattern(evento: ReservaEventoRead) -> str:
    """Format recurrence rule for display from JSON"""
    try:
        import json

        rule = json.loads(evento.regra_recorrencia_json)

        tipo = rule.get("tipo", "unica")
        if tipo == "unica":
            return "Único"
        elif tipo == "diaria":
            intervalo = rule.get("intervalo", 1)
            return f"Diário: {intervalo} dias"
        elif tipo == "semanal":
            dias_map = {
                2: "Seg",
                3: "Ter",
                4: "Qua",
                5: "Qui",
                6: "Sex",
                7: "Sáb",
                8: "Dom",
            }
            dias = [dias_map[d] for d in rule.get("dias", [])]
            return f"Semanal: {', '.join(dias)}"
        elif tipo == "mensal":
            if "dia_mes" in rule:
                return f"Mensal: Dia {rule['dia_mes']}"
            elif "posicao" in rule and "dia_semana" in rule:
                pos_map = {1: "1ª", 2: "2ª", 3: "3ª", 4: "4ª", 5: "Última"}
                dia_map = {
                    2: "Seg",
                    3: "Ter",
                    4: "Qua",
                    5: "Qui",
                    6: "Sex",
                    7: "Sáb",
                    8: "Dom",
                }
                return (
                    f"Mensal: {pos_map[rule['posicao']]} {dia_map[rule['dia_semana']]}"
                )

        return "Desconhecido"
    except (json.JSONDecodeError, KeyError):
        return "Desconhecido"


def create_reservations_grid(data: List[Dict]) -> None:
    """Create AgGrid for reservations display"""
    if not data:
        st.info("Nenhuma reserva encontrada para os filtros selecionados.")
        return

    df = pd.DataFrame(data)

    # Configure grid options
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        resizable=True,
        wrapHeaderText=True,
        autoHeaderHeight=True,
        filterable=True,
        sortable=True,
        editable=False,
    )

    # Column configurations
    gb.configure_column(
        "data_reserva",
        header_name="Data",
        cellRenderer="agDateCellRenderer",
        cellRendererParams={"format": "dd/MM/yyyy"},
        width=120,
    )
    gb.configure_column("horario", header_name="Horário", width=140)
    gb.configure_column("sala_codigo", header_name="Sala", width=100)
    gb.configure_column("predio_nome", header_name="Prédio", width=80)
    gb.configure_column(
        "titulo_evento", header_name="Evento", width=200, wrapText=True, autoHeight=True
    )
    gb.configure_column("padrao_recorrencia", header_name="Recorrência", width=150)
    gb.configure_column("criador", header_name="Criador", width=120)

    # Grid options
    grid_options = gb.build()
    grid_options.update(
        {
            "enableRangeSelection": True,
            "enableRangeHandle": True,
            "enableFillHandle": True,
            "enableCellChangeFlash": True,
            "suppressMovableColumns": True,
            "rowHeight": 40,
            "headerHeight": 45,
        }
    )

    # Render grid
    AgGrid(
        df,
        gridOptions=grid_options,
        height=400,
        width="100%",
        data_return_mode="AS_INPUT",
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        key="reservas_grid",
    )


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

st.title("📅 Reservas de Salas")
st.markdown(
    "Gerencie reservas esporádicas e recorrentes de salas com interface estilo calendário."
)

# Get current semester
with get_db_session() as session:
    from src.models.academic import Semestre

    semestre_repo = SemestreRepository(session)
    # Find active semester by checking status=True
    semestre_atual = session.query(Semestre).filter(Semestre.status == True).first()
    if not semestre_atual:
        st.error("❌ Nenhum semestre ativo encontrado. Contate o administrador.")
        st.stop()

    sala_repo = SalaRepository(session)
    evento_repo = ReservaEventoRepository(session)
    ocorrencia_repo = ReservaOcorrenciaRepository(session)
    reserva_service = ReservaEventoService(session)
    alocacao_repo = AlocacaoRepository(session)

# ============================================================================
# FILTERS
# ============================================================================

st.sidebar.markdown("### 📋 Filtros")

# Date range filter
with st.sidebar:
    data_inicio = st.date_input(
        "Data Inicial", value=datetime.now().date(), key="filtro_data_inicio"
    )

    data_fim = st.date_input(
        "Data Final",
        value=datetime.now().date() + timedelta(days=30),
        key="filtro_data_fim",
    )

    # Room filter
    salas_com_predio = sala_repo.get_with_predio_info()
    if salas_com_predio:
        sala_options = {
            item["sala"].id: f"{item['sala'].nome} ({item['predio'].nome})"
            for item in salas_com_predio
        }
        salas = [item["sala"] for item in salas_com_predio]
        sala_ids = st.multiselect(
            "Salas",
            options=list(sala_options.keys()),
            format_func=lambda x: sala_options.get(x, "N/A"),
            key="filtro_salas",
        )
    else:
        sala_ids = []
        st.warning("Nenhuma sala ativa encontrada.")

# ============================================================================
# TABS
# ============================================================================

tab1, tab2 = st.tabs(["📅 Visualizar Reservas", "➕ Nova Reserva"])

with tab1:
    st.header("📅 Reservas Existentes")

    # Load filtered reservations
    try:
        ocorrencias = ocorrencia_repo.get_ocorrencias_by_date_range(
            data_inicio, data_fim, sala_ids
        )

        # Format data for display
        data_display = []
        for ocorrencia in ocorrencias:
            evento = ocorrencia.evento
            sala = evento.sala

            # Get building info for display
            predio_info = next(
                (
                    item["predio"]
                    for item in salas_com_predio
                    if item["sala"].id == sala.id
                ),
                None,
            )
            predio_nome = predio_info.nome if predio_info else "N/A"

            data_display.append(
                {
                    "data_reserva": ocorrencia.data_reserva.strftime("%Y-%m-%d"),
                    "horario": format_bloco_horario(ocorrencia.codigo_bloco),
                    "sala_codigo": sala.nome,
                    "predio_nome": predio_nome,
                    "titulo_evento": evento.titulo_evento,
                    "padrao_recorrencia": format_recurrence_pattern(evento),
                    "criador": evento.username_criador,
                    "evento_id": evento.id,
                    "ocorrencia_id": ocorrencia.id,
                    "status": ocorrencia.status_excorrencia,
                }
            )

        # Sort by date and time
        data_display.sort(key=lambda x: (x["data_reserva"], x["horario"]))

        create_reservations_grid(data_display)

        # Export options
        if data_display:
            st.markdown("### 📊 Exportar Dados")
            col1, col2 = st.columns(2)

            with col1:
                df_export = pd.DataFrame(data_display)
                csv = df_export.to_csv(index=False, sep=";")
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"reservas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_csv",
                )

            with col2:
                excel_df = df_export.drop(columns=["evento_id", "ocorrencia_id"])
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_df.to_excel(index=False, engine="openpyxl"),
                    file_name=f"reservas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel",
                )

    except Exception as e:
        st.error(f"❌ Erro ao carregar reservas: {str(e)}")

with tab2:
    st.header("➕ Criar Nova Reserva")

    with st.form("form_nova_reserva"):
        st.markdown("#### 📝 Informações do Evento")

        col1, col2 = st.columns(2)

        with col1:
            titulo_evento = st.text_input(
                "Título do Evento *",
                placeholder="Ex: Reunião de Departamento",
                key="form_titulo",
            )

            # Optional fields for external guests
            nome_solicitante = st.text_input(
                "Nome do Solicitante (opcional)",
                placeholder="Nome completo do solicitante externo",
                key="form_solicitante",
            )

            nome_responsavel = st.text_input(
                "Nome do Responsável (opcional)",
                placeholder="Nome do responsável pelo evento",
                key="form_responsavel",
            )

            if salas:
                sala_id = st.selectbox(
                    "Sala *",
                    options=list(sala_options.keys()),
                    format_func=lambda x: sala_options.get(x, "N/A"),
                    key="form_sala",
                )
            else:
                st.error("Nenhuma sala disponível para reserva.")
                st.stop()

        with col2:
            data_inicio_evento = st.date_input(
                "Data Inicial *",
                value=datetime.now().date(),
                min_value=datetime.now().date(),
                key="form_data_inicio",
            )

            # Recurrence pattern selection
            st.markdown("#### 🔄 Padrão de Recorrência")
            tipo_recorrencia = st.selectbox(
                "Tipo de Recorrência",
                options=["unica", "diaria", "semanal", "mensal_dia", "mensal_posicao"],
                format_func=lambda x: {
                    "unica": "Único",
                    "diaria": "Diária",
                    "semanal": "Semanal",
                    "mensal_dia": "Mensal (dia do mês)",
                    "mensal_posicao": "Mensal (posição na semana)",
                }.get(x, x),
                key="form_tipo_recorrencia",
            )

        # Time blocks selection
        st.markdown("#### ⏰ Blocos de Horário")
        blocos_disponiveis = [
            "M1",
            "M2",
            "M3",
            "M4",
            "M5",
            "T1",
            "T2",
            "T3",
            "T4",
            "T5",
            "T6",
            "N1",
            "N2",
            "N3",
            "N4",
        ]

        cols = st.columns(5)
        blocos_selecionados = []

        for i, bloco in enumerate(blocos_disponiveis):
            with cols[i % 5]:
                if st.checkbox(
                    f"{bloco} ({format_bloco_horario(bloco)})", key=f"bloco_{bloco}"
                ):
                    blocos_selecionados.append(bloco)

        # Additional recurrence options
        regra_json = None
        data_fim_evento = None

        if tipo_recorrencia == "unica":
            regra_json = '{"tipo": "unica"}'

        elif tipo_recorrencia == "diaria":
            st.markdown("#### 📅 Opções de Recorrência Diária")
            intervalo_dias = st.number_input(
                "Repetir a cada (dias)",
                min_value=1,
                max_value=30,
                value=1,
                key="form_intervalo_dias",
            )
            data_fim_evento = st.date_input(
                "Data Final",
                value=data_inicio_evento + timedelta(days=90),
                min_value=data_inicio_evento,
                key="form_data_fim_diaria",
            )
            regra_json = f'{{"tipo": "diaria", "intervalo": {intervalo_dias}, "fim": "{data_fim_evento}"}}'

        elif tipo_recorrencia == "semanal":
            st.markdown("#### 📅 Opções de Recorrência Semanal")
            dias_semana_opcoes = {
                2: "Segunda-feira",
                3: "Terça-feira",
                4: "Quarta-feira",
                5: "Quinta-feira",
                6: "Sexta-feira",
                7: "Sábado",
                8: "Domingo",
            }
            dias_selecionados = st.multiselect(
                "Dias da Semana",
                options=list(dias_semana_opcoes.keys()),
                format_func=lambda x: dias_semana_opcoes.get(x, ""),
                default=[2, 4, 6],  # Seg, Qua, Sex
                key="form_dias_semana",
            )
            data_fim_evento = st.date_input(
                "Data Final",
                value=data_inicio_evento + timedelta(days=90),
                min_value=data_inicio_evento,
                key="form_data_fim_semanal",
            )
            dias_json = str(dias_selecionados).replace("'", "")
            regra_json = f'{{"tipo": "semanal", "dias": {dias_json}, "fim": "{data_fim_evento}"}}'

        elif tipo_recorrencia == "mensal_dia":
            st.markdown("#### 📅 Opções de Recorrência Mensal")
            dia_mes = st.number_input(
                "Dia do Mês",
                min_value=1,
                max_value=31,
                value=data_inicio_evento.day,
                key="form_dia_mes",
            )
            data_fim_evento = st.date_input(
                "Data Final",
                value=data_inicio_evento + timedelta(days=365),
                min_value=data_inicio_evento,
                key="form_data_fim_mensal_dia",
            )
            regra_json = f'{{"tipo": "mensal", "dia_mes": {dia_mes}, "fim": "{data_fim_evento}"}}'

        elif tipo_recorrencia == "mensal_posicao":
            st.markdown("#### 📅 Opções de Recorrência Mensal")
            pos_map = {1: "1ª", 2: "2ª", 3: "3ª", 4: "4ª", 5: "Última"}
            posicao_selecionada = st.selectbox(
                "Posição no Mês",
                options=list(pos_map.keys()),
                format_func=lambda x: pos_map.get(x, ""),
                key="form_posicao",
            )
            dia_semana_map = {
                2: "Segunda-feira",
                3: "Terça-feira",
                4: "Quarta-feira",
                5: "Quinta-feira",
                6: "Sexta-feira",
                7: "Sábado",
                8: "Domingo",
            }
            dia_semana_selecionado = st.selectbox(
                "Dia da Semana",
                options=list(dia_semana_map.keys()),
                format_func=lambda x: dia_semana_map.get(x, ""),
                key="form_dia_semana",
            )
            data_fim_evento = st.date_input(
                "Data Final",
                value=data_inicio_evento + timedelta(days=365),
                min_value=data_inicio_evento,
                key="form_data_fim_mensal_posicao",
            )
            regra_json = f'{{"tipo": "mensal", "posicao": {posicao_selecionada}, "dia_semana": {dia_semana_selecionado}, "fim": "{data_fim_evento}"}}'

        # Submit button
        st.markdown("---")

        col_submit, col_cancel = st.columns([1, 1])

        with col_submit:
            submit_button = st.form_submit_button(
                "✅ Criar Reserva", type="primary", use_container_width=True
            )

        with col_cancel:
            cancel_button = st.form_submit_button(
                "❌ Cancelar", use_container_width=True
            )

        # Form submission handling
        if submit_button:
            # Validation
            if not titulo_evento.strip():
                st.error("❌ O título do evento é obrigatório.")
                st.stop()

            if not blocos_selecionados:
                st.error("❌ Selecione pelo menos um bloco de horário.")
                st.stop()

            if tipo_recorrencia != "unica":
                if data_fim_evento <= data_inicio_evento:
                    st.error("❌ A data final deve ser posterior à data inicial.")
                    st.stop()

                if (data_fim_evento - data_inicio_evento).days > 365:
                    st.error("❌ O período máximo para recorrência é de 1 ano.")
                    st.stop()

            # Create reservation
            try:
                evento_dto = ReservaEventoCreate(
                    sala_id=sala_id,
                    titulo_evento=titulo_evento.strip(),
                    username_criador=st.session_state.get("username", "unknown"),
                    nome_solicitante=(
                        nome_solicitante.strip() if nome_solicitante.strip() else None
                    ),
                    nome_responsavel=(
                        nome_responsavel.strip() if nome_responsavel.strip() else None
                    ),
                    regra_recorrencia_json=regra_json,
                    status="Aprovada",  # Default status
                )

                evento_criado, erros = reserva_service.criar_reserva_recorrente(
                    evento_dto=evento_dto,
                    blocos_selecionados=blocos_selecionados,
                    data_inicio=data_inicio_evento,
                    data_fim=data_fim_evento,
                )

                if evento_criado:
                    set_session_feedback(
                        "reservas_feedback",
                        success=True,
                        message=f"✅ Reserva '{evento_criado.titulo_evento}' criada com sucesso!",
                        ttl=8,
                    )
                    st.rerun()
                else:
                    st.error("❌ Erros ao criar reserva:")
                    for erro in erros:
                        st.error(f"• {erro}")

            except Exception as e:
                st.error(f"❌ Erro inesperado ao criar reserva: {str(e)}")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    f"<small>Semestre atual: {semestre_atual.nome} | "
    f"Sistema de Ensalamento FUP/UnB</small>",
    unsafe_allow_html=True,
)
