"""
Statistics Report Generation Service

Creates comprehensive statistics reports for room allocation analysis.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import io
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from src.utils.cache_helpers import get_sigaa_parser


class StatisticsReportService:
    """Service for generating statistics reports of room allocations."""

    def __init__(self):
        """Initialize statistics report service."""
        self.parser = get_sigaa_parser()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        # Title style
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

        # Section heading
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

        # Normal text
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

        # Table header
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

        # Table cell
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
    ) -> bytes:
        """
        Generate comprehensive statistics report.

        Args:
            allocations: List of allocation objects
            demands: List of all demand objects
            rooms: List of all room objects
            buildings: Dict mapping building_id to building name
            semester_name: Name of the semester (e.g., "2025-1")

        Returns:
            bytes: PDF file content
        """
        buffer = io.BytesIO()

        # Create PDF document
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

        # Build document content
        story = []

        # Title
        title = Paragraph(
            f"Estatísticas de Ensalamento<br/>Semestre {semester_name}",
            self.styles["ReportTitle"],
        )
        story.append(title)
        story.append(Spacer(1, 10))

        # Calculate statistics
        stats = self._calculate_statistics(allocations, demands, rooms, buildings)

        # 1. Executive Summary
        story.extend(self._build_executive_summary(stats))
        story.append(Spacer(1, 10))

        # 2. Room Utilization
        story.extend(self._build_room_utilization(stats))
        story.append(Spacer(1, 10))

        # 3. Time Slot Heatmap (new page)
        story.append(PageBreak())
        story.extend(self._build_time_slot_heatmap(stats))
        story.append(Spacer(1, 10))

        # 4. Building-Level Analysis
        story.extend(self._build_building_analysis(stats))
        story.append(Spacer(1, 10))

        # 5. Unallocated Demands
        story.extend(self._build_unallocated_demands(stats))

        # Build PDF
        doc.build(story)

        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content

    def _calculate_statistics(
        self,
        allocations: List[Any],
        demands: List[Any],
        rooms: List[Any],
        buildings: Dict[int, str],
    ) -> Dict[str, Any]:
        """Calculate all statistics needed for the report."""
        stats = {}

        # Basic counts
        stats["total_rooms"] = len(rooms)
        stats["total_demands"] = len(demands)
        stats["total_allocations"] = len(allocations)

        # Rooms used
        rooms_used = set(alloc.sala_id for alloc in allocations)
        stats["rooms_used"] = len(rooms_used)
        stats["rooms_unused"] = stats["total_rooms"] - stats["rooms_used"]

        # Demands allocated
        demands_allocated = set(
            alloc.demanda_id for alloc in allocations if alloc.demanda_id
        )
        stats["demands_allocated"] = len(demands_allocated)
        stats["demands_unallocated"] = (
            stats["total_demands"] - stats["demands_allocated"]
        )

        # Room utilization (allocations per room)
        room_allocations = defaultdict(list)
        for alloc in allocations:
            room_allocations[alloc.sala_id].append(alloc)

        # Create room lookup
        room_lookup = {room.id: room for room in rooms}

        # Calculate utilization per room
        room_stats = []
        for room_id, allocs in room_allocations.items():
            room = room_lookup.get(room_id)
            if not room:
                continue

            building_name = buildings.get(room.predio_id, "Desconhecido")
            room_name = f"{building_name}: {room.nome}"

            # Calculate total hours (each allocation = 1 block ~= 1 hour)
            total_hours = len(allocs)

            # Calculate occupancy rate (assuming 48 possible slots per week: 6 days × 15 blocks - rough estimate)
            # More accurate: count unique (day, block) combinations
            unique_slots = set((a.dia_semana_id, a.codigo_bloco) for a in allocs)
            max_slots = 6 * 15  # 6 days × 15 time blocks (M1-M5, T1-T6, N1-N4)
            occupancy_rate = (len(unique_slots) / max_slots) * 100

            room_stats.append(
                {
                    "room_id": room_id,
                    "room_name": room_name,
                    "allocations": len(allocs),
                    "hours_per_week": total_hours,
                    "occupancy_rate": occupancy_rate,
                    "capacity": room.capacidade,
                }
            )

        # Sort by occupancy rate
        room_stats.sort(key=lambda x: x["occupancy_rate"], reverse=True)
        stats["room_stats"] = room_stats

        # Average occupancy
        if room_stats:
            stats["avg_occupancy"] = sum(r["occupancy_rate"] for r in room_stats) / len(
                room_stats
            )
        else:
            stats["avg_occupancy"] = 0.0

        # Time slot heatmap (day × time block)
        time_slot_grid = defaultdict(lambda: defaultdict(set))
        for alloc in allocations:
            day = alloc.dia_semana_id
            block = alloc.codigo_bloco
            time_slot_grid[block][day].add(alloc.sala_id)

        stats["time_slot_grid"] = time_slot_grid

        # Building-level stats
        building_stats = defaultdict(
            lambda: {"rooms": 0, "allocations": 0, "capacity": 0}
        )
        for room in rooms:
            building_name = buildings.get(room.predio_id, "Desconhecido")
            building_stats[building_name]["rooms"] += 1
            building_stats[building_name]["capacity"] += room.capacidade or 0

        for alloc in allocations:
            room = room_lookup.get(alloc.sala_id)
            if room:
                building_name = buildings.get(room.predio_id, "Desconhecido")
                building_stats[building_name]["allocations"] += 1

        # Calculate building occupancy
        for building_name, bstats in building_stats.items():
            # Each room has max_slots possible allocations
            max_possible = bstats["rooms"] * 90  # 6 days × 15 blocks
            if max_possible > 0:
                bstats["occupancy_rate"] = (bstats["allocations"] / max_possible) * 100
            else:
                bstats["occupancy_rate"] = 0.0

        stats["building_stats"] = dict(building_stats)

        # Unallocated demands
        unallocated_demands = []
        for demand in demands:
            if demand.id not in demands_allocated:
                unallocated_demands.append(
                    {
                        "codigo": demand.codigo_disciplina,
                        "nome": demand.nome_disciplina,
                        "turma": demand.turma_disciplina,
                        "vagas": demand.vagas_disciplina,
                        "horario": demand.horario_sigaa_bruto,
                    }
                )

        stats["unallocated_demands"] = unallocated_demands

        return stats

    def _build_executive_summary(self, stats: Dict[str, Any]) -> List:
        """Build executive summary section."""
        elements = []

        # Section heading
        heading = Paragraph("Resumo Executivo", self.styles["SectionHeading"])
        elements.append(heading)

        # Summary data
        summary_data = [
            ["Métrica", "Valor"],
            ["Salas Cadastradas", f"{stats['total_rooms']} salas"],
            [
                "Salas Utilizadas",
                f"{stats['rooms_used']} salas ({(stats['rooms_used']/stats['total_rooms']*100):.1f}%)",
            ],
            ["Demandas Cadastradas", f"{stats['total_demands']} disciplinas"],
            [
                "Demandas Alocadas",
                f"{stats['demands_allocated']} disciplinas ({(stats['demands_allocated']/stats['total_demands']*100 if stats['total_demands'] > 0 else 0):.1f}%)",
            ],
            ["Taxa de Ocupação Média", f"{stats['avg_occupancy']:.1f}%"],
            ["Total de Alocações", f"{stats['total_allocations']} alocações"],
        ]

        table = Table(summary_data, colWidths=[100 * mm, 60 * mm])
        table.setStyle(
            TableStyle(
                [
                    # Header row
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Data rows
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    # Grid
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    # Zebra striping
                    *[
                        ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f5f5f5"))
                        for i in range(1, len(summary_data), 2)
                    ],
                ]
            )
        )

        elements.append(table)

        return elements

    def _build_room_utilization(self, stats: Dict[str, Any]) -> List:
        """Build room utilization section."""
        elements = []

        # Section heading
        heading = Paragraph("Utilização de Salas", self.styles["SectionHeading"])
        elements.append(heading)

        room_stats = stats["room_stats"]

        # Top 5 most utilized
        if room_stats:
            elements.append(
                Paragraph(
                    "<b>Top 5 Salas Mais Utilizadas</b>", self.styles["StatsText"]
                )
            )
            elements.append(Spacer(1, 3))

            top_5 = room_stats[:5]
            top_data = [["Sala", "Alocações", "Horas/Sem", "% Ocupação"]]
            for room in top_5:
                top_data.append(
                    [
                        room["room_name"],
                        str(room["allocations"]),
                        f"{room['hours_per_week']}h",
                        f"{room['occupancy_rate']:.1f}%",
                    ]
                )

            top_table = Table(top_data, colWidths=[70 * mm, 30 * mm, 30 * mm, 30 * mm])
            top_table.setStyle(
                TableStyle(
                    [
                        # Header
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        # Data
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("ALIGN", (0, 1), (0, -1), "LEFT"),
                        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )

            elements.append(top_table)
            elements.append(Spacer(1, 8))

        # Bottom 5 underutilized (< 30%)
        underutilized = [r for r in room_stats if r["occupancy_rate"] < 30]
        if underutilized:
            elements.append(
                Paragraph(
                    "<b>Salas Subutilizadas (< 30%)</b>", self.styles["StatsText"]
                )
            )
            elements.append(Spacer(1, 3))

            bottom_5 = underutilized[:5]
            bottom_data = [["Sala", "Alocações", "Horas/Sem", "% Ocupação"]]
            for room in bottom_5:
                bottom_data.append(
                    [
                        room["room_name"],
                        str(room["allocations"]),
                        f"{room['hours_per_week']}h",
                        f"{room['occupancy_rate']:.1f}%",
                    ]
                )

            bottom_table = Table(
                bottom_data, colWidths=[70 * mm, 30 * mm, 30 * mm, 30 * mm]
            )
            bottom_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ff9800")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("ALIGN", (0, 1), (0, -1), "LEFT"),
                        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )

            elements.append(bottom_table)

        return elements

    def _build_time_slot_heatmap(self, stats: Dict[str, Any]) -> List:
        """Build time slot heatmap section."""
        elements = []

        # Section heading
        heading = Paragraph(
            "Mapa de Ocupação por Horário", self.styles["SectionHeading"]
        )
        elements.append(heading)

        time_slot_grid = stats["time_slot_grid"]
        total_rooms = stats["total_rooms"]

        # Get sorted time blocks
        time_blocks = sorted(
            self.parser.MAP_SCHEDULE_TIMES.keys(), key=self._sort_time_block
        )

        # Day mapping
        day_names = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}

        # Build heatmap data (percentage of rooms occupied)
        heatmap_data = [["Horário"] + [day_names[d] for d in sorted(day_names.keys())]]

        for block in time_blocks:
            block_info = self.parser.MAP_SCHEDULE_TIMES.get(block, {})
            start_time = block_info.get("inicio", block)

            row = [start_time]

            for day in sorted(day_names.keys()):
                rooms_occupied = len(time_slot_grid[block].get(day, set()))
                if total_rooms > 0:
                    occupancy_pct = (rooms_occupied / total_rooms) * 100
                else:
                    occupancy_pct = 0
                row.append(f"{occupancy_pct:.0f}%")

            heatmap_data.append(row)

        heatmap_table = Table(heatmap_data, colWidths=[25 * mm] + [22 * mm] * 6)

        # Style with color coding
        table_styles = [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            # Time column
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#e8eaf6")),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (0, -1), 7),
            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            # Data cells
            ("FONTNAME", (1, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (1, 1), (-1, -1), 7),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]

        # Color code cells based on occupancy
        for i in range(1, len(heatmap_data)):
            for j in range(1, len(heatmap_data[i])):
                try:
                    occupancy = float(heatmap_data[i][j].rstrip("%"))
                    if occupancy >= 70:
                        # High occupancy - red
                        bg_color = colors.HexColor("#ffcdd2")
                    elif occupancy >= 40:
                        # Medium occupancy - yellow
                        bg_color = colors.HexColor("#fff9c4")
                    else:
                        # Low occupancy - green
                        bg_color = colors.HexColor("#c8e6c9")

                    table_styles.append(("BACKGROUND", (j, i), (j, i), bg_color))
                except ValueError:
                    pass

        heatmap_table.setStyle(TableStyle(table_styles))

        elements.append(heatmap_table)

        # Legend
        elements.append(Spacer(1, 5))
        legend_text = "vermelho >70% Alta  |  amarelo 40-69% Média  |  verde <40% Baixa"
        elements.append(
            Paragraph(
                f"<i>{legend_text}</i>",
                ParagraphStyle(
                    "Legend",
                    parent=self.styles["StatsText"],
                    fontSize=7,
                    alignment=TA_CENTER,
                ),
            )
        )

        return elements

    def _build_building_analysis(self, stats: Dict[str, Any]) -> List:
        """Build building-level analysis section."""
        elements = []

        # Section heading
        heading = Paragraph("Utilização por Prédio", self.styles["SectionHeading"])
        elements.append(heading)

        building_stats = stats["building_stats"]

        if building_stats:
            building_data = [
                ["Prédio", "Salas", "Alocações", "% Ocupação", "Capacidade"]
            ]

            for building_name, bstats in sorted(building_stats.items()):
                building_data.append(
                    [
                        building_name,
                        str(bstats["rooms"]),
                        str(bstats["allocations"]),
                        f"{bstats['occupancy_rate']:.1f}%",
                        f"{bstats['capacity']} lugares",
                    ]
                )

            building_table = Table(
                building_data, colWidths=[40 * mm, 25 * mm, 30 * mm, 30 * mm, 35 * mm]
            )
            building_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("ALIGN", (0, 1), (0, -1), "LEFT"),
                        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        *[
                            ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f5f5f5"))
                            for i in range(1, len(building_data), 2)
                        ],
                    ]
                )
            )

            elements.append(building_table)

        return elements

    def _build_unallocated_demands(self, stats: Dict[str, Any]) -> List:
        """Build unallocated demands section."""
        elements = []

        # Section heading
        heading = Paragraph("Demandas Não Alocadas", self.styles["SectionHeading"])
        elements.append(heading)

        unallocated = stats["unallocated_demands"]

        if unallocated:
            elements.append(
                Paragraph(
                    f"<b>Total: {len(unallocated)} disciplinas não alocadas</b>",
                    self.styles["StatsText"],
                )
            )
            elements.append(Spacer(1, 5))

            # Show first 10
            demand_data = [["Código", "Disciplina", "Turma", "Vagas", "Horário"]]

            for demand in unallocated[:10]:
                demand_data.append(
                    [
                        demand["codigo"],
                        (
                            demand["nome"][:30] + "..."
                            if len(demand["nome"]) > 30
                            else demand["nome"]
                        ),
                        demand["turma"] or "-",
                        str(demand["vagas"]),
                        demand["horario"],
                    ]
                )

            demand_table = Table(
                demand_data, colWidths=[25 * mm, 55 * mm, 20 * mm, 20 * mm, 40 * mm]
            )
            demand_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f44336")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 7),
                        ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                        ("ALIGN", (3, 1), (3, -1), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )

            elements.append(demand_table)

            if len(unallocated) > 10:
                elements.append(Spacer(1, 3))
                elements.append(
                    Paragraph(
                        f"<i>... e mais {len(unallocated) - 10} disciplinas não alocadas.</i>",
                        self.styles["StatsText"],
                    )
                )
        else:
            elements.append(
                Paragraph(
                    "✅ Todas as demandas foram alocadas com sucesso!",
                    self.styles["StatsText"],
                )
            )

        return elements

    def _sort_time_block(self, block_code: str) -> int:
        """Sort time blocks chronologically."""
        block_info = self.parser.MAP_SCHEDULE_TIMES.get(block_code, {})
        start_time = block_info.get("inicio", "00:00")

        try:
            hours, minutes = map(int, start_time.split(":"))
            return hours * 60 + minutes
        except (ValueError, AttributeError):
            return 0
