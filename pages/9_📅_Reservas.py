"""
Room Reservations Page

Display and manage sporadic/recurrent room reservations with calendar-like interface.
Supports recurring reservations using Parent/Instance design pattern.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple, Optional
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
from src.utils.cache_helpers import (
    get_predio_options,
    get_tipo_sala_options,
    get_sigaa_parser,
)
from pages.components.ui import page_footer

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Reservas - Ensalamento",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Display any session feedback
display_session_feedback("reservas_feedback")
display_session_feedback("reservas_crud")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Get cached SIGAA parser singleton
_sigaa_parser = None


def get_parser():
    """Get cached SIGAA parser instance (singleton)"""
    global _sigaa_parser
    if _sigaa_parser is None:
        _sigaa_parser = get_sigaa_parser()
    return _sigaa_parser


# Define the canonical block order from SIGAA parser (single source of truth)
# This maintains the insertion order from MAP_SCHEDULE_TIMES (Python 3.7+ dict ordering)
def get_canonical_block_order() -> List[str]:
    """Get the canonical block order from SIGAA parser"""
    parser = get_parser()
    return list(parser.MAP_SCHEDULE_TIMES.keys())


# Cache the canonical order at module level for performance
CANONICAL_BLOCK_ORDER = get_canonical_block_order()

# Create a mapping of block code to its position in the canonical order
BLOCK_POSITION_MAP = {block: idx for idx, block in enumerate(CANONICAL_BLOCK_ORDER)}


def get_bloco_horario(bloco_codigo: str) -> str:
    """Get time range for a block code using SIGAA parser"""
    parser = get_parser()
    schedule_times = parser.MAP_SCHEDULE_TIMES

    if bloco_codigo not in schedule_times:
        return "N/A"

    times = schedule_times[bloco_codigo]
    return f"{times['inicio']}-{times['fim']}"


def get_blocos_disponiveis() -> List[str]:
    """Get list of available blocks in canonical order (DRY - from SIGAA parser)"""
    return CANONICAL_BLOCK_ORDER.copy()


def are_blocks_adjacent(bloco1: str, bloco2: str) -> bool:
    """
    Check if two blocks are adjacent in the canonical block order.

    Adjacent means they follow the canonical order without skips:
    M1->M2->M3->M4->M5->T1->T2->T3->T4->T5->T6->N1->N2->N3->N4

    Args:
        bloco1: First block code (e.g., "M1")
        bloco2: Second block code (e.g., "M2")

    Returns:
        True if bloco2 immediately follows bloco1 in canonical order
    """
    if bloco1 not in BLOCK_POSITION_MAP or bloco2 not in BLOCK_POSITION_MAP:
        return False

    pos1 = BLOCK_POSITION_MAP[bloco1]
    pos2 = BLOCK_POSITION_MAP[bloco2]

    return pos2 == pos1 + 1


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


def merge_adjacent_time_blocks(data_display: List[Dict]) -> List[Dict]:
    """
    Merge adjacent time blocks for the same reservation on the same date.

    Groups occurrences by (data_reserva, sala_codigo, titulo_evento) and merges
    consecutive time blocks into a single row showing the full time range.

    Adjacency is determined by the canonical block order:
    M1->M2->M3->M4->M5->T1->T2->T3->T4->T5->T6->N1->N2->N3->N4

    Blocks are adjacent if they follow this order without skips, regardless of time.

    Example:
        Input: [
            {"data_reserva": "2025-01-15", "horario": "08:00-08:55", "titulo_evento": "Reunião", "codigo_bloco": "M1", ...},
            {"data_reserva": "2025-01-15", "horario": "08:55-09:50", "titulo_evento": "Reunião", "codigo_bloco": "M2", ...},
            {"data_reserva": "2025-01-15", "horario": "10:00-10:55", "titulo_evento": "Reunião", "codigo_bloco": "M3", ...},
        ]
        Output: [
            {"data_reserva": "2025-01-15", "horario": "08:00-10:55", "titulo_evento": "Reunião", "blocos_count": 3, "blocos_detalhes": "M1, M2, M3", ...},
        ]
    """
    from collections import defaultdict

    # Group by (data_reserva, sala_codigo, titulo_evento)
    grouped = defaultdict(list)
    for row in data_display:
        key = (row["data_reserva"], row["sala_codigo"], row["titulo_evento"])
        grouped[key].append(row)

    merged_rows = []

    for group_rows in grouped.values():
        if len(group_rows) == 1:
            # Single block - no merging needed
            row = group_rows[0].copy()
            row["blocos_count"] = None
            row["blocos_detalhes"] = None
            merged_rows.append(row)
        else:
            # Multiple blocks - sort by canonical block order for proper detection
            sorted_rows = sorted(
                group_rows,
                key=lambda x: BLOCK_POSITION_MAP.get(
                    x.get("codigo_bloco", ""), float("inf")
                ),
            )

            # Group adjacent blocks based on canonical order
            merged = []
            current_group = [sorted_rows[0]]

            for i in range(1, len(sorted_rows)):
                curr_row = sorted_rows[i]
                prev_row = current_group[-1]

                # Check if blocks are adjacent in canonical order
                prev_bloco = prev_row.get("codigo_bloco", "")
                curr_bloco = curr_row.get("codigo_bloco", "")

                if are_blocks_adjacent(prev_bloco, curr_bloco):
                    # Adjacent blocks - add to current group
                    current_group.append(curr_row)
                else:
                    # Gap found - finalize current group and start new one
                    merged.append(current_group)
                    current_group = [curr_row]

            # Don't forget the last group
            merged.append(current_group)

            # Convert each group to a single merged row
            for group in merged:
                base_row = group[0].copy()

                # Get time range from first and last blocks in group
                first_time = base_row["horario"].split("-")[0]
                last_time = group[-1]["horario"].split("-")[1]
                base_row["horario"] = f"{first_time}-{last_time}"

                # Add block count if multiple blocks were merged
                if len(group) > 1:
                    base_row["blocos_count"] = len(group)
                    # Show which blocks were merged (e.g., "M1, M2, M3")
                    blocos_merged = ", ".join(
                        [row.get("codigo_bloco", "?") for row in group]
                    )
                    base_row["blocos_detalhes"] = blocos_merged
                else:
                    base_row["blocos_count"] = None
                    base_row["blocos_detalhes"] = None

                merged_rows.append(base_row)

    return sorted(
        merged_rows,
        key=lambda x: (
            x["data_reserva"],
            BLOCK_POSITION_MAP.get(x.get("codigo_bloco", ""), float("inf")),
        ),
    )


def create_reservations_editor(data: List[Dict]) -> None:
    """Create st.data_editor for reservations display with merged time blocks and CRUD operations"""
    if not data:
        st.info("Nenhuma reserva encontrada para os filtros selecionados.")
        return

    # Create a copy of data for display with hidden IDs for CRUD operations
    data_for_display = []
    for row in data:
        display_row = row.copy()

        # Format horario column to show merged block count if applicable
        if pd.notna(row.get("blocos_count")) and row["blocos_count"] is not None:
            blocos_info = f"{row['horario']} ({row['blocos_count']} blocos)"
            display_row["horario_display"] = blocos_info
        else:
            display_row["horario_display"] = row["horario"]

        # Add evento_id for tracking which ReservaEvento this corresponds to
        # This is needed because merged rows represent multiple occurrences but we edit the parent event
        display_row["evento_id"] = row.get("evento_id", None)

        data_for_display.append(display_row)

    df = pd.DataFrame(data_for_display)

    # Reorder columns for better display
    desired_column_order = [
        "data_reserva",
        "horario_display",
        "sala_codigo",
        "sala_descricao",
        "predio_nome",
        "titulo_evento",
        "padrao_recorrencia",
        "nome_solicitante",
        "nome_responsavel",
        "evento_id",  # Hidden column
        "horario",  # Hidden column
        "blocos_count",  # Hidden column
        "blocos_detalhes",  # Hidden column
        "codigo_bloco",  # Hidden column
    ]

    df = df[desired_column_order]

    st.info(
        """
        ℹ️ Edite os dados diretamente na tabela abaixo.
        - Para **excluir** reservas, selecione a linha correspondente clicando na primeira coluna e, em seguida, remova a linha clicando no ícone 🗑️ no canto superior direito da tabela.
        - Para **alterar** dados (evento, solicitante, responsável), dê um clique duplo na célula da tabela. As edições serão salvas automaticamente.
        - Não é possível adicionar novas reservas aqui. Use a aba **➕Nova Reserva** para isso.
        """
    )

    # Use st.data_editor with num_rows="dynamic" but no additions allowed
    # We set num_rows="dynamic" but will prevent additions in the logic below
    edited_df = st.data_editor(
        df,
        column_config={
            "evento_id": None,  # Hide the internal evento_id column
            "data_reserva": st.column_config.TextColumn(
                "Data", disabled=True, help="Data da reserva (não editável)"
            ),
            "horario_display": st.column_config.TextColumn(
                "Horário", disabled=True, help="Horário da reserva (não editável)"
            ),
            "sala_codigo": st.column_config.TextColumn(
                "Sala", disabled=True, help="Sala da reserva (não editável)"
            ),
            "sala_descricao": st.column_config.TextColumn(
                "Descrição", disabled=True, help="Descrição da sala (não editável)"
            ),
            "predio_nome": st.column_config.TextColumn(
                "Prédio", disabled=True, help="Prédio da sala (não editável)"
            ),
            "titulo_evento": st.column_config.TextColumn(
                "Evento", help="Título do evento"
            ),
            "padrao_recorrencia": st.column_config.TextColumn(
                "Recorrência",
                disabled=True,
                help="Padrão de recorrência (não editável)",
            ),
            "nome_solicitante": st.column_config.TextColumn(
                "Solicitante", help="Nome do solicitante"
            ),
            "nome_responsavel": st.column_config.TextColumn(
                "Responsável", help="Nome do responsável (opcional)"
            ),
            # Hide internal merging columns
            "horario": None,
            "blocos_count": None,
            "blocos_detalhes": None,
            "codigo_bloco": None,
        },
        hide_index=True,
        num_rows="dynamic",
        key="reservas_editor",
    )

    # Process deletions and updates in batch
    if edited_df is not None:
        # Check for deletions (comparing row counts)
        if len(edited_df) < len(df):
            # Handle deletions - find which events are missing
            original_eventos = df.dropna(subset=["evento_id"])["evento_id"].unique()
            edited_eventos = edited_df.dropna(subset=["evento_id"])[
                "evento_id"
            ].unique()
            deleted_eventos = set(original_eventos) - set(edited_eventos)

            if deleted_eventos:
                st.write(
                    f"DEBUG: Attempting to delete eventos: {deleted_eventos}"
                )  # Debug output
                try:
                    with get_db_session() as session:
                        evento_repo = ReservaEventoRepository(session)
                        deleted_count = 0
                        for evento_id in deleted_eventos:
                            result = evento_repo.delete(int(evento_id))
                            st.write(
                                f"DEBUG: Delete event {evento_id}: {result}"
                            )  # Debug output
                            if result:
                                deleted_count += 1

                        if deleted_count > 0:
                            st.write(
                                f"DEBUG: Successfully deleted {deleted_count} events"
                            )  # Debug output
                            set_session_feedback(
                                "reservas_crud",
                                True,
                                f"{deleted_count} reserva(s) excluída(s) com sucesso!",
                            )
                            st.rerun()
                        else:
                            st.write(
                                f"DEBUG: No events were actually deleted"
                            )  # Debug output
                except Exception as e:
                    st.write(
                        f"DEBUG: Exception during deletion: {str(e)}"
                    )  # Debug output
                    set_session_feedback(
                        "reservas_crud",
                        False,
                        f"Erro ao excluir reserva(s): {str(e)}",
                    )

        # Check for field updates (same number of rows, but changed data)
        elif len(edited_df) == len(df):
            changes_made = False
            errors_occurred = False
            updated_eventos = set()  # Track which eventos we've already updated

            try:
                with get_db_session() as session:
                    evento_repo = ReservaEventoRepository(session)

                    for idx, edited_row in edited_df.iterrows():
                        if idx < len(df):
                            original_row = df.iloc[idx]

                            evento_id = edited_row.get("evento_id")
                            if pd.isna(evento_id):
                                continue

                            # Skip if we've already updated this event
                            if evento_id in updated_eventos:
                                continue

                            # Check for changes in editable fields
                            titulo_changed = (
                                edited_row["titulo_evento"]
                                != original_row["titulo_evento"]
                            )
                            solicitante_changed = (
                                edited_row["nome_solicitante"]
                                != original_row["nome_solicitante"]
                            )
                            responsavel_changed = (
                                edited_row["nome_responsavel"]
                                != original_row["nome_responsavel"]
                            )

                            if (
                                titulo_changed
                                or solicitante_changed
                                or responsavel_changed
                            ):
                                # Mark this event as being updated
                                updated_eventos.add(evento_id)

                                # Validate data
                                titulo = str(edited_row["titulo_evento"]).strip()
                                solicitante = str(
                                    edited_row["nome_solicitante"]
                                ).strip()
                                responsavel = (
                                    str(edited_row["nome_responsavel"]).strip()
                                    if pd.notna(edited_row["nome_responsavel"])
                                    else None
                                )

                                if not titulo:
                                    set_session_feedback(
                                        "reservas_crud",
                                        False,
                                        "O título do evento é obrigatório",
                                    )
                                    errors_occurred = True
                                    continue

                                if not solicitante:
                                    set_session_feedback(
                                        "reservas_crud",
                                        False,
                                        "O nome do solicitante é obrigatório",
                                    )
                                    errors_occurred = True
                                    continue

                                # Validate full names
                                for field_name, value in [
                                    ("solicitante", solicitante),
                                    ("responsavel", responsavel),
                                ]:
                                    if value:
                                        parts = value.split()
                                        if len(parts) < 2:
                                            set_session_feedback(
                                                "reservas_crud",
                                                False,
                                                f"Campo '{field_name}' deve conter nome completo (nome + sobrenome)",
                                            )
                                            errors_occurred = True
                                            continue
                                        elif any(len(part) < 2 for part in parts):
                                            set_session_feedback(
                                                "reservas_crud",
                                                False,
                                                f"Campo '{field_name}' deve ter palavras com pelo menos 2 caracteres",
                                            )
                                            errors_occurred = True
                                            continue

                                # Create update DTO and call repository
                                from src.schemas.allocation import ReservaEventoUpdate

                                update_dto = ReservaEventoUpdate(
                                    titulo_evento=titulo,
                                    nome_solicitante=solicitante,
                                    nome_responsavel=responsavel,
                                )

                                result = evento_repo.update(int(evento_id), update_dto)
                                if result:
                                    set_session_feedback(
                                        "reservas_crud",
                                        True,
                                        f"Reserva '{titulo}' atualizada com sucesso!",
                                    )
                                    changes_made = True
                                else:
                                    set_session_feedback(
                                        "reservas_crud",
                                        False,
                                        f"Erro ao atualizar reserva de ID {evento_id}",
                                    )
                                    errors_occurred = True

                if changes_made:
                    st.rerun()
                # If only errors occurred, do NOT rerun so user can fix values in-place.

            except Exception as e:
                set_session_feedback(
                    "reservas_crud",
                    False,
                    f"Erro inesperado ao processar edições: {str(e)}",
                )


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

st.title("📅 Reservas de Salas")
st.markdown("Crie, visualize e gerencie reservas esporádicas e recorrentes de salas.")

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

    # Load available rooms with building info for both display and form
    salas_com_predio = sala_repo.get_with_predio_info()

    # Create room options for selectbox - use sala/predio objects
    sala_options = {}
    for item in salas_com_predio:
        sala = item["sala"]
        predio = item["predio"]
        predio_nome = predio.nome if predio else "N/A"
        sala_display = f"{sala.nome}: {sala.descricao}" if sala.descricao else sala.nome
        sala_options[sala.id] = f"{sala_display} ({predio_nome})"

# ============================================================================
# FILTERS
# ============================================================================

# Load ALL possible filter data across all reservations first
ocorrencias = ocorrencia_repo.get_ocorrencias_by_date_range(
    datetime.now().date() - timedelta(days=365),  # Load from past year
    datetime.now().date() + timedelta(days=365),  # Load to future year
    room_ids=None,  # Load all rooms
)

# Extract unique values for filters
salas_unicas = set()
predios_unicos = set()
for ocorrencia in ocorrencias:
    evento = ocorrencia.evento
    sala = evento.sala
    salas_unicas.add(f"{sala.nome}: {sala.descricao}" if sala.descricao else sala.nome)
    if sala.predio:
        predios_unicos.add(sala.predio.nome)

salas_unicas = sorted(list(salas_unicas))
predios_unicos = sorted(list(predios_unicos))

# Extract event titles
eventos_unicos = set()
for ocorrencia in ocorrencias:
    evento = ocorrencia.evento
    eventos_unicos.add(evento.titulo_evento)

eventos_unicos = sorted(list(eventos_unicos))

# ============================================================================
# TABS
# ============================================================================

# Initialize active tab in session state
if "reservas_active_tab" not in st.session_state:
    st.session_state.reservas_active_tab = "📅 Visualizar Reservas"

# Create tab navigation with segmented control
selected_tab = st.segmented_control(
    "Navegação",
    options=["📅 Visualizar Reservas", "➕ Nova Reserva"],
    key="reservas_active_tab",
    label_visibility="collapsed",
)

if selected_tab == "📅 Visualizar Reservas":
    # Main filters section
    st.subheader("🔍 Filtrar Reservas Existentes")

    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input(
            "Data Inicial",
            value=datetime.now().date(),
            key="filtro_data_inicio",
            format="DD/MM/YYYY",
        )

    with col2:
        data_fim = st.date_input(
            "Data Final",
            value=datetime.now().date() + timedelta(days=30),
            key="filtro_data_fim",
            format="DD/MM/YYYY",
        )

    # Text search filter
    filtro_evento_texto = st.text_input("Buscar por Evento (título)")

    # Room filter
    filtro_sala = st.multiselect("Filtrar por Sala", options=salas_unicas)

    # Building filter
    filtro_predio = st.multiselect("Filtrar por Prédio", options=predios_unicos)
    # TAB 1: VISUALIZAR RESERVAS
    st.header("📅 Reservas Existentes")

    # Load filtered reservations
    try:
        ocorrencias = ocorrencia_repo.get_ocorrencias_by_date_range(
            data_inicio, data_fim, room_ids=None
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

            sala_display = (
                f"{sala.nome}: {sala.descricao}" if sala.descricao else sala.nome
            )

            data_display.append(
                {
                    "evento_id": evento.id,  # Add for CRUD tracking
                    "data_reserva": ocorrencia.data_reserva,  # Already a string in YYYY-MM-DD format
                    "horario": get_bloco_horario(ocorrencia.codigo_bloco),
                    "codigo_bloco": ocorrencia.codigo_bloco,  # Add for merging reference
                    "sala_codigo": sala.nome,
                    "sala_descricao": sala.descricao if sala.descricao else "",
                    "predio_nome": predio_nome,
                    "sala_display": sala_display,  # For filtering
                    "titulo_evento": evento.titulo_evento,
                    "padrao_recorrencia": format_recurrence_pattern(evento),
                    "nome_solicitante": evento.nome_solicitante,
                    "nome_responsavel": (
                        evento.nome_responsavel if evento.nome_responsavel else "-"
                    ),
                }
            )

        # Apply display filters before merging
        if filtro_evento_texto:
            term = filtro_evento_texto.lower()
            data_display = [
                row for row in data_display if term in row["titulo_evento"].lower()
            ]

        if filtro_sala:
            data_display = [
                row for row in data_display if row["sala_display"] in filtro_sala
            ]

        if filtro_predio:
            data_display = [
                row for row in data_display if row["predio_nome"] in filtro_predio
            ]

        # Merge adjacent time blocks for same reservation on same date
        data_display = merge_adjacent_time_blocks(data_display)

        create_reservations_editor(data_display)

        # Export options
        if data_display:
            col1, _ = st.columns(2)

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

    except Exception as e:
        # Use toast for runtime errors in viewing tab
        set_session_feedback(
            "reservas_feedback",
            success=False,
            message=f"Erro ao carregar reservas: {str(e)}",
            ttl=10,
        )
        # Still display inline for immediate visibility since this is in viewing tab
        st.error(f"❌ Erro ao carregar reservas: {str(e)}")

elif selected_tab == "➕ Nova Reserva":
    # TAB 2: NOVA RESERVA
    st.header("➕ Criar Nova Reserva")

    # Recurrence pattern selection OUTSIDE form for dynamic UI updates
    st.markdown("#### 🔄 Tipo de Recorrência")
    tipo_recorrencia = st.selectbox(
        "Como esta reserva será repetida? *",
        options=["unica", "diaria", "semanal", "mensal_dia", "mensal_posicao"],
        format_func=lambda x: {
            "unica": "Evento Único (uma só data)",
            "diaria": "Repetir Diariamente",
            "semanal": "Repetir Semanalmente",
            "mensal_dia": "Repetir Mensalmente (mesmo dia)",
            "mensal_posicao": "Repetir Mensalmente (semana específica)",
        }.get(x, x),
        key="tipo_recorrencia_selector",
        help="Define como a reserva será repetida ao longo do tempo",
    )

    # Show info box based on selection
    if tipo_recorrencia == "unica":
        st.info(
            "ℹ️ **Evento Único:** A reserva será criada apenas para a data inicial selecionada, sem repetições."
        )
    elif tipo_recorrencia == "diaria":
        st.info(
            "ℹ️ **Repetição Diária:** A reserva será repetida a cada X dias, até a data final."
        )
    elif tipo_recorrencia == "semanal":
        st.info(
            "ℹ️ **Repetição Semanal:** A reserva será repetida nos dias da semana selecionados, até a data final."
        )
    elif tipo_recorrencia == "mensal_dia":
        st.info(
            "ℹ️ **Repetição Mensal (mesmo dia):** A reserva será repetida todo mês no mesmo dia (ex: dia 15), até a data final."
        )
    elif tipo_recorrencia == "mensal_posicao":
        st.info(
            "ℹ️ **Repetição Mensal (semana específica):** A reserva será repetida na mesma semana do mês (ex: toda 2ª segunda-feira), até a data final."
        )

    with st.form("form_nova_reserva"):
        st.markdown("#### 📝 Informações do Evento")

        col1, col2 = st.columns(2)

        with col1:
            titulo_evento = st.text_input(
                "Título do Evento *",
                placeholder="Ex: Reunião de Departamento",
                key="form_titulo",
                help="Título descritivo para identificar a reserva",
            )

            # Required field: solicitante
            nome_solicitante = st.text_input(
                "Nome do Solicitante *",
                placeholder="Ex: João Silva Santos",
                key="form_solicitante",
                help="Nome completo de quem está solicitando a reserva",
            )

            # Optional field: responsavel
            nome_responsavel = st.text_input(
                "Nome do Responsável (opcional)",
                placeholder="Ex: Maria Oliveira Costa",
                key="form_responsavel",
                help="Nome completo do responsável pelo evento (opcional)",
            )

            if sala_options:
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
                help="Data da primeira ocorrência da reserva",
                format="DD/MM/YYYY",
            )

        # Time blocks selection
        st.markdown("#### ⏰ Blocos de Horário *")
        st.caption("Selecione um ou mais horários para a reserva")
        blocos_disponiveis = get_blocos_disponiveis()

        cols = st.columns(5)
        blocos_selecionados = []

        for i, bloco in enumerate(blocos_disponiveis):
            with cols[i % 5]:
                if st.checkbox(f"{get_bloco_horario(bloco)}", key=f"bloco_{bloco}"):
                    blocos_selecionados.append(bloco)

        # Additional recurrence options
        regra_json = None
        data_fim_evento = None

        st.markdown("---")
        st.markdown("#### 📆 Configuração de Recorrência")

        if tipo_recorrencia == "unica":
            regra_json = '{"tipo": "unica"}'

        elif tipo_recorrencia == "diaria":
            col_int, col_fim = st.columns(2)
            with col_int:
                intervalo_dias = st.number_input(
                    "Repetir a cada (dias) *",
                    min_value=1,
                    max_value=30,
                    value=1,
                    key="form_intervalo_dias",
                    help="Intervalo em dias entre cada reserva",
                )
            with col_fim:
                data_fim_evento = st.date_input(
                    "Data Final *",
                    value=data_inicio_evento + timedelta(days=30),
                    min_value=data_inicio_evento + timedelta(days=1),
                    max_value=data_inicio_evento + timedelta(days=365),
                    key="form_data_fim_diaria",
                    help="Última data possível para repetição (máximo 1 ano)",
                    format="DD/MM/YYYY",
                )
            st.caption(
                f"📅 Exemplo: Repetir a cada {intervalo_dias} dia(s) de {data_inicio_evento.strftime('%d/%m/%Y')} até {data_fim_evento.strftime('%d/%m/%Y')}"
            )
            regra_json = f'{{"tipo": "diaria", "intervalo": {intervalo_dias}, "fim": "{data_fim_evento}"}}'

        elif tipo_recorrencia == "semanal":
            dias_semana_opcoes = {
                2: "Segunda-feira",
                3: "Terça-feira",
                4: "Quarta-feira",
                5: "Quinta-feira",
                6: "Sexta-feira",
                7: "Sábado",
            }
            col_dias, col_fim = st.columns(2)
            with col_dias:
                dias_selecionados = st.multiselect(
                    "Dias da Semana *",
                    options=list(dias_semana_opcoes.keys()),
                    format_func=lambda x: dias_semana_opcoes.get(x, ""),
                    default=(
                        [data_inicio_evento.isoweekday() + 1]
                        if data_inicio_evento.isoweekday() < 6
                        else [2]
                    ),
                    key="form_dias_semana",
                    help="Selecione os dias da semana em que a reserva se repetirá",
                )
            with col_fim:
                data_fim_evento = st.date_input(
                    "Data Final *",
                    value=data_inicio_evento + timedelta(days=90),
                    min_value=data_inicio_evento + timedelta(days=1),
                    max_value=data_inicio_evento + timedelta(days=365),
                    key="form_data_fim_semanal",
                    help="Última data possível para repetição (máximo 1 ano)",
                    format="DD/MM/YYYY",
                )
            if dias_selecionados:
                dias_str = ", ".join(
                    [dias_semana_opcoes[d][:3] for d in sorted(dias_selecionados)]
                )
                st.caption(
                    f"📅 Exemplo: Repetir toda(s) {dias_str} de {data_inicio_evento.strftime('%d/%m/%Y')} até {data_fim_evento.strftime('%d/%m/%Y')}"
                )
            dias_json = str(dias_selecionados).replace("'", "")
            regra_json = f'{{"tipo": "semanal", "dias": {dias_json}, "fim": "{data_fim_evento}"}}'

        elif tipo_recorrencia == "mensal_dia":
            col_dia, col_fim = st.columns(2)
            with col_dia:
                dia_mes = st.number_input(
                    "Dia do Mês *",
                    min_value=1,
                    max_value=31,
                    value=data_inicio_evento.day,
                    key="form_dia_mes",
                    help="Dia do mês em que a reserva se repetirá (ex: 15 = dia 15 de cada mês)",
                )
            with col_fim:
                data_fim_evento = st.date_input(
                    "Data Final *",
                    value=data_inicio_evento + timedelta(days=180),
                    min_value=data_inicio_evento + timedelta(days=1),
                    max_value=data_inicio_evento + timedelta(days=365),
                    key="form_data_fim_mensal_dia",
                    help="Última data possível para repetição (máximo 1 ano)",
                    format="DD/MM/YYYY",
                )
            st.caption(
                f"📅 Exemplo: Repetir todo dia {dia_mes} de cada mês, de {data_inicio_evento.strftime('%m/%Y')} até {data_fim_evento.strftime('%m/%Y')}"
            )
            regra_json = f'{{"tipo": "mensal", "dia_mes": {dia_mes}, "fim": "{data_fim_evento}"}}'

        elif tipo_recorrencia == "mensal_posicao":
            pos_map = {
                1: "Primeira",
                2: "Segunda",
                3: "Terceira",
                4: "Quarta",
                5: "Última",
            }
            dia_semana_map = {
                2: "Segunda-feira",
                3: "Terça-feira",
                4: "Quarta-feira",
                5: "Quinta-feira",
                6: "Sexta-feira",
                7: "Sábado",
            }
            col_pos, col_dia, col_fim = st.columns(3)
            with col_pos:
                posicao_selecionada = st.selectbox(
                    "Posição no Mês *",
                    options=list(pos_map.keys()),
                    format_func=lambda x: pos_map.get(x, ""),
                    index=0,
                    key="form_posicao",
                    help="Qual semana do mês (1ª, 2ª, 3ª, 4ª ou última)",
                )
            with col_dia:
                dia_semana_selecionado = st.selectbox(
                    "Dia da Semana *",
                    options=list(dia_semana_map.keys()),
                    format_func=lambda x: dia_semana_map.get(x, ""),
                    index=0,
                    key="form_dia_semana",
                    help="Dia da semana para a repetição",
                )
            with col_fim:
                data_fim_evento = st.date_input(
                    "Data Final *",
                    value=data_inicio_evento + timedelta(days=180),
                    min_value=data_inicio_evento + timedelta(days=1),
                    max_value=data_inicio_evento + timedelta(days=365),
                    key="form_data_fim_mensal_posicao",
                    help="Última data possível para repetição (máximo 1 ano)",
                    format="DD/MM/YYYY",
                )
            st.caption(
                f"📅 Exemplo: Repetir toda {pos_map[posicao_selecionada].lower()} {dia_semana_map[dia_semana_selecionado].lower()} do mês, de {data_inicio_evento.strftime('%m/%Y')} até {data_fim_evento.strftime('%m/%Y')}"
            )
            regra_json = f'{{"tipo": "mensal", "posicao": {posicao_selecionada}, "dia_semana": {dia_semana_selecionado}, "fim": "{data_fim_evento}"}}'

        # Submit button
        st.markdown("---")

        col_submit, _ = st.columns([1, 1])

        with col_submit:
            submit_button = st.form_submit_button(
                "✅ Criar Reserva", type="primary", use_container_width=True
            )

        # Form submission handling
        if submit_button:
            # ============================================================
            # VALIDATION
            # ============================================================
            validation_errors = []

            # Validate título
            if not titulo_evento.strip():
                validation_errors.append("• O título do evento é obrigatório.")

            # Validate nome_solicitante (required, full name)
            if not nome_solicitante.strip():
                validation_errors.append("• O nome do solicitante é obrigatório.")
            else:
                # Check if it's a valid full name (at least 2 words, each >= 2 chars)
                nome_parts = nome_solicitante.strip().split()
                if len(nome_parts) < 2:
                    validation_errors.append(
                        "• O nome do solicitante deve conter nome e sobrenome (mínimo 2 palavras)."
                    )
                elif any(len(part) < 2 for part in nome_parts):
                    validation_errors.append(
                        "• O nome do solicitante deve ter palavras com pelo menos 2 caracteres cada."
                    )
                elif not all(part.replace("-", "").isalpha() for part in nome_parts):
                    validation_errors.append(
                        "• O nome do solicitante deve conter apenas letras e hífens."
                    )

            # Validate nome_responsavel (optional, but if provided, must be full name)
            if nome_responsavel.strip():
                # Check if it's a valid full name (at least 2 words, each >= 2 chars)
                nome_parts = nome_responsavel.strip().split()
                if len(nome_parts) < 2:
                    validation_errors.append(
                        "• O nome do responsável deve conter nome e sobrenome (mínimo 2 palavras)."
                    )
                elif any(len(part) < 2 for part in nome_parts):
                    validation_errors.append(
                        "• O nome do responsável deve ter palavras com pelo menos 2 caracteres cada."
                    )
                elif not all(part.replace("-", "").isalpha() for part in nome_parts):
                    validation_errors.append(
                        "• O nome do responsável deve conter apenas letras e hífens."
                    )

            # Validate time blocks
            if not blocos_selecionados:
                validation_errors.append("• Selecione pelo menos um bloco de horário.")

            # Validate recurrence-specific fields
            if tipo_recorrencia == "semanal" and not dias_selecionados:
                validation_errors.append(
                    "• Selecione pelo menos um dia da semana para recorrência semanal."
                )

            # Validate end date for recurring events
            if tipo_recorrencia != "unica":
                if not data_fim_evento:
                    validation_errors.append(
                        "• A data final é obrigatória para eventos recorrentes."
                    )
                elif data_fim_evento <= data_inicio_evento:
                    validation_errors.append(
                        "• A data final deve ser posterior à data inicial."
                    )
                elif (data_fim_evento - data_inicio_evento).days > 365:
                    validation_errors.append(
                        "• O período máximo para recorrência é de 1 ano (365 dias)."
                    )

            # Display all validation errors
            if validation_errors:
                # Store validation errors in session feedback
                error_message = "\n".join(validation_errors)
                set_session_feedback(
                    "reservas_feedback",
                    success=False,
                    message=error_message,
                    ttl=10,
                )
                st.rerun()

            # ============================================================
            # CREATE RESERVATION
            # ============================================================
            try:
                evento_dto = ReservaEventoCreate(
                    sala_id=sala_id,
                    titulo_evento=titulo_evento.strip(),
                    username_criador=st.session_state.get("username", "unknown"),
                    nome_solicitante=nome_solicitante.strip(),
                    nome_responsavel=(
                        nome_responsavel.strip() if nome_responsavel.strip() else None
                    ),
                    regra_recorrencia_json=regra_json,
                )

                evento_criado, erros = reserva_service.criar_reserva_recorrente(
                    evento_dto=evento_dto,
                    blocos_selecionados=blocos_selecionados,
                    data_inicio=data_inicio_evento,
                )

                if evento_criado:
                    set_session_feedback(
                        "reservas_feedback",
                        success=True,
                        message=f"Reserva '{evento_criado.titulo_evento}' criada com sucesso!",
                        ttl=8,
                    )
                    st.rerun()
                else:
                    # Store creation errors in session feedback
                    error_list = "\n".join([f"• {erro}" for erro in erros])
                    set_session_feedback(
                        "reservas_feedback",
                        success=False,
                        message=f"Erros ao criar reserva:\n{error_list}",
                        ttl=10,
                    )
                    st.rerun()

            except Exception as e:
                # Store exception in session feedback
                set_session_feedback(
                    "reservas_feedback",
                    success=False,
                    message=f"Erro inesperado ao criar reserva: {str(e)}",
                    ttl=10,
                )
                st.rerun()

# ============================================================================
# FOOTER
# ============================================================================
page_footer.show()
