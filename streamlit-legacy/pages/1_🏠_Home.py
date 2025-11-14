"""
Home Page (no login required)

Displays rooms allocation grids/tables
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple
from st_aggrid import AgGrid, GridOptionsBuilder
from pages.components.auth import initialize_page

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Home - Ensalamento",
    page_icon="🏠",
    layout="wide",
    key_suffix="home",
    requires_auth=False,
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
from src.models.academic import Professor, Semestre
from src.models.allocation import AlocacaoSemestral
from src.utils.cache_helpers import get_sigaa_parser, get_semester_options
from src.services.pdf_report_service import PDFReportService
from src.services.statistics_report_service import StatisticsReportService
from pages.components.ui import page_footer

# ============================================================================
# CONFIGURATION OPTIONS
# ============================================================================

# Control advanced grid features (enterprise modules, sidebar, export)
# Set to False for faster loading, True for full feature set
USE_ADVANCED_GRID_FEATURES = False

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def create_grid_options(dataframe: pd.DataFrame) -> dict:
    """
    Create AgGrid configuration for room schedule display.

    Args:
        dataframe: DataFrame containing room schedule data

    Returns:
        Grid options dictionary for AgGrid
    """
    gb = GridOptionsBuilder.from_dataframe(dataframe)

    # Configure grid options
    gb.configure_default_column(
        resizable=True,
        filterable=True,
        sortable=True,
        wrapText=True,
        autoHeight=True,
        cellStyle={"borderRight": "1px solid #e0e0e0"},
        headerCellStyle={"borderRight": "1px solid #e0e0e0"},
    )

    # Set column widths - make time column narrower, content columns wider
    gb.configure_column("Horário", width=120, pinned="left")
    for col in dataframe.columns:
        if col != "Horário":
            gb.configure_column(col, width=200)

    # Enable sidebar filtering only if advanced features are enabled
    if USE_ADVANCED_GRID_FEATURES:
        gb.configure_side_bar()

    # Grid options
    grid_options = gb.build()
    grid_options["domLayout"] = "autoHeight"

    return grid_options


# ============================================================================
# UTILITY FUNCTIONS (continued)
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

    # Get all time slots from MAP_SCHEDULE_TIMES to ensure consistent grid height
    # This includes M1-M5, T1-T6, N1-N4
    time_slots = set(parser.MAP_SCHEDULE_TIMES.keys())
    schedule_data = {}

    # Weekdays mapping
    weekdays = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}

    # Initialize empty schedule
    for dia_id, dia_name in weekdays.items():
        schedule_data[dia_name] = {}

    # Populate schedule data with allocations
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
                else ""
            )

            if professor:
                professor = f" | Prof(a). {professor}"

            schedule_data[dia_name][bloco] = f"{disciplina}{professor}"

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
    df.index.name = "Horário"

    return df


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

        # Get the active semester (status = 1)
        active_semester = (
            session.query(Semestre).filter(Semestre.status == True).first()
        )
        if not active_semester:
            st.warning(
                "Nenhum semestre ativo encontrado. Configure um semestre ativo nas configurações."
            )
            st.stop()

        active_semester_id = active_semester.id
        active_semester_name = active_semester.nome

        # Get rooms data
        salas_orm = session.query(Sala).join(Predio).all()

        # Create filter options
        salas_options = {s.id: f"{s.predio.nome}: {s.nome}" for s in salas_orm}
        predios_options = {p.id: p.nome for p in session.query(Predio).all()}

        # Get disciplines for the active semester
        demandas = disc_repo.get_by_semestre(active_semester_id)

        # Create unique discipline options (codigo - nome format)
        disciplina_options = {}
        for demanda in demandas:
            key = demanda.codigo_disciplina
            display_name = f"{demanda.codigo_disciplina} - {demanda.nome_disciplina}"
            if key not in disciplina_options:
                disciplina_options[key] = display_name

        # Create unique professor options from active semester allocations
        professor_options = {}
        for demanda in demandas:
            if (
                demanda.professores_disciplina
                and demanda.professores_disciplina.strip()
            ):
                # Split by common separators and clean up
                professors = [
                    p.strip()
                    for p in demanda.professores_disciplina.replace(";", ",")
                    .replace("/", ",")
                    .split(",")
                    if p.strip()
                ]
                for professor in professors:
                    if professor and professor not in professor_options:
                        professor_options[professor] = professor

        st.title(f"📅 Visualizar Ensalamento {active_semester_name}")

        st.subheader("🔎 Filtrar Exibição do Ensalamento")

        # Clear filters button (must be before widgets that use session state)
        if st.button(
            "🔄 Limpar Filtros",
            help="Limpa todos os filtros",
            key="clear_filters",
        ):
            st.session_state.predio_filter = "all"
            st.session_state.entity_filter = "all"
            st.session_state.disciplina_filter = "all"
            st.session_state.professor_filter = "all"
            st.rerun()

        col1, col2 = st.columns(2)

        with col1:
            selected_predio = st.selectbox(
                "🏢 Prédio:",
                options=["all"] + list(predios_options.keys()),
                format_func=lambda x: (
                    "Todas os prédios"
                    if x == "all"
                    else predios_options.get(x, f"ID {x}")
                ),
                key="predio_filter",
            )
            selected_disciplina = st.selectbox(
                "📚 Disciplina:",
                options=["all"] + list(disciplina_options.keys()),
                format_func=lambda x: (
                    "Todas as disciplinas"
                    if x == "all"
                    else disciplina_options.get(x, f"Código {x}")
                ),
                key="disciplina_filter",
            )

        with col2:
            selected_entity = st.selectbox(
                "🚪 Sala:",
                options=["all"] + list(salas_options.keys()),
                format_func=lambda x: (
                    "Todas as salas" if x == "all" else salas_options.get(x, f"ID {x}")
                ),
                key="entity_filter",
            )

            selected_professor = st.selectbox(
                "👨‍🏫 Professor:",
                options=["all"] + list(professor_options.keys()),
                format_func=lambda x: (
                    "Todos os professores"
                    if x == "all"
                    else professor_options.get(x, f"Professor {x}")
                ),
                key="professor_filter",
            )

        show_reservations = False  # disable reservations display in this page

        # Get data based on filters - LOAD DATA BEFORE BUTTONS
        with st.spinner("Carregando dados..."):
            # Get allocations for active semester
            allocacoes = aloc_repo.get_by_semestre(active_semester_id)

            # Get reservations only if checkbox is checked
            reservas = reserva_repo.get_all() if show_reservations else []

            # Group allocations by room
            room_allocations = {}
            for alloc in allocacoes:
                room_id = alloc.sala_id

                # Apply entity filter (specific room)
                if selected_entity != "all" and room_id != selected_entity:
                    continue

                # Apply building filter (selected_predio)
                if selected_predio != "all":
                    # Get the room to check its building
                    room = next((s for s in salas_orm if s.id == room_id), None)
                    if room and room.predio_id != selected_predio:
                        continue

                # Apply discipline filter
                if selected_disciplina != "all":
                    # Check if allocation has a demanda and matches the selected discipline
                    if (
                        not alloc.demanda
                        or alloc.demanda.codigo_disciplina != selected_disciplina
                    ):
                        continue

                # Apply professor filter
                if selected_professor != "all":
                    # Check if allocation has a demanda and the professor name contains the selected professor
                    if (
                        not alloc.demanda
                        or not alloc.demanda.professores_disciplina
                        or selected_professor
                        not in alloc.demanda.professores_disciplina
                    ):
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

                # Apply entity filter (specific room)
                if selected_entity != "all" and room_id != selected_entity:
                    continue

                # Apply building filter (selected_predio)
                if selected_predio != "all":
                    # Get the room to check its building
                    room = next((s for s in salas_orm if s.id == room_id), None)
                    if room and room.predio_id != selected_predio:
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

        # Count rooms with allocations for display
        rooms_displayed = sum(
            1 for room_data in room_allocations.values() if room_data["allocations"]
        )

        # Display schedule grids for each room
        st.markdown("---")

        if rooms_displayed == 0:
            st.info("ℹ️ Nenhum dado encontrado com os filtros aplicados.")
        else:
            for room_id, room_data in room_allocations.items():
                room_name = room_data["room_name"]
                allocations = room_data["allocations"]

                if not allocations:
                    continue

                # Create room schedule grid
                room_grid = create_room_schedule_grid(allocations, room_name)
                if room_grid is not None and not room_grid.empty:
                    st.write(f"🏢 **{room_name}**")

                    # Configure and display interactive grid
                    grid_options = create_grid_options(room_grid)
                    aggrid_kwargs = {
                        "gridOptions": grid_options,
                        "height": 400,
                        "width": "100%",
                        "fit_columns_on_grid_load": True,
                        "theme": "streamlit",  # Use streamlit theme for consistency
                        "key": f"room_grid_{room_id}_{active_semester_id}",
                        "allow_unsafe_jscode": True,
                    }

                    # Enable enterprise modules only for advanced features
                    if USE_ADVANCED_GRID_FEATURES:
                        aggrid_kwargs["enable_enterprise_modules"] = True
                        grid_response = AgGrid(room_grid, **aggrid_kwargs)

                        # Add CSV export button for this room
                        col1, col2 = st.columns([1, 5])  # Small column for button
                        with col1:
                            if st.button(
                                "📥 CSV",
                                key=f"export_csv_{room_id}_{active_semester_id}",
                                help=f"Exportar planilha de {room_name} para CSV",
                            ):
                                csv_data = room_grid.to_csv(index=True)
                                st.download_button(
                                    label="⬇️ Baixar CSV",
                                    data=csv_data,
                                    file_name=f"sala_{room_name.replace(':', '_').replace(' ', '_')}.csv",
                                    mime="text/csv",
                                    key=f"download_csv_{room_id}_{active_semester_id}",
                                )
                    else:
                        # Simple mode without enterprise features
                        grid_response = AgGrid(room_grid, **aggrid_kwargs)

        # Display feedback
        display_session_feedback("allocation_view")

except Exception as e:
    st.error(f"❌ Erro ao carregar dados de ensalamento: {str(e)}")
    import traceback

    st.code(traceback.format_exc())

# Page Footer
page_footer.show()
