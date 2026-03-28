"""
Statistics Report Generation Service

Creates comprehensive statistics reports for room allocation analysis.
"""

from __future__ import annotations

import io
from collections import defaultdict
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.utils.cache_helpers import get_sigaa_parser


class StatisticsReportService:
    """Service for generating statistics reports of room allocations."""

    DAY_NAMES = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}
    SHIFT_NAMES = {"M": "Manhã", "T": "Tarde", "N": "Noite"}

    def __init__(self):
        """Initialize statistics report service."""
        self.parser = get_sigaa_parser()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        self.styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=self.styles["Heading1"],
                fontSize=16,
                textColor=colors.HexColor("#1f4788"),
                spaceAfter=12,
                spaceBefore=0,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="SectionHeading",
                parent=self.styles["Heading2"],
                fontSize=12,
                textColor=colors.HexColor("#1f4788"),
                spaceAfter=6,
                spaceBefore=12,
                fontName="Helvetica-Bold",
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="StatsText",
                parent=self.styles["Normal"],
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
                fontName="Helvetica",
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="TableHeader",
                parent=self.styles["Normal"],
                fontSize=8,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
                textColor=colors.white,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="TableCell",
                parent=self.styles["Normal"],
                fontSize=8,
                alignment=TA_LEFT,
                fontName="Helvetica",
            )
        )

    def generate_statistics_report(
        self,
        allocations: List[Any],
        demands: List[Any],
        rooms: List[Any],
        buildings: Dict[int, str],
        semester_name: str,
        semester_reservations_by_room: Optional[Dict[int, List[Dict[str, Any]]]] = None,
        room_types: Optional[Dict[int, str]] = None,
    ) -> bytes:
        """
        Generate comprehensive statistics report.

        Args:
            allocations: List of allocation objects
            demands: List of all demand objects
            rooms: List of all room objects
            buildings: Dict mapping building_id to building name
            semester_name: Name of the semester (e.g., "2025-1")
            semester_reservations_by_room: Weekly reservation slots aggregated by room
            room_types: Dict mapping room type IDs to room type names

        Returns:
            bytes: PDF file content
        """
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            title=f"Estatísticas - {semester_name}",
            author="Sistema de Ensalamento FUP/UnB",
        )

        story = []
        story.append(
            Paragraph(
                f"Estatísticas de Ensalamento<br/>Semestre {semester_name}",
                self.styles["ReportTitle"],
            )
        )
        story.append(Spacer(1, 10))

        stats = self._calculate_statistics(
            allocations=allocations,
            demands=demands,
            rooms=rooms,
            buildings=buildings,
            semester_reservations_by_room=semester_reservations_by_room,
            room_types=room_types,
        )

        story.extend(self._build_executive_summary(stats))
        story.append(Spacer(1, 10))

        story.extend(self._build_room_utilization(stats))
        story.append(Spacer(1, 10))

        story.extend(self._build_capacity_analysis(stats))
        story.append(Spacer(1, 10))

        story.append(PageBreak())
        story.extend(self._build_time_slot_heatmap(stats))
        story.append(Spacer(1, 10))

        story.extend(self._build_building_analysis(stats))
        story.append(Spacer(1, 10))

        story.extend(self._build_room_type_analysis(stats))
        story.append(Spacer(1, 10))

        story.extend(self._build_unallocated_demands(stats))

        doc.build(story)

        pdf_content = buffer.getvalue()
        buffer.close()
        return pdf_content

    def _calculate_statistics(
        self,
        allocations: List[Any],
        demands: List[Any],
        rooms: List[Any],
        buildings: Dict[int, str],
        semester_reservations_by_room: Optional[Dict[int, List[Dict[str, Any]]]] = None,
        room_types: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        """Calculate all statistics needed for the report."""
        room_lookup = {room.id: room for room in rooms}
        demand_lookup = {demand.id: demand for demand in demands}
        room_types = room_types or {}

        total_slots_per_room = len(self.parser.MAP_SCHEDULE_TIMES) * len(self.DAY_NAMES)

        academic_slots = set()
        reservation_slots = set()
        combined_slots = set()
        demands_allocated = set()

        room_slot_map = defaultdict(set)
        room_academic_slot_map = defaultdict(set)
        room_reservation_slot_map = defaultdict(set)
        time_slot_grid = defaultdict(lambda: defaultdict(set))
        building_slot_map = defaultdict(set)
        room_type_slot_map = defaultdict(set)
        day_slot_usage = defaultdict(set)
        shift_slot_usage = defaultdict(set)
        capacity_gap_records = []
        seen_capacity_gap_keys = set()

        for alloc in allocations:
            room = room_lookup.get(alloc.sala_id)
            if not room:
                continue

            slot = (alloc.sala_id, alloc.dia_semana_id, alloc.codigo_bloco)
            academic_slots.add(slot)
            combined_slots.add(slot)
            demands_allocated.add(alloc.demanda_id)

            room_slot_map[alloc.sala_id].add((alloc.dia_semana_id, alloc.codigo_bloco))
            room_academic_slot_map[alloc.sala_id].add(
                (alloc.dia_semana_id, alloc.codigo_bloco)
            )
            time_slot_grid[alloc.codigo_bloco][alloc.dia_semana_id].add(alloc.sala_id)
            day_slot_usage[alloc.dia_semana_id].add(slot)
            shift_slot_usage[alloc.codigo_bloco[0]].add(slot)

            building_name = buildings.get(room.predio_id, "Desconhecido")
            building_slot_map[building_name].add(slot)
            room_type_slot_map[room.tipo_sala_id].add(slot)

            capacity_key = (alloc.demanda_id, alloc.sala_id)
            if capacity_key in seen_capacity_gap_keys:
                continue

            seen_capacity_gap_keys.add(capacity_key)
            demand = getattr(alloc, "demanda", None) or demand_lookup.get(
                alloc.demanda_id
            )
            demand_seats = getattr(demand, "vagas_disciplina", 0) or 0
            room_capacity = getattr(room, "capacidade", 0) or 0
            seat_gap = demand_seats - room_capacity

            if seat_gap > 0:
                capacity_gap_records.append(
                    {
                        "codigo": getattr(
                            demand, "codigo_disciplina", f"Demanda {alloc.demanda_id}"
                        ),
                        "nome": getattr(demand, "nome_disciplina", ""),
                        "turma": getattr(demand, "turma_disciplina", "") or "-",
                        "room_name": self._build_room_name(room, buildings),
                        "vagas": demand_seats,
                        "capacidade": room_capacity,
                        "deficit": seat_gap,
                    }
                )

        flattened_reservations = self._flatten_semester_reservations(
            semester_reservations_by_room or {}
        )
        for reservation in flattened_reservations:
            room = room_lookup.get(reservation["room_id"])
            if not room:
                continue

            slot = (
                reservation["room_id"],
                reservation["day_id"],
                reservation["codigo_bloco"],
            )
            reservation_slots.add(slot)
            combined_slots.add(slot)

            room_slot_map[reservation["room_id"]].add(
                (reservation["day_id"], reservation["codigo_bloco"])
            )
            room_reservation_slot_map[reservation["room_id"]].add(
                (reservation["day_id"], reservation["codigo_bloco"])
            )
            time_slot_grid[reservation["codigo_bloco"]][reservation["day_id"]].add(
                reservation["room_id"]
            )
            day_slot_usage[reservation["day_id"]].add(slot)
            shift_slot_usage[reservation["codigo_bloco"][0]].add(slot)

            building_name = buildings.get(room.predio_id, "Desconhecido")
            building_slot_map[building_name].add(slot)
            room_type_slot_map[room.tipo_sala_id].add(slot)

        stats: Dict[str, Any] = {
            "total_rooms": len(rooms),
            "total_demands": len(demands),
            "total_allocations": len(allocations),
            "total_academic_slots": len(academic_slots),
            "total_reservation_slots": len(reservation_slots),
            "total_occupied_slots": len(combined_slots),
        }

        rooms_used = {
            room_id
            for room_id, occupied_slots in room_slot_map.items()
            if occupied_slots
        }
        reservation_rooms = {
            room_id
            for room_id, occupied_slots in room_reservation_slot_map.items()
            if occupied_slots
        }
        academic_rooms = {
            room_id
            for room_id, occupied_slots in room_academic_slot_map.items()
            if occupied_slots
        }
        unused_room_ids = [room.id for room in rooms if room.id not in rooms_used]

        stats["rooms_used"] = len(rooms_used)
        stats["rooms_unused"] = len(unused_room_ids)
        stats["rooms_with_reservations"] = len(reservation_rooms)
        stats["rooms_reserved_only"] = len(reservation_rooms - academic_rooms)
        stats["demands_allocated"] = len(demands_allocated)
        stats["demands_unallocated"] = (
            stats["total_demands"] - stats["demands_allocated"]
        )
        stats["unused_rooms"] = [
            self._build_room_name(room_lookup[room_id], buildings)
            for room_id in unused_room_ids
            if room_id in room_lookup
        ]

        room_stats = []
        for room in rooms:
            occupied_slots = room_slot_map.get(room.id, set())
            academic_room_slots = room_academic_slot_map.get(room.id, set())
            reservation_room_slots = room_reservation_slot_map.get(room.id, set())

            room_stats.append(
                {
                    "room_id": room.id,
                    "room_name": self._build_room_name(room, buildings),
                    "room_type": room_types.get(
                        room.tipo_sala_id, f"Tipo {room.tipo_sala_id}"
                    ),
                    "occupied_slots": len(occupied_slots),
                    "academic_slots": len(academic_room_slots),
                    "reservation_slots": len(reservation_room_slots),
                    "weekly_minutes": sum(
                        self._slot_duration_minutes(block_code)
                        for _, block_code in occupied_slots
                    ),
                    "occupancy_rate": self._safe_percentage(
                        len(occupied_slots), total_slots_per_room
                    ),
                    "capacity": getattr(room, "capacidade", 0) or 0,
                }
            )

        room_stats.sort(
            key=lambda room_stat: (
                room_stat["occupancy_rate"],
                room_stat["weekly_minutes"],
                room_stat["room_name"],
            ),
            reverse=True,
        )
        stats["room_stats"] = room_stats
        stats["avg_occupancy"] = (
            sum(room["occupancy_rate"] for room in room_stats) / len(room_stats)
            if room_stats
            else 0.0
        )

        building_stats = defaultdict(
            lambda: {
                "rooms": 0,
                "capacity": 0,
                "occupied_slots": 0,
                "academic_slots": 0,
                "reservation_slots": 0,
                "occupancy_rate": 0.0,
            }
        )
        for room in rooms:
            building_name = buildings.get(room.predio_id, "Desconhecido")
            building_stats[building_name]["rooms"] += 1
            building_stats[building_name]["capacity"] += (
                getattr(room, "capacidade", 0) or 0
            )

        for building_name, slot_set in building_slot_map.items():
            building_stats[building_name]["occupied_slots"] = len(slot_set)
            building_stats[building_name]["academic_slots"] = sum(
                1 for slot in slot_set if slot in academic_slots
            )
            building_stats[building_name]["reservation_slots"] = sum(
                1 for slot in slot_set if slot in reservation_slots
            )
            building_stats[building_name]["occupancy_rate"] = self._safe_percentage(
                len(slot_set),
                building_stats[building_name]["rooms"] * total_slots_per_room,
            )
        stats["building_stats"] = dict(building_stats)

        room_type_stats = defaultdict(
            lambda: {
                "rooms": 0,
                "capacity": 0,
                "occupied_slots": 0,
                "occupancy_rate": 0.0,
            }
        )
        for room in rooms:
            room_type_name = room_types.get(
                room.tipo_sala_id, f"Tipo {room.tipo_sala_id}"
            )
            room_type_stats[room_type_name]["rooms"] += 1
            room_type_stats[room_type_name]["capacity"] += (
                getattr(room, "capacidade", 0) or 0
            )

        for room_type_id, slot_set in room_type_slot_map.items():
            room_type_name = room_types.get(room_type_id, f"Tipo {room_type_id}")
            room_type_stats[room_type_name]["occupied_slots"] = len(slot_set)
            room_type_stats[room_type_name]["occupancy_rate"] = self._safe_percentage(
                len(slot_set),
                room_type_stats[room_type_name]["rooms"] * total_slots_per_room,
            )
        stats["room_type_stats"] = dict(room_type_stats)

        unallocated_demands = []
        for demand in demands:
            if demand.id in demands_allocated:
                continue

            unallocated_demands.append(
                {
                    "codigo": demand.codigo_disciplina,
                    "nome": demand.nome_disciplina,
                    "turma": demand.turma_disciplina or "-",
                    "vagas": demand.vagas_disciplina or 0,
                    "horario": self.parser.parse_to_human_readable(
                        demand.horario_sigaa_bruto or ""
                    )
                    or demand.horario_sigaa_bruto,
                    "professor": demand.professores_disciplina or "-",
                    "curso": demand.codigo_curso or "-",
                }
            )
        unallocated_demands.sort(
            key=lambda demand: (-demand["vagas"], demand["codigo"])
        )
        stats["unallocated_demands"] = unallocated_demands
        stats["unallocated_total_vagas"] = sum(
            demand["vagas"] for demand in unallocated_demands
        )

        capacity_gap_records.sort(
            key=lambda record: (-record["deficit"], -record["vagas"], record["codigo"])
        )
        stats["capacity_gap_records"] = capacity_gap_records
        stats["capacity_gap_count"] = len(capacity_gap_records)
        stats["students_without_seats"] = sum(
            record["deficit"] for record in capacity_gap_records
        )

        stats["time_slot_grid"] = time_slot_grid
        stats["peak_slot"] = self._get_peak_slot(time_slot_grid, stats["total_rooms"])
        stats["busiest_day"] = self._get_busiest_bucket(
            bucket_map=day_slot_usage,
            labels=self.DAY_NAMES,
            denominator=stats["total_rooms"] * len(self.parser.MAP_SCHEDULE_TIMES),
        )
        stats["busiest_shift"] = self._get_busiest_bucket(
            bucket_map=shift_slot_usage,
            labels=self.SHIFT_NAMES,
            denominator_map={
                shift: stats["total_rooms"]
                * len(self.DAY_NAMES)
                * self._count_shift_blocks(shift)
                for shift in self.SHIFT_NAMES
            },
        )

        return stats

    def _build_executive_summary(self, stats: Dict[str, Any]) -> List[Any]:
        """Build executive summary section."""
        elements = [Paragraph("Resumo Executivo", self.styles["SectionHeading"])]

        elements.append(
            Paragraph(
                (
                    "A ocupação consolidada abaixo considera aulas semestrais e "
                    "reservas do tipo semestre inteiro exibidas na visualização."
                ),
                self.styles["StatsText"],
            )
        )
        elements.append(Spacer(1, 5))

        peak_slot = stats.get("peak_slot")
        peak_label = "Nenhum pico identificado"
        if peak_slot:
            peak_label = (
                f"{peak_slot['day_name']} {peak_slot['time_label']} "
                f"({peak_slot['occupancy_rate']:.1f}% das salas)"
            )

        summary_data = [
            ["Métrica", "Valor"],
            ["Salas Cadastradas", f"{stats['total_rooms']} salas"],
            [
                "Salas Utilizadas",
                f"{stats['rooms_used']} salas ({self._safe_percentage(stats['rooms_used'], stats['total_rooms']):.1f}%)",
            ],
            [
                "Salas Sem Uso",
                f"{stats['rooms_unused']} salas ({self._safe_percentage(stats['rooms_unused'], stats['total_rooms']):.1f}%)",
            ],
            ["Demandas Cadastradas", f"{stats['total_demands']} disciplinas"],
            [
                "Demandas Alocadas",
                f"{stats['demands_allocated']} disciplinas ({self._safe_percentage(stats['demands_allocated'], stats['total_demands']):.1f}%)",
            ],
            [
                "Reservas Semestrais",
                f"{stats['total_reservation_slots']} blocos em {stats['rooms_with_reservations']} salas",
            ],
            ["Taxa de Ocupação Média", f"{stats['avg_occupancy']:.1f}%"],
            [
                "Déficit de Capacidade",
                (
                    f"{stats['capacity_gap_count']} alocações "
                    f"({stats['students_without_seats']} alunos sem assento estimados)"
                ),
            ],
            ["Maior Pico de Ocupação", peak_label],
        ]

        table = Table(summary_data, colWidths=[100 * mm, 60 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    *[
                        (
                            "BACKGROUND",
                            (0, index),
                            (-1, index),
                            colors.HexColor("#f5f5f5"),
                        )
                        for index in range(1, len(summary_data), 2)
                    ],
                ]
            )
        )
        elements.append(table)

        busiest_day = stats.get("busiest_day")
        busiest_shift = stats.get("busiest_shift")
        if busiest_day or busiest_shift:
            elements.append(Spacer(1, 5))
            summary_notes = []
            if busiest_day:
                summary_notes.append(
                    f"Dia mais carregado: <b>{busiest_day['label']}</b> ({busiest_day['occupancy_rate']:.1f}% da capacidade semanal do dia)."
                )
            if busiest_shift:
                summary_notes.append(
                    f"Turno mais carregado: <b>{busiest_shift['label']}</b> ({busiest_shift['occupancy_rate']:.1f}% da capacidade semanal do turno)."
                )
            elements.append(
                Paragraph(" ".join(summary_notes), self.styles["StatsText"])
            )

        return elements

    def _build_room_utilization(self, stats: Dict[str, Any]) -> List[Any]:
        """Build room utilization section."""
        elements = [Paragraph("Utilização de Salas", self.styles["SectionHeading"])]

        room_stats = [
            room for room in stats["room_stats"] if room["occupied_slots"] > 0
        ]

        if room_stats:
            elements.append(
                Paragraph(
                    "<b>Top 5 Salas Mais Utilizadas</b>", self.styles["StatsText"]
                )
            )
            elements.append(Spacer(1, 3))

            top_data = [["Sala", "Carga/Sem", "Blocos", "% Ocupação"]]
            for room in room_stats[:5]:
                top_data.append(
                    [
                        room["room_name"],
                        self._format_duration(room["weekly_minutes"]),
                        str(room["occupied_slots"]),
                        f"{room['occupancy_rate']:.1f}%",
                    ]
                )

            top_table = Table(top_data, colWidths=[78 * mm, 28 * mm, 24 * mm, 30 * mm])
            top_table.setStyle(
                self._build_table_style(
                    header_color="#1f4788",
                    row_count=len(top_data),
                )
            )
            elements.append(top_table)
            elements.append(Spacer(1, 8))

        underutilized = [
            room
            for room in stats["room_stats"]
            if 0 < room["occupied_slots"] and room["occupancy_rate"] < 30
        ]
        if underutilized:
            elements.append(
                Paragraph(
                    "<b>Salas Subutilizadas (ocupação menor que 30%)</b>",
                    self.styles["StatsText"],
                )
            )
            elements.append(Spacer(1, 3))

            bottom_data = [["Sala", "Tipo", "Carga/Sem", "% Ocupação"]]
            for room in underutilized[:5]:
                bottom_data.append(
                    [
                        room["room_name"],
                        self._truncate_text(room["room_type"], 18),
                        self._format_duration(room["weekly_minutes"]),
                        f"{room['occupancy_rate']:.1f}%",
                    ]
                )

            bottom_table = Table(
                bottom_data, colWidths=[65 * mm, 40 * mm, 28 * mm, 27 * mm]
            )
            bottom_table.setStyle(
                self._build_table_style(
                    header_color="#ff9800",
                    row_count=len(bottom_data),
                )
            )
            elements.append(bottom_table)

        if stats["unused_rooms"]:
            elements.append(Spacer(1, 8))
            elements.append(
                Paragraph("<b>Salas Sem Uso no Semestre</b>", self.styles["StatsText"])
            )
            elements.append(Spacer(1, 3))
            room_list = ", ".join(stats["unused_rooms"][:8])
            if len(stats["unused_rooms"]) > 8:
                room_list += f" e mais {len(stats['unused_rooms']) - 8}."
            elements.append(Paragraph(room_list, self.styles["StatsText"]))

        return elements

    def _build_capacity_analysis(self, stats: Dict[str, Any]) -> List[Any]:
        """Build capacity fit section."""
        elements = [
            Paragraph("Capacidade e Atendimento", self.styles["SectionHeading"])
        ]

        if not stats["capacity_gap_records"]:
            elements.append(
                Paragraph(
                    "✅ Nenhuma alocação com déficit de assentos foi encontrada.",
                    self.styles["StatsText"],
                )
            )
            return elements

        elements.append(
            Paragraph(
                (
                    f"<b>{stats['capacity_gap_count']} alocações</b> apresentam sala "
                    f"com capacidade inferior à demanda, somando "
                    f"<b>{stats['students_without_seats']} alunos</b> sem assento estimados."
                ),
                self.styles["StatsText"],
            )
        )
        elements.append(Spacer(1, 5))

        capacity_data = [["Disciplina", "Sala", "Vagas", "Capac.", "Déficit"]]
        for record in stats["capacity_gap_records"][:6]:
            discipline_label = f"{record['codigo']} / {record['turma']}"
            capacity_data.append(
                [
                    self._truncate_text(discipline_label, 26),
                    self._truncate_text(record["room_name"], 26),
                    str(record["vagas"]),
                    str(record["capacidade"]),
                    str(record["deficit"]),
                ]
            )

        capacity_table = Table(
            capacity_data,
            colWidths=[50 * mm, 55 * mm, 18 * mm, 18 * mm, 18 * mm],
        )
        capacity_table.setStyle(
            self._build_table_style(
                header_color="#d32f2f",
                row_count=len(capacity_data),
            )
        )
        elements.append(capacity_table)

        if len(stats["capacity_gap_records"]) > 6:
            elements.append(Spacer(1, 3))
            elements.append(
                Paragraph(
                    f"<i>... e mais {len(stats['capacity_gap_records']) - 6} casos de déficit de capacidade.</i>",
                    self.styles["StatsText"],
                )
            )

        return elements

    def _build_time_slot_heatmap(self, stats: Dict[str, Any]) -> List[Any]:
        """Build time slot heatmap section."""
        elements = [
            Paragraph("Mapa de Ocupação por Horário", self.styles["SectionHeading"])
        ]

        if stats["total_reservation_slots"] > 0:
            elements.append(
                Paragraph(
                    (
                        "O mapa abaixo inclui aulas semestrais e reservas do tipo "
                        "semestre inteiro para representar a ocupação real da grade."
                    ),
                    self.styles["StatsText"],
                )
            )
            elements.append(Spacer(1, 5))

        time_slot_grid = stats["time_slot_grid"]
        total_rooms = stats["total_rooms"]
        time_blocks = sorted(
            self.parser.MAP_SCHEDULE_TIMES.keys(), key=self._sort_time_block
        )

        heatmap_data = [
            ["Horário"] + [self.DAY_NAMES[day] for day in sorted(self.DAY_NAMES)]
        ]

        for block in time_blocks:
            block_info = self.parser.MAP_SCHEDULE_TIMES.get(block, {})
            row = [block_info.get("inicio", block)]

            for day in sorted(self.DAY_NAMES):
                rooms_occupied = len(time_slot_grid[block].get(day, set()))
                row.append(f"{self._safe_percentage(rooms_occupied, total_rooms):.0f}%")

            heatmap_data.append(row)

        heatmap_table = Table(heatmap_data, colWidths=[25 * mm] + [22 * mm] * 6)

        table_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#e8eaf6")),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (0, -1), 7),
            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ("FONTNAME", (1, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (1, 1), (-1, -1), 7),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]

        for row_index in range(1, len(heatmap_data)):
            for column_index in range(1, len(heatmap_data[row_index])):
                occupancy = float(heatmap_data[row_index][column_index].rstrip("%"))
                if occupancy >= 70:
                    background = colors.HexColor("#ffcdd2")
                elif occupancy >= 40:
                    background = colors.HexColor("#fff9c4")
                else:
                    background = colors.HexColor("#c8e6c9")
                table_styles.append(
                    (
                        "BACKGROUND",
                        (column_index, row_index),
                        (column_index, row_index),
                        background,
                    )
                )

        heatmap_table.setStyle(TableStyle(table_styles))
        elements.append(heatmap_table)

        peak_slot = stats.get("peak_slot")
        if peak_slot:
            elements.append(Spacer(1, 5))
            elements.append(
                Paragraph(
                    (
                        f"Pico registrado em <b>{peak_slot['day_name']} {peak_slot['time_label']}</b> "
                        f"com <b>{peak_slot['rooms_occupied']}</b> salas ocupadas "
                        f"({peak_slot['occupancy_rate']:.1f}% do inventário)."
                    ),
                    self.styles["StatsText"],
                )
            )

        elements.append(Spacer(1, 5))
        elements.append(
            Paragraph(
                "<i>vermelho >70% Alta  |  amarelo 40-69% Média  |  verde <40% Baixa</i>",
                ParagraphStyle(
                    "Legend",
                    parent=self.styles["StatsText"],
                    fontSize=7,
                    alignment=TA_CENTER,
                ),
            )
        )

        return elements

    def _build_building_analysis(self, stats: Dict[str, Any]) -> List[Any]:
        """Build building-level analysis section."""
        elements = [Paragraph("Utilização por Prédio", self.styles["SectionHeading"])]

        building_stats = stats["building_stats"]
        if not building_stats:
            elements.append(
                Paragraph(
                    "Nenhum dado por prédio disponível.", self.styles["StatsText"]
                )
            )
            return elements

        building_data = [["Prédio", "Salas", "Blocos", "% Ocupação", "Capacidade"]]
        for building_name, building_stat in sorted(building_stats.items()):
            building_data.append(
                [
                    building_name,
                    str(building_stat["rooms"]),
                    str(building_stat["occupied_slots"]),
                    f"{building_stat['occupancy_rate']:.1f}%",
                    f"{building_stat['capacity']} lugares",
                ]
            )

        building_table = Table(
            building_data, colWidths=[45 * mm, 20 * mm, 25 * mm, 30 * mm, 40 * mm]
        )
        building_table.setStyle(
            self._build_table_style(
                header_color="#1f4788",
                row_count=len(building_data),
            )
        )
        elements.append(building_table)
        return elements

    def _build_room_type_analysis(self, stats: Dict[str, Any]) -> List[Any]:
        """Build room type utilization section."""
        elements = [
            Paragraph("Utilização por Tipo de Sala", self.styles["SectionHeading"])
        ]

        room_type_stats = stats["room_type_stats"]
        if not room_type_stats:
            elements.append(
                Paragraph(
                    "Nenhum dado por tipo de sala disponível.", self.styles["StatsText"]
                )
            )
            return elements

        type_data = [["Tipo de Sala", "Salas", "Blocos", "% Ocupação", "Capacidade"]]
        for room_type_name, room_type_stat in sorted(room_type_stats.items()):
            type_data.append(
                [
                    self._truncate_text(room_type_name, 28),
                    str(room_type_stat["rooms"]),
                    str(room_type_stat["occupied_slots"]),
                    f"{room_type_stat['occupancy_rate']:.1f}%",
                    f"{room_type_stat['capacity']} lugares",
                ]
            )

        type_table = Table(
            type_data, colWidths=[55 * mm, 18 * mm, 24 * mm, 28 * mm, 35 * mm]
        )
        type_table.setStyle(
            self._build_table_style(
                header_color="#455a64",
                row_count=len(type_data),
            )
        )
        elements.append(type_table)
        return elements

    def _build_unallocated_demands(self, stats: Dict[str, Any]) -> List[Any]:
        """Build unallocated demands section."""
        elements = [Paragraph("Demandas Não Alocadas", self.styles["SectionHeading"])]

        unallocated = stats["unallocated_demands"]
        if not unallocated:
            elements.append(
                Paragraph(
                    "✅ Todas as demandas foram alocadas com sucesso.",
                    self.styles["StatsText"],
                )
            )
            return elements

        elements.append(
            Paragraph(
                (
                    f"<b>Total: {len(unallocated)} disciplinas não alocadas</b> "
                    f"({stats['unallocated_total_vagas']} vagas pendentes)."
                ),
                self.styles["StatsText"],
            )
        )
        elements.append(Spacer(1, 5))

        demand_data = [["Código", "Disciplina", "Turma", "Vagas", "Horário"]]
        for demand in unallocated[:12]:
            demand_data.append(
                [
                    demand["codigo"],
                    self._truncate_text(demand["nome"], 34),
                    demand["turma"],
                    str(demand["vagas"]),
                    self._truncate_text(demand["horario"], 32),
                ]
            )

        demand_table = Table(
            demand_data, colWidths=[22 * mm, 63 * mm, 18 * mm, 18 * mm, 49 * mm]
        )
        demand_table.setStyle(
            self._build_table_style(
                header_color="#f44336",
                row_count=len(demand_data),
            )
        )
        elements.append(demand_table)

        if len(unallocated) > 12:
            elements.append(Spacer(1, 3))
            elements.append(
                Paragraph(
                    f"<i>... e mais {len(unallocated) - 12} disciplinas não alocadas.</i>",
                    self.styles["StatsText"],
                )
            )

        return elements

    def _build_table_style(self, header_color: str, row_count: int) -> TableStyle:
        """Build a reusable table style with zebra striping."""
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                *[
                    (
                        "BACKGROUND",
                        (0, row_index),
                        (-1, row_index),
                        colors.HexColor("#f5f5f5"),
                    )
                    for row_index in range(1, row_count, 2)
                ],
            ]
        )

    def _build_room_name(self, room: Any, buildings: Dict[int, str]) -> str:
        """Build a display name for a room."""
        building_name = buildings.get(room.predio_id, "Desconhecido")
        return f"{building_name}: {room.nome}"

    def _flatten_semester_reservations(
        self, semester_reservations_by_room: Dict[int, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Flatten per-room reservation payloads into a normalized list."""
        flattened = []

        for room_id, reservations in semester_reservations_by_room.items():
            for reservation in reservations:
                day_id = reservation.get("day_id") or reservation.get("dia_semana_id")
                block_code = reservation.get("codigo_bloco")
                if not day_id or not block_code:
                    continue

                flattened.append(
                    {
                        "room_id": room_id,
                        "day_id": day_id,
                        "codigo_bloco": block_code,
                        "titulo": reservation.get("titulo", ""),
                    }
                )

        return flattened

    def _slot_duration_minutes(self, block_code: str) -> int:
        """Return the real duration in minutes for an atomic SIGAA block."""
        block_info = self.parser.MAP_SCHEDULE_TIMES.get(block_code, {})
        start_time = block_info.get("inicio")
        end_time = block_info.get("fim")
        if not start_time or not end_time:
            return 0

        start_hours, start_minutes = map(int, start_time.split(":"))
        end_hours, end_minutes = map(int, end_time.split(":"))
        return (end_hours * 60 + end_minutes) - (start_hours * 60 + start_minutes)

    def _format_duration(self, total_minutes: int) -> str:
        """Format minutes as a compact weekly workload label."""
        if total_minutes <= 0:
            return "-"

        hours, minutes = divmod(total_minutes, 60)
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h{minutes:02d}"

    def _safe_percentage(self, numerator: int, denominator: int) -> float:
        """Safely calculate percentage values."""
        if denominator <= 0:
            return 0.0
        return (numerator / denominator) * 100

    def _get_peak_slot(
        self,
        time_slot_grid: Dict[str, Dict[int, set]],
        total_rooms: int,
    ) -> Optional[Dict[str, Any]]:
        """Return the busiest day/block pair in the semester grid."""
        peak_slot = None

        for block_code, day_map in time_slot_grid.items():
            for day_id, room_ids in day_map.items():
                rooms_occupied = len(room_ids)
                if peak_slot is None or rooms_occupied > peak_slot["rooms_occupied"]:
                    peak_slot = {
                        "day_id": day_id,
                        "day_name": self.DAY_NAMES.get(day_id, str(day_id)),
                        "block_code": block_code,
                        "time_label": self._get_block_time_label(block_code),
                        "rooms_occupied": rooms_occupied,
                        "occupancy_rate": self._safe_percentage(
                            rooms_occupied, total_rooms
                        ),
                    }

        return peak_slot

    def _get_busiest_bucket(
        self,
        bucket_map: Dict[Any, set],
        labels: Dict[Any, str],
        denominator: Optional[int] = None,
        denominator_map: Optional[Dict[Any, int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the busiest labeled bucket by occupied slot count."""
        if not bucket_map:
            return None

        bucket_key, bucket_slots = max(
            bucket_map.items(), key=lambda item: len(item[1])
        )
        bucket_denominator = (
            denominator_map.get(bucket_key, 0)
            if denominator_map is not None
            else (denominator or 0)
        )
        return {
            "key": bucket_key,
            "label": labels.get(bucket_key, str(bucket_key)),
            "slot_count": len(bucket_slots),
            "occupancy_rate": self._safe_percentage(
                len(bucket_slots), bucket_denominator
            ),
        }

    def _count_shift_blocks(self, shift_code: str) -> int:
        """Count how many atomic blocks exist for a shift."""
        return sum(
            1
            for block_code in self.parser.MAP_SCHEDULE_TIMES
            if block_code.startswith(shift_code)
        )

    def _get_block_time_label(self, block_code: str) -> str:
        """Return a readable time label for a block code."""
        block_info = self.parser.MAP_SCHEDULE_TIMES.get(block_code, {})
        start_time = block_info.get("inicio", block_code)
        end_time = block_info.get("fim", block_code)
        return f"{start_time}-{end_time}"

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncate text for compact PDF tables."""
        text = text or "-"
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    def _sort_time_block(self, block_code: str) -> int:
        """Sort time blocks chronologically."""
        block_info = self.parser.MAP_SCHEDULE_TIMES.get(block_code, {})
        start_time = block_info.get("inicio", "00:00")

        try:
            hours, minutes = map(int, start_time.split(":"))
            return hours * 60 + minutes
        except (ValueError, AttributeError):
            return 0
