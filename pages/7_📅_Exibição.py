"""
Room Allocation Visualization Page

Display and manage semester allocations and reservations.

Route: /pages/6_📅_Ensalamento.py
URL: /Ensalamento
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple
from pages.components.auth import initialize_page

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Ensalamento - Sistema de Ensalamento FUP/UnB",
    page_icon="📅",
    layout="wide",
    key_suffix="ensalamento",
):
    st.stop()

# ============================================================================
# IMPORTS
# ============================================================================

from src.repositories.alocacao import AlocacaoRepository
from src.repositories.reserva import ReservaRepository
from src.repositories.sala import SalaRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.semestre import SemestreRepository
from src.repositories.dia_semana import DiaSemanaRepository
from src.repositories.horario_bloco import HorarioBlocoRepository
from src.config.database import get_db_session
from src.utils.ui_feedback import (
    display_session_feedback,
    set_session_feedback,
)
from src.models.inventory import Sala, Predio
from src.models.academic import Professor
from src.models.allocation import AlocacaoSemestral
from src.utils.cache_helpers import get_sigaa_parser, get_semester_options
from pages.components.ui import page_footer

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def combine_consecutive_blocks(blocks: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
    """
    Combine consecutive time blocks into consolidated schedules.

    Args:
        blocks: List of (codigo_bloco, dia_sigaa) tuples

    Returns:
        List of combined schedule dicts with start/end times
    """
    if not blocks:
        return []

    # Sort blocks by day and time
    blocks_sorted = sorted(
        blocks, key=lambda x: (x[1], x[0])
    )  # dia_sigaa, codigo_bloco

    parser = get_sigaa_parser()
    combined = []

    current_start = None
    current_end = None
    current_day = None
    current_start_code = None

    day_names = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}

    for bloco, dia_sigaa in blocks_sorted:
        try:
            # Get time info for this block
            bloco_info = parser.MAP_SCHEDULE_TIMES.get(bloco, {})
            start_time = bloco_info.get("inicio")
            end_time = bloco_info.get("fim")

            if not start_time or not end_time:
                continue

            if current_day is None:
                # Start new group
                current_day = dia_sigaa
                current_start_code = bloco
                current_start = start_time
                current_end = end_time
            elif current_day == dia_sigaa and current_end == start_time:
                # Extend current group (consecutive blocks)
                current_end = end_time
            else:
                # Close current group
                day_name = day_names.get(current_day, f"Dia {current_day}")
                combined.append(
                    {
                        "day": current_day,
                        "day_name": day_name,
                        "time": f"{current_start}-{current_end}",
                        "blocks": f"{current_start_code} até {bloco}",
                    }
                )

                # Start new group
                current_day = dia_sigaa
                current_start_code = bloco
                current_start = start_time
                current_end = end_time

        except Exception as e:
            # Skip problematic blocks
            continue

    # Close last group
    if current_day is not None:
        day_name = day_names.get(current_day, f"Dia {current_day}")
        combined.append(
            {
                "day": current_day,
                "day_name": day_name,
                "time": f"{current_start}-{current_end}",
                "blocks": current_start_code,
            }
        )

    return combined


def format_schedule_display(allocation_records: List[Dict[str, Any]]) -> str:
    """
    Format allocation records into human-readable schedule string.

    Args:
        allocation_records: List of allocation/reservation dicts

    Returns:
        Formatted schedule string
    """
    if not allocation_records:
        return "Nenhum horário agendado"

    schedule_parts = []

    for record in allocation_records:
        combined_schedules = combine_consecutive_blocks(record.get("blocks", []))
        if combined_schedules:
            for schedule in combined_schedules:
                schedule_parts.append(f"{schedule['day_name']} {schedule['time']}")

    return " • ".join(schedule_parts) if schedule_parts else "Nenhum horário agendado"


def create_room_schedule_grid(allocations: List[Any], room_name: str) -> pd.DataFrame:
    """
    Create a schedule grid DataFrame for a room.

    Args:
        allocations: List of allocation/reservation objects
        room_name: Name of the room

    Returns:
        DataFrame with time slots as index and days as columns
    """
    parser = get_sigaa_parser()

    # Get all unique time slots used in this room's allocations
    time_slots = set()
    schedule_data = {}

    # Weekdays mapping
    weekdays = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}

    # Initialize empty schedule
    for dia_id, dia_name in weekdays.items():
        schedule_data[dia_name] = {}

    # Populate schedule data
    for alloc in allocations:
        # Check if this is a reservation (dict) or allocation (object)
        if isinstance(alloc, dict) and alloc.get("type") == "reservation":
            # Handle reservation
            bloco = alloc["codigo_bloco"]
            titulo = alloc["titulo"]
            solicitante = alloc["solicitante"]

            # For now, put all reservations in a separate section
            # TODO: Properly map reservation dates to weekdays
            dia_name = "RESERVAS"
            if dia_name not in schedule_data:
                schedule_data[dia_name] = {}

            schedule_data[dia_name][bloco] = f"🎯 {titulo} ({solicitante})"
            time_slots.add(bloco)
        else:
            # Handle regular allocation
            dia_id = alloc.dia_semana_id
            bloco = alloc.codigo_bloco

            if dia_id not in weekdays:
                continue

            dia_name = weekdays[dia_id]

            # Get course information
            codigo_disciplina = (
                alloc.demanda.codigo_disciplina if alloc.demanda is not None else "N/A"
            )
            nome_disciplina = (
                alloc.demanda.nome_disciplina if alloc.demanda is not None else ""
            )
            disciplina = (
                f"{codigo_disciplina} - {nome_disciplina}"
                if nome_disciplina
                else codigo_disciplina
            )
            turma = (
                alloc.demanda.turma_disciplina if alloc.demanda is not None else "N/A"
            )
            professor = (
                alloc.demanda.professores_disciplina
                if alloc.demanda is not None
                else "N/A"
            )

            schedule_data[dia_name][bloco] = f"{disciplina}\n{professor}"

            time_slots.add(bloco)

    if not time_slots:
        return pd.DataFrame()

    # Sort time slots chronologically using parser
    def sort_key(block_code):
        bloco_info = parser.MAP_SCHEDULE_TIMES.get(block_code, {})
        start_time = bloco_info.get("inicio", "00:00")
        # Convert to minutes for proper sorting
        try:
            hours, minutes = map(int, start_time.split(":"))
            return hours * 60 + minutes
        except ValueError:
            return 0

    sorted_time_slots = sorted(time_slots, key=sort_key)

    # Create DataFrame
    df_data = {}
    for dia_name in weekdays.values():
        df_data[dia_name] = []
        for bloco in sorted_time_slots:
            content = schedule_data.get(dia_name, {}).get(bloco, "")
            df_data[dia_name].append(content)

    # Handle reservations separately if any
    if "RESERVAS" in schedule_data:
        df_data["RESERVAS"] = []
        for bloco in sorted_time_slots:
            content = schedule_data["RESERVAS"].get(bloco, "")
            df_data["RESERVAS"].append(content)

    # Create DataFrame with time slots as index
    df = pd.DataFrame(df_data, index=sorted_time_slots)

    # Format index with human-readable times
    formatted_index = []
    for bloco in sorted_time_slots:
        bloco_info = parser.MAP_SCHEDULE_TIMES.get(bloco, {})
        start_time = bloco_info.get("inicio", bloco)
        end_time = bloco_info.get("fim", "")
        formatted_index.append(
            f"{start_time}-{end_time}" if start_time != bloco else bloco
        )

    df.index = formatted_index

    return df


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("📅 Visualização do Ensalamento")
st.markdown(
    "Visualize e gerencie o ensalamento semestral consolidado com reservas esporádicas."
)

# ============================================================================
# FILTERS AND CONTROLS
# ============================================================================

try:
    with get_db_session() as session:
        # Initialize repositories
        aloc_repo = AlocacaoRepository(session)
        reserva_repo = ReservaRepository(session)
        sala_repo = SalaRepository(session)
        prof_repo = ProfessorRepository(session)
        disc_repo = DisciplinaRepository(session)
        dia_repo = DiaSemanaRepository(session)
        horario_repo = HorarioBlocoRepository(session)

        # Get semester options using cached helper
        semester_options = get_semester_options()
        if not semester_options:
            st.warning("Nenhum semestre encontrado.")
            st.stop()

        # Get rooms data
        salas_orm = session.query(Sala).join(Predio).all()

        # Create filter options
        semestres_options = {sem_id: sem_name for sem_id, sem_name in semester_options}
        salas_options = {s.id: f"{s.predio.nome}: {s.nome}" for s in salas_orm}

        col1, col2 = st.columns(2)

        with col1:
            selected_semestre = st.selectbox(
                "📅 Semestre:",
                options=list(semestres_options.keys()),
                format_func=lambda x: semestres_options.get(x, f"ID {x}"),
                index=0,  # Select first (most recent) by default
                key="semester_filter",
            )

        with col2:
            selected_entity = st.selectbox(
                "Sala:",
                options=["all"] + list(salas_options.keys()),
                format_func=lambda x: (
                    "Todas as salas" if x == "all" else salas_options.get(x, f"ID {x}")
                ),
                key="entity_filter",
            )

        # Show reservations only if checkbox is checked
        show_reservations = st.checkbox(
            "Mostrar Reservas",
            value=False,
            help="Incluir reservas esporádicas na visualização",
            key="show_reservations",
        )

        # Get data based on filters and display by default
        with st.spinner("Carregando dados..."):
            # Get allocations for selected semester
            allocacoes = (
                aloc_repo.get_by_semestre(selected_semestre)
                if selected_semestre
                else []
            )

            # Get reservations only if checkbox is checked
            reservas = reserva_repo.get_all() if show_reservations else []

            # Group allocations by room
            room_allocations = {}
            for alloc in allocacoes:
                room_id = alloc.sala_id
                if selected_entity != "all" and room_id != selected_entity:
                    continue

                if room_id not in room_allocations:
                    room_allocations[room_id] = {
                        "room_name": salas_options.get(room_id, f"Sala {room_id}"),
                        "allocations": [],
                    }

                room_allocations[room_id]["allocations"].append(alloc)

            # Group reservations by room
            for reserva in reservas:
                room_id = reserva.sala_id
                if selected_entity != "all" and room_id != selected_entity:
                    continue

                if room_id not in room_allocations:
                    room_allocations[room_id] = {
                        "room_name": salas_options.get(room_id, f"Sala {room_id}"),
                        "allocations": [],
                    }

                # Convert reservation to allocation-like format for consistency
                reservation_alloc = {
                    "type": "reservation",
                    "titulo": reserva.titulo_evento,
                    "solicitante": reserva.username_solicitante,
                    "dia_semana_id": reserva.data_reserva,  # Placeholder - would need weekday mapping
                    "codigo_bloco": reserva.codigo_bloco,
                }
                room_allocations[room_id]["allocations"].append(reservation_alloc)

            # Display schedule grids for each room
            rooms_displayed = 0
            for room_id, room_data in room_allocations.items():
                room_name = room_data["room_name"]
                allocations = room_data["allocations"]

                if not allocations:
                    continue

                # Create room schedule grid
                room_grid = create_room_schedule_grid(allocations, room_name)
                if room_grid is not None and not room_grid.empty:
                    rooms_displayed += 1
                    st.subheader(f"🏢 {room_name}")
                    st.table(room_grid)

            if rooms_displayed == 0:
                st.info("ℹ️ Nenhum dado encontrado com os filtros aplicados.")

        # Export options
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "📊 Gerar Relatório PDF", help="Gera relatório completo em PDF"
            ):
                st.warning("⚠️ Funcionalidade de PDF será implementada próxima versão")

        with col2:
            if st.button(
                "📈 Gerar Estatísticas", help="Gera estatísticas de utilização"
            ):
                st.warning(
                    "⚠️ Funcionalidade de estatísticas será implementada próxima versão"
                )

        # Display feedback
        display_session_feedback("allocation_view")

except Exception as e:
    st.error(f"❌ Erro ao carregar dados de ensalamento: {str(e)}")
    import traceback

    st.code(traceback.format_exc())

# Page Footer
page_footer.show()
