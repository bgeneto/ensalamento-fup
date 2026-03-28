"""
Room Allocation Visualization Page

Display and manage semester allocations.
"""

from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from pages.components.auth import initialize_page

# Initialize page with authentication and configuration
if not initialize_page(
    page_title="Visualização - Ensalamento",
    page_icon="👁️",
    layout="wide",
    key_suffix="visualizacao",
):
    st.stop()

# ============================================================================
# IMPORTS
# ============================================================================

from pages.components.ui import page_footer
from src.services.pdf_report_service import PDFReportService
from src.services.statistics_report_service import StatisticsReportService
from src.utils.browser_download import trigger_auto_download
from src.utils.cache_helpers import (
    get_room_display_metadata,
    get_semester_demands_snapshot,
    get_semester_options,
    get_semester_schedule_snapshot,
    get_sigaa_parser,
    get_tipo_sala_options,
)
from src.utils.ui_feedback import display_session_feedback

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

        except Exception:
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
        if isinstance(alloc, dict) and alloc.get("type") in {
            "reservation",
            "semester_reservation",
        }:
            bloco = alloc["codigo_bloco"]
            titulo = alloc["titulo"]
            day_id = alloc.get("day_id") or alloc.get("dia_semana_id")

            if day_id not in weekdays:
                continue

            dia_name = weekdays[day_id]
            schedule_data[dia_name][bloco] = titulo
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


# ============================================================================
# MAIN PAGE CONTENT
# ============================================================================

# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("📅 Visualização do Ensalamento")
st.markdown("Visualize o ensalamento semestral consolidado para o semestre desejado.")

# ============================================================================
# FILTERS AND CONTROLS
# ============================================================================

st.subheader("🔎 Filtrar Exibição do Ensalamento")

