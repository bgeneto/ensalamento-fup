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


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_sigaa_schedule_parser():
    """Create and return SigaaScheduleParser instance."""
    from src.utils.sigaa_parser import SigaaScheduleParser

    return SigaaScheduleParser()


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

    parser = get_sigaa_schedule_parser()
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
        sem_repo = SemestreRepository(session)
        dia_repo = DiaSemanaRepository(session)
        horario_repo = HorarioBlocoRepository(session)

        # Get basic data
        semestres = sem_repo.get_all()
        salas_orm = session.query(Sala).join(Predio).all()

        # Create filter options
        semestres_options = {s.id: f"{s.nome}" for s in semestres}
        salas_options = {s.id: f"{s.predio.nome}/{s.nome}" for s in salas_orm}

        col1, col2, col3 = st.columns(3)

        with col1:
            selected_semestre = st.selectbox(
                "Semestre:",
                options=list(semestres_options.keys()),
                format_func=lambda x: semestres_options.get(x, f"ID {x}"),
                index=(
                    len(semestres) - 1 if semestres else None
                ),  # Select latest by default
                key="semester_filter",
            )

        with col2:
            view_type = st.selectbox(
                "Visualizar por:",
                options=["sala", "professor", "disciplina"],
                format_func=lambda x: {
                    "sala": "Por Sala",
                    "professor": "Por Professor",
                    "disciplina": "Por Disciplina",
                }.get(x, x),
                key="view_type_filter",
            )

        with col3:
            if view_type == "sala":
                selected_entity = st.selectbox(
                    "Sala:",
                    options=["all"] + list(salas_options.keys()),
                    format_func=lambda x: (
                        "Todas as salas"
                        if x == "all"
                        else salas_options.get(x, f"ID {x}")
                    ),
                    key="entity_filter",
                )
            elif view_type == "professor":
                all_professores = prof_repo.get_all()
                prof_options = {p.id: p.nome_completo for p in all_professores}
                selected_entity = st.selectbox(
                    "Professor:",
                    options=["all"] + list(prof_options.keys()),
                    format_func=lambda x: (
                        "Todos os professores"
                        if x == "all"
                        else prof_options.get(x, f"ID {x}")
                    ),
                    key="entity_filter",
                )
            else:  # disciplina
                try:
                    all_disciplinas = disc_repo.get_all()
                    disc_options = {
                        d.id: f"{d.codigo_disciplina} - {d.nome_disciplina}"
                        for d in all_disciplinas
                    }
                    selected_entity = st.selectbox(
                        "Disciplina:",
                        options=["all"] + list(disc_options.keys()),
                        format_func=lambda x: (
                            "Todas as disciplinas"
                            if x == "all"
                            else disc_options.get(x, f"ID {x}")
                        ),
                        key="entity_filter",
                    )
                except Exception as e:
                    st.warning(f"Não foi possível carregar disciplinas: {str(e)}")
                    selected_entity = "all"

        # Get data based on filters
        if st.button("🔍 Atualizar Visualização", type="primary"):
            with st.spinner("Carregando dados..."):

                # Build data structure based on view type
                display_data = []

                if view_type == "sala":
                    # Get allocations and reservations for selected semester

                    # Get semester allocations
                    allocacoes = (
                        aloc_repo.get_by_semestre(selected_semestre)
                        if selected_semestre
                        else []
                    )

                    # Get all reservations (reservations don't have semester, they're date-based)
                    reservas = reserva_repo.get_all()

                    # Group by room
                    rooms_data = {}

                    for alloc in allocacoes:
                        room_id = alloc.sala_id
                        if selected_entity != "all" and room_id != selected_entity:
                            continue

                        if room_id not in rooms_data:
                            rooms_data[room_id] = {
                                "room_name": salas_options.get(
                                    room_id, f"Sala {room_id}"
                                ),
                                "allocations": [],
                                "reservations": [],
                            }

                        # Get all blocks for this allocation
                        blocks = []
                        if hasattr(alloc, "dia_semana_id") and hasattr(
                            alloc, "codigo_bloco"
                        ):
                            # This is a semester allocation
                            blocks.append((alloc.codigo_bloco, alloc.dia_semana_id))

                        if blocks:
                            rooms_data[room_id]["allocations"].append(
                                {
                                    "type": "allocation",
                                    "disciplina": (
                                        alloc.demanda.codigo_disciplina
                                        if alloc.demanda
                                        else "N/A"
                                    ),
                                    "professor": (
                                        alloc.demanda.professores_disciplina
                                        if alloc.demanda
                                        else "N/A"
                                    ),
                                    "turma": (
                                        alloc.demanda.turma_disciplina
                                        if alloc.demanda
                                        else "N/A"
                                    ),
                                    "blocks": blocks,
                                }
                            )

                    for reserva in reservas:
                        room_id = reserva.sala_id
                        if selected_entity != "all" and room_id != selected_entity:
                            continue

                        if room_id not in rooms_data:
                            rooms_data[room_id] = {
                                "room_name": salas_options.get(
                                    room_id, f"Sala {room_id}"
                                ),
                                "allocations": [],
                                "reservations": [],
                            }

                        # For reservations, we need to map the date to weekday
                        # This is simplified - in real implementation, you'd need date-to-weekday conversion
                        blocks = [
                            (reserva.codigo_bloco, 0)
                        ]  # Placeholder for date logic

                        rooms_data[room_id]["reservations"].append(
                            {
                                "type": "reservation",
                                "titulo": reserva.titulo_evento,
                                "solicitante": reserva.username_solicitante,
                                "data": reserva.data_reserva,
                                "blocks": blocks,
                            }
                        )

                    # Convert to display format
                    for room_id, data in rooms_data.items():
                        # Combine allocations and reservations
                        all_events = data["allocations"] + data["reservations"]

                        if all_events:
                            # Group by time blocks for display
                            time_groups = {}
                            for event in all_events:
                                for bloco, dia in event["blocks"]:
                                    key = f"{dia}-{bloco}"
                                    if key not in time_groups:
                                        time_groups[key] = []
                                    time_groups[key].append(event)

                            # Create display item
                            display_item = {
                                "Sala": data["room_name"],
                                "Horários": format_schedule_display(all_events),
                            }

                            # Add event details
                            event_descriptions = []
                            for event in all_events:
                                if event["type"] == "allocation":
                                    event_descriptions.append(
                                        f"📘 {event['disciplina']} T{event['turma']} - {event['professor']}"
                                    )
                                else:
                                    event_descriptions.append(
                                        f"🎯 {event['titulo']} ({event['solicitante']})"
                                    )

                            display_item["Eventos"] = " | ".join(event_descriptions)
                            display_data.append(display_item)

                elif view_type == "professor":
                    st.info(
                        "📝 Visualização por professor será implementada em seguida..."
                    )

                else:  # disciplina
                    st.info(
                        "📝 Visualização por disciplina será implementada em seguida..."
                    )

                # Display results
                if display_data:
                    df = pd.DataFrame(display_data)
                    st.dataframe(
                        df, width="stretch", hide_index=True, use_container_width=True
                    )
                else:
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
