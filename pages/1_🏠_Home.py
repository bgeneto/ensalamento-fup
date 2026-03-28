"""
Home Page (no login required)

Displays rooms allocation grids/tables
"""

from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st
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

from pages.components.ui import page_footer
from src.utils.cache_helpers import (
    get_active_semester_snapshot,
    get_room_display_metadata,
    get_semester_demands_snapshot,
    get_semester_schedule_snapshot,
    get_sigaa_parser,
)
from src.utils.ui_feedback import (
    display_session_feedback,
)

# ============================================================================
# CONFIGURATION OPTIONS
# ============================================================================

# Control advanced grid features (enterprise modules, sidebar, export)
# Set to False for faster loading, True for full feature set
USE_ADVANCED_GRID_FEATURES = False
AGGRID_CUSTOM_CSS = {
    ".ag-root-wrapper": {
        "font-family": "'Arial Narrow', 'FiraXCond', 'Fira Sans Extra Condensed', 'Roboto Condensed', 'Noto Sans Condensed', 'Noto Sans SemiCondensed', 'Avenir Next Condensed', 'Helvetica Neue Condensed', 'Arial Narrow', 'Liberation Sans Narrow', 'Roboto', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif !important",
        "font-stretch": "condensed",
    },
    ".ag-root-wrapper .ag-cell": {
        "font-family": "'Arial Narrow', 'FiraXCond', 'Fira Sans Extra Condensed', 'Roboto Condensed', 'Noto Sans Condensed', 'Noto Sans SemiCondensed', 'Avenir Next Condensed', 'Helvetica Neue Condensed', 'Arial Narrow', 'Liberation Sans Narrow', 'Roboto', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif !important",
        "font-stretch": "condensed",
    },
    ".ag-root-wrapper .ag-header-cell-text": {
        "font-family": "'Arial Narrow', 'FiraXCond', 'Fira Sans Extra Condensed', 'Roboto Condensed', 'Noto Sans Condensed', 'Noto Sans SemiCondensed', 'Avenir Next Condensed', 'Helvetica Neue Condensed', 'Arial Narrow', 'Liberation Sans Narrow', 'Roboto', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif !important",
        "font-stretch": "condensed",
        "font-weight": "600 !important",
        "letter-spacing": "0.2px",
    },
}
WEEKDAY_NAMES = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}

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


def get_block_sort_value(block_code: str) -> int:
    """Return a stable numeric sort key for a SIGAA block code."""
    parser = get_sigaa_parser()
    bloco_info = parser.MAP_SCHEDULE_TIMES.get(block_code, {})
    start_time = bloco_info.get("inicio", "00:00")

    try:
        hours, minutes = map(int, start_time.split(":"))
        return hours * 60 + minutes
    except ValueError:
        return 0


def get_time_range_sort_value(time_range: str) -> int:
    """Return a numeric sort key for a display time range."""
    start_time = time_range.split("-", 1)[0]

    try:
        hours, minutes = map(int, start_time.split(":"))
        return hours * 60 + minutes
    except ValueError:
        return 0


# ============================================================================
# UTILITY FUNCTIONS (continued)
# ============================================================================


def combine_consecutive_blocks(blocks: List[Tuple[str, int]]) -> List[Dict[str, Any]]:
    """
    Combine consecutive time blocks into consolidated schedules.

    Args:
        blocks: List of (codigo_bloco, dia_sigaa) tuples

    Returns:
        List of combined schedule dicts with start/end times
    """
    if not blocks:
        return []

    parser = get_sigaa_parser()
    blocks_sorted = sorted(blocks, key=lambda x: (x[1], get_block_sort_value(x[0])))
    combined = []

    current_start = None
    current_end = None
    current_day = None
    current_start_code = None

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
                day_name = WEEKDAY_NAMES.get(current_day, f"Dia {current_day}")
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

        except Exception:
            # Skip problematic blocks
            continue

    # Close last group
    if current_day is not None:
        day_name = WEEKDAY_NAMES.get(current_day, f"Dia {current_day}")
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