try:
    semester_options = get_semester_options()
    if not semester_options:
        st.warning("Nenhum semestre encontrado.")
        st.stop()

    semestres_options = {sem_id: sem_name for sem_id, sem_name in semester_options}
    current_semester_id = st.session_state.get("global_semester_id")

    if current_semester_id not in semestres_options:
        current_semester_id = semester_options[0][0]
        st.session_state.global_semester_id = current_semester_id

    room_metadata = get_room_display_metadata()
    salas = room_metadata["salas"]
    salas_options = room_metadata["salas_options"]
    predios_options = room_metadata["predios_options"]
    room_to_predio = room_metadata["room_to_predio"]

    col1, col2 = st.columns(2)

    with col1:
        selected_semestre = st.selectbox(
            "📅 Semestre:",
            options=semestres_options.keys(),
            format_func=lambda x: semestres_options.get(x, f"Semestre {x}"),
            index=list(semestres_options.keys()).index(current_semester_id),
            disabled=False,
            key="semester_display_exibicao",
        )

        selected_predio = st.selectbox(
            "🏢 Prédio:",
            options=["all"] + list(predios_options.keys()),
            format_func=lambda x: (
                "Todas os prédios" if x == "all" else predios_options.get(x, f"ID {x}")
            ),
            key="predio_filter",
        )

        def clear_filters():
            st.session_state.predio_filter = "all"
            st.session_state.entity_filter = "all"

        if st.button(
            "🔄 Limpar Filtros",
            help="Limpa os filtros de prédio e sala",
            key="clear_filters",
            on_click=clear_filters,
            width="stretch",
        ):
            pass

    with col2:
        selected_entity = st.selectbox(
            "🚪 Sala:",
            options=["all"] + list(salas_options.keys()),
            format_func=lambda x: (
                "Todas as salas" if x == "all" else salas_options.get(x, f"ID {x}")
            ),
            key="entity_filter",
        )

    with st.spinner("Carregando dados..."):
        schedule_snapshot = get_semester_schedule_snapshot(
            selected_semestre,
            include_semester_reservations=True,
        )
        allocacoes = schedule_snapshot["allocations"]
        semester_reservation_allocations = schedule_snapshot[
            "semester_reservation_allocations"
        ]

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

            room_allocations.setdefault(
                room_id,
                {
                    "room_name": salas_options.get(room_id, f"Sala {room_id}"),
                    "allocations": [],
                },
            )
            room_allocations[room_id]["allocations"].append(alloc)

        for room_id, reservations in semester_reservation_allocations.items():
            if selected_entity != "all" and room_id != selected_entity:
                continue

            if (
                selected_predio != "all"
                and room_to_predio.get(room_id) != selected_predio
            ):
                continue

            room_allocations.setdefault(
                room_id,
                {
                    "room_name": salas_options.get(room_id, f"Sala {room_id}"),
                    "allocations": [],
                },
            )
            room_allocations[room_id]["allocations"].extend(reservations)

    rooms_displayed = sum(
        1 for room_data in room_allocations.values() if room_data["allocations"]
    )

    st.markdown("---")
    st.subheader("📊 Relatórios e Exportação")

    col1, col2 = st.columns(2)

    with col1:
        portrait_mode = st.checkbox(
            "📄 Modo Retrato",
            value=True,
            help="Gera relatório em orientação retrato A4 (padrão: paisagem)",
            key="portrait_mode_checkbox",
        )

        if st.button(
            "📊 Gerar Relatório PDF",
            help="Gera relatório completo em PDF (uma sala por página)",
            key="generate_pdf_report",
        ):
            try:
                with st.spinner("Gerando relatório PDF..."):
                    pdf_service = PDFReportService()
                    room_id_for_pdf = (
                        None if selected_entity == "all" else selected_entity
                    )
                    pdf_content = pdf_service.generate_allocation_report(
                        room_allocations=room_allocations,
                        semester_name=semestres_options.get(
                            selected_semestre, f"Semestre {selected_semestre}"
                        ),
                        selected_room_id=room_id_for_pdf,
                        portrait_mode=portrait_mode,
                    )

                    if pdf_content:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                        if selected_entity == "all":
                            filename = f"ensalamento_{semestres_options.get(selected_semestre, 'sem')}_{timestamp}.pdf"
                            success_msg = f"✅ Relatório gerado com sucesso ({rooms_displayed} salas)"
                        else:
                            room_name_clean = salas_options.get(
                                selected_entity, f"sala_{selected_entity}"
                            )
                            room_name_clean = (
                                room_name_clean.replace(":", "_")
                                .replace(" ", "_")
                                .replace("/", "-")
                            )
                            filename = f"ensalamento_{room_name_clean}_{timestamp}.pdf"
                            success_msg = "✅ Relatório gerado com sucesso (1 sala)"

                        st.session_state["allocation_view_pdf"] = pdf_content
                        st.session_state["allocation_view_pdf_filename"] = filename
                        trigger_auto_download(
                            data=pdf_content,
                            filename=filename,
                            mime="application/pdf",
                        )
                        st.success(
                            f"{success_msg}. O download deve iniciar automaticamente."
                        )
                    else:
                        st.error("❌ Erro: Nenhum conteúdo gerado para o PDF")

            except ImportError:
                st.error(
                    "❌ Biblioteca reportlab não instalada. Execute: pip install reportlab>=4.0.0"
                )
            except Exception as e:
                st.error(f"❌ Erro ao gerar relatório PDF: {str(e)}")
                import traceback

                with st.expander("🔍 Detalhes do erro"):
                    st.code(traceback.format_exc())

        if st.session_state.get("allocation_view_pdf"):
            st.download_button(
                label="⬇️ Baixar Relatório PDF",
                data=st.session_state["allocation_view_pdf"],
                file_name=st.session_state.get(
                    "allocation_view_pdf_filename", "relatorio_ensalamento.pdf"
                ),
                mime="application/pdf",
                key="download_pdf_report",
            )

    with col2:
        if st.button(
            "📈 Gerar Estatísticas",
            help="Gera relatório estatístico completo",
            key="generate_statistics_report",
        ):
            try:
                with st.spinner("Gerando relatório estatístico..."):
                    stats_service = StatisticsReportService()
                    demands = get_semester_demands_snapshot(selected_semestre)
                    pdf_content = stats_service.generate_statistics_report(
                        allocations=allocacoes,
                        demands=demands,
                        rooms=salas,
                        buildings=predios_options,
                        semester_name=semestres_options.get(
                            selected_semestre, f"Semestre {selected_semestre}"
                        ),
                        semester_reservations_by_room=semester_reservation_allocations,
                        room_types=get_tipo_sala_options(),
                    )

                    if pdf_content:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"estatisticas_{semestres_options.get(selected_semestre, 'sem')}_{timestamp}.pdf"

                        st.session_state["statistics_view_pdf"] = pdf_content
                        st.session_state["statistics_view_pdf_filename"] = filename
                        trigger_auto_download(
                            data=pdf_content,
                            filename=filename,
                            mime="application/pdf",
                        )
                        st.success(
                            "✅ Relatório estatístico gerado com sucesso. "
                            "O download deve iniciar automaticamente."
                        )
                    else:
                        st.error("❌ Erro: Nenhum conteúdo gerado para o PDF")

            except ImportError:
                st.error(
                    "❌ Biblioteca reportlab não instalada. Execute: pip install reportlab>=4.0.0"
                )
            except Exception as e:
                st.error(f"❌ Erro ao gerar relatório estatístico: {str(e)}")
                import traceback

                with st.expander("🔍 Detalhes do erro"):
                    st.code(traceback.format_exc())

        if st.session_state.get("statistics_view_pdf"):
            st.download_button(
                label="⬇️ Baixar Relatório Estatístico",
                data=st.session_state["statistics_view_pdf"],
                file_name=st.session_state.get(
                    "statistics_view_pdf_filename", "relatorio_estatistico.pdf"
                ),
                mime="application/pdf",
                key="download_statistics_report",
            )

    st.markdown("---")
    st.subheader("📋 Ensalamento por Sala")

    if rooms_displayed == 0:
        st.info("ℹ️ Nenhum dado encontrado com os filtros aplicados.")
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
                "key": f"room_grid_{room_id}_{selected_semestre}",
                "allow_unsafe_jscode": True,
            }

            if USE_ADVANCED_GRID_FEATURES:
                aggrid_kwargs["enable_enterprise_modules"] = True
                AgGrid(room_grid_display, **aggrid_kwargs)

                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button(
                        "📥 CSV",
                        key=f"export_csv_{room_id}_{selected_semestre}",
                        help=f"Exportar planilha de {room_name} para CSV",
                    ):
                        csv_data = room_grid.to_csv(index=True)
                        st.download_button(
                            label="⬇️ Baixar CSV",
                            data=csv_data,
                            file_name=f"sala_{room_name.replace(':', '_').replace(' ', '_')}.csv",
                            mime="text/csv",
                            key=f"download_csv_{room_id}_{selected_semestre}",
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