def create_allocation_list_items(
    room_allocations: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build a discipline-oriented list view from already filtered room allocations.

    Returns:
        List of list item dicts sorted by discipline code/name/turma.
    """
    disciplines: Dict[Tuple[Any, ...], Dict[str, Any]] = {}

    for room_id, room_data in room_allocations.items():
        room_name = room_data["room_name"]

        for alloc in room_data["allocations"]:
            if isinstance(alloc, dict):
                continue

            demanda = getattr(alloc, "demanda", None)
            if demanda is None:
                continue

            discipline_key = (
                getattr(alloc, "demanda_id", None),
                getattr(demanda, "codigo_disciplina", "") or "",
                getattr(demanda, "nome_disciplina", "") or "",
                getattr(demanda, "turma_disciplina", "") or "",
            )

            if discipline_key not in disciplines:
                disciplines[discipline_key] = {
                    "codigo": getattr(demanda, "codigo_disciplina", "") or "N/A",
                    "nome": getattr(demanda, "nome_disciplina", "") or "Sem nome",
                    "turma": getattr(demanda, "turma_disciplina", "") or "",
                    "professores": getattr(demanda, "professores_disciplina", "") or "",
                    "schedules_by_room": {},
                }

            room_key = (room_id, room_name)
            schedules_by_room = disciplines[discipline_key]["schedules_by_room"]
            schedules_by_room.setdefault(room_key, []).append(
                (alloc.codigo_bloco, alloc.dia_semana_id)
            )

    items: List[Dict[str, Any]] = []
    for discipline_data in disciplines.values():
        schedule_lines = []

        for (_, room_name), blocks in discipline_data["schedules_by_room"].items():
            grouped_schedules = combine_consecutive_blocks(blocks)
            merged_by_time: Dict[str, Dict[str, Any]] = {}

            for schedule in grouped_schedules:
                time_key = schedule["time"]
                if time_key not in merged_by_time:
                    merged_by_time[time_key] = {
                        "days": [],
                        "time": time_key,
                        "room_name": room_name,
                        "sort_day": schedule["day"],
                        "sort_time": get_time_range_sort_value(time_key),
                    }

                merged_by_time[time_key]["days"].append(
                    (schedule["day"], schedule["day_name"])
                )

            for merged in merged_by_time.values():
                sorted_days = sorted(merged["days"], key=lambda x: x[0])
                schedule_lines.append(
                    {
                        "days_label": "/".join(day_name for _, day_name in sorted_days),
                        "time": merged["time"],
                        "room_name": merged["room_name"],
                        "sort_day": merged["sort_day"],
                        "sort_time": merged["sort_time"],
                    }
                )

        schedule_lines.sort(
            key=lambda item: (item["sort_day"], item["sort_time"], item["room_name"])
        )

        items.append(
            {
                "codigo": discipline_data["codigo"],
                "nome": discipline_data["nome"],
                "turma": discipline_data["turma"],
                "professores": discipline_data["professores"],
                "schedule_lines": schedule_lines,
            }
        )

    items.sort(
        key=lambda item: (
            item["codigo"],
            item["nome"],
            item["turma"],
            item["professores"],
        )
    )
    return items


def render_allocation_list(room_allocations: Dict[int, Dict[str, Any]]) -> int:
    """Render the mobile-friendly discipline list view."""
    list_items = create_allocation_list_items(room_allocations)

    if not list_items:
        return 0

    st.caption(
        f"{len(list_items)} oferta(s) exibida(s), ordenadas por disciplina e com horários consolidados por sala."
    )

    for item in list_items:
        title = f"{item['codigo']} - {item['nome']}"
        if item["turma"]:
            title = f"{title} (Turma {item['turma']})"

        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.write(
                f"👨‍🏫 {item['professores']}"
                if item["professores"]
                else "👨‍🏫 Professor não informado"
            )

            schedule_lines = item["schedule_lines"]
            if schedule_lines:
                schedule_text = "\n".join(
                    f"- **{schedule['days_label']} {schedule['time']}** | {schedule['room_name']}"
                    for schedule in schedule_lines
                )
                st.markdown(schedule_text)
            else:
                st.caption("Sem horários alocados.")

    return len(list_items)


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

    # Initialize empty schedule
    for dia_id, dia_name in WEEKDAY_NAMES.items():
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

            if dia_id not in WEEKDAY_NAMES:
                continue

            dia_name = WEEKDAY_NAMES[dia_id]

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
            professor = (
                alloc.demanda.professores_disciplina
                if alloc.demanda is not None
                else ""
            )

            if professor:
                professor = f" | Prof(a). {professor}"

            schedule_data[dia_name][bloco] = f"{disciplina}{professor}"

    sorted_time_slots = sorted(time_slots, key=get_block_sort_value)

    # Create DataFrame
    df_data = {}
    for dia_name in WEEKDAY_NAMES.values():
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
    active_semester = get_active_semester_snapshot()
    if not active_semester:
        st.warning(
            "Nenhum semestre ativo encontrado. Configure um semestre ativo na página ⚙️ Configurações."
        )
        st.stop()

    active_semester_id = active_semester["id"]
    active_semester_name = active_semester["nome"]

    room_metadata = get_room_display_metadata()
    salas_options = room_metadata["salas_options"]
    predios_options = room_metadata["predios_options"]
    room_to_predio = room_metadata["room_to_predio"]

    demandas = get_semester_demands_snapshot(active_semester_id)

    disciplina_options = {}
    for demanda in demandas:
        key = demanda.codigo_disciplina
        display_name = f"{demanda.codigo_disciplina} - {demanda.nome_disciplina}"
        if key not in disciplina_options:
            disciplina_options[key] = display_name

    professor_options = {}
    for demanda in demandas:
        if demanda.professores_disciplina and demanda.professores_disciplina.strip():
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

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"""
            <div style="text-align:center;">
                <img src="/app/static/unb-logo.png" width="60">
                <h2>Ensalamento FUP/UnB {active_semester_name}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
                "Todas os prédios" if x == "all" else predios_options.get(x, f"ID {x}")
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

    if "home_view_mode" not in st.session_state:
        st.session_state.home_view_mode = "📋 Lista"

    selected_view = st.segmented_control(
        "👁️ Visualização:",
        options=["📋 Lista", "📊 Tabela"],
        key="home_view_mode",
    )

    with st.spinner("Carregando dados..."):
        schedule_snapshot = get_semester_schedule_snapshot(active_semester_id)
        allocacoes = schedule_snapshot["allocations"]

        room_allocations = {}
        for alloc in allocacoes:
            room_id = alloc.sala_id

            if selected_entity != "all" and room_id != selected_entity:
                continue

            if (
                selected_predio != "all"
                and room_to_predio.get(room_id) != selected_predio
            ):
                continue

            if selected_disciplina != "all" and (
                not alloc.demanda
                or alloc.demanda.codigo_disciplina != selected_disciplina
            ):
                continue

            if selected_professor != "all" and (
                not alloc.demanda
                or not alloc.demanda.professores_disciplina
                or selected_professor not in alloc.demanda.professores_disciplina
            ):
                continue

            room_allocations.setdefault(
                room_id,
                {
                    "room_name": salas_options.get(room_id, f"Sala {room_id}"),
                    "allocations": [],
                },
            )
            room_allocations[room_id]["allocations"].append(alloc)

    rooms_displayed = sum(
        1 for room_data in room_allocations.values() if room_data["allocations"]
    )

    st.markdown("---")

    if rooms_displayed == 0:
        st.info("ℹ️ Nenhum dado encontrado com os filtros aplicados.")
    else:
        if selected_view == "📋 Lista":
            items_displayed = render_allocation_list(room_allocations)
            if items_displayed == 0:
                st.info("ℹ️ Nenhum ensalamento encontrado com os filtros aplicados.")
        else:
            for room_id, room_data in room_allocations.items():
                room_name = room_data["room_name"]
                allocations = room_data["allocations"]

                if not allocations:
                    continue

                room_grid = create_room_schedule_grid(allocations, room_name)
                if room_grid is None or room_grid.empty:
                    continue

                st.write(f"🏢 **{room_name}**")

                room_grid_display = room_grid.reset_index()
                grid_options = create_grid_options(room_grid_display)
                aggrid_kwargs = {
                    "gridOptions": grid_options,
                    "height": 400,
                    "width": "100%",
                    "fit_columns_on_grid_load": True,
                    "theme": "streamlit",
                    "custom_css": AGGRID_CUSTOM_CSS,
                    "key": f"room_grid_{room_id}_{active_semester_id}",
                    "allow_unsafe_jscode": True,
                }

                if USE_ADVANCED_GRID_FEATURES:
                    aggrid_kwargs["enable_enterprise_modules"] = True
                    AgGrid(room_grid_display, **aggrid_kwargs)

                    col1, col2 = st.columns([1, 5])
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
                    AgGrid(room_grid_display, **aggrid_kwargs)

    display_session_feedback("allocation_view")

except Exception as e:
    st.error(f"❌ Erro ao carregar dados de ensalamento: {str(e)}")
    import traceback

    st.code(traceback.format_exc())

# Page Footer
page_footer.show()
