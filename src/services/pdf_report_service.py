"""
PDF Report Generation Service

Creates formatted PDF reports for room allocation schedules.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from src.utils.cache_helpers import get_sigaa_parser


class PDFReportService:
    """Service for generating PDF reports of room allocations."""

    # Arial Narrow font names
    FONT_REGULAR = "ArialNarrow"
    FONT_BOLD = "ArialNarrow-Bold"

    def __init__(self):
        """Initialize PDF report service."""
        self.parser = get_sigaa_parser()
        self._register_narrow_fonts()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _register_narrow_fonts(self):
        """Register Arial Narrow fonts from the static folder."""
        import os

        # Get the project root directory (where static folder is located)
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        static_dir = os.path.join(project_root, "static")

        try:
            pdfmetrics.registerFont(
                TTFont(self.FONT_REGULAR, os.path.join(static_dir, "arialnarrow.ttf"))
            )
            pdfmetrics.registerFont(
                TTFont(self.FONT_BOLD, os.path.join(static_dir, "arialnarrow_bold.ttf"))
            )
            # Register font family so ReportLab can map between regular/bold variants
            pdfmetrics.registerFontFamily(
                self.FONT_REGULAR,
                normal=self.FONT_REGULAR,
                bold=self.FONT_BOLD,
            )
        except Exception:
            # Fallback to Helvetica if Arial Narrow not available
            type(self).FONT_REGULAR = "Helvetica"
            type(self).FONT_BOLD = "Helvetica-Bold"

    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        # Title style - more compact
        self.styles.add(
            ParagraphStyle(
                name="RoomTitle",
                parent=self.styles["Heading1"],
                fontSize=12,
                textColor=colors.HexColor("#1f4788"),
                spaceAfter=3,
                spaceBefore=0,
                alignment=TA_CENTER,
                fontName=self.FONT_BOLD,
            )
        )

        # Cell content style - smaller fonts
        self.styles.add(
            ParagraphStyle(
                name="CellContent",
                parent=self.styles["Normal"],
                fontSize=8,
                leading=9,
                alignment=TA_LEFT,
                fontName=self.FONT_REGULAR,
                leftIndent=1,
                rightIndent=1,
            )
        )

        # Time slot style - smaller
        self.styles.add(
            ParagraphStyle(
                name="TimeSlot",
                parent=self.styles["Normal"],
                fontSize=8,
                leading=9,
                alignment=TA_CENTER,
                fontName=self.FONT_BOLD,
            )
        )

        # Header style - smaller
        self.styles.add(
            ParagraphStyle(
                name="DayHeader",
                parent=self.styles["Normal"],
                fontSize=9,
                alignment=TA_CENTER,
                fontName=self.FONT_BOLD,
                textColor=colors.white,
            )
        )

    def generate_allocation_report(
        self,
        room_allocations: Dict[int, Dict[str, Any]],
        semester_name: str,
        selected_room_id: Optional[int] = None,
        portrait_mode: bool = False,
    ) -> bytes:
        """
        Generate PDF report for room allocations.

        Args:
            room_allocations: Dictionary mapping room_id to allocation data
            semester_name: Name of the semester (e.g., "2025-1")
            selected_room_id: If provided, generate report only for this room

        Returns:
            bytes: PDF file content
        """
        buffer = io.BytesIO()

        # Set page size and margins based on orientation
        if portrait_mode:
            page_size = A4  # Portrait A4
            # Portrait A4 = 210mm width - 12mm margins = 198mm available (same as landscape)
            # Time column: 18mm (increased for better time display), Day columns: (198-18)/6 = 30mm each
            right_margin = 6 * mm
            left_margin = 6 * mm
            time_col_width = 18 * mm
            day_col_width = 30 * mm
        else:
            page_size = landscape(A4)  # Landscape A4 (default)
            # Landscape A4 = 297mm width - 12mm margins = 285mm available
            # Time column: 18mm, Day columns: (285-18)/6 = 44.5mm each
            right_margin = 6 * mm
            left_margin = 6 * mm
            time_col_width = 18 * mm
            day_col_width = 44.5 * mm

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            rightMargin=right_margin,
            leftMargin=left_margin,
            topMargin=4 * mm,
            bottomMargin=4 * mm,
            title=f"Ensalamento {semester_name}",
            author="Sistema de Ensalamento FUP/UnB",
        )

        # Build document content
        story = []

        # Filter rooms if specific room selected
        rooms_to_process = room_allocations
        if selected_room_id and selected_room_id in room_allocations:
            rooms_to_process = {selected_room_id: room_allocations[selected_room_id]}

        # Generate one page per room
        for room_id, room_data in rooms_to_process.items():
            room_name = room_data["room_name"]
            allocations = room_data["allocations"]

            # Format room name: convert "UAC: AT-42/12" to "AT-42/12 (UAC)"
            if ":" in room_name:
                parts = room_name.split(":", 1)
                building = parts[0].strip()
                room = parts[1].strip()
                formatted_room_name = f"{room} ({building})"
            else:
                formatted_room_name = room_name

            # Add room title - compact
            title_text = f"Sala: {formatted_room_name}"
            title = Paragraph(title_text, self.styles["RoomTitle"])
            story.append(title)
            story.append(Spacer(1, 0))

            # Build schedule table
            table_data = self._build_schedule_table(allocations)

            if table_data:
                # Create table with optimized column widths based on orientation
                table = Table(
                    table_data,
                    colWidths=[time_col_width] + [day_col_width] * 6,
                    repeatRows=1,  # Repeat header row on each page
                )

                # Apply table styling - minimal padding for compactness
                table.setStyle(
                    TableStyle(
                        [
                            # Header row styling
                            (
                                "BACKGROUND",
                                (0, 0),
                                (-1, 0),
                                colors.HexColor("#1f4788"),
                            ),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), self.FONT_BOLD),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                            ("TOPPADDING", (0, 0), (-1, 0), 4),
                            # Time column styling (first column)
                            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#e8eaf6")),
                            ("ALIGN", (0, 1), (0, -1), "CENTER"),
                            ("FONTNAME", (0, 1), (0, -1), self.FONT_BOLD),
                            ("FONTSIZE", (0, 1), (0, -1), 8),
                            # All cells - minimal padding
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("LEFTPADDING", (0, 0), (-1, -1), 2),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                            ("TOPPADDING", (0, 1), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
                            # Zebra striping every two rows for better readability
                            # rows 1-2 gray, 3-4 white, 5-6 gray, etc.
                            *[
                                (
                                    "BACKGROUND",
                                    (1, i),
                                    (-1, i),
                                    (
                                        colors.HexColor("#f5f5f5")
                                        if ((i - 1) // 2) % 2 == 0
                                        else colors.white
                                    ),
                                )
                                for i in range(1, len(table_data))
                            ],
                        ]
                    )
                )

                story.append(table)

            # Add page break after each room (except last)
            if room_id != list(rooms_to_process.keys())[-1]:
                story.append(PageBreak())

        # Build PDF
        doc.build(story)

        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content

    def _build_schedule_table(self, allocations: List[Any]) -> List[List[Any]]:
        """
        Build schedule table data from allocations.

        Args:
            allocations: List of allocation objects

        Returns:
            List of lists containing table data (header + rows)
        """
        # Weekday names in Portuguese
        weekdays = {
            2: "SEGUNDA",
            3: "TERÇA",
            4: "QUARTA",
            5: "QUINTA",
            6: "SEXTA",
            7: "SÁBADO",
        }

        # Get all time blocks from parser (M1-M5, T1-T6, N1-N4)
        time_blocks = sorted(
            self.parser.MAP_SCHEDULE_TIMES.keys(), key=self._sort_time_block
        )

        # Initialize schedule grid
        schedule_grid = {}
        for dia_id in weekdays.keys():
            schedule_grid[dia_id] = {block: [] for block in time_blocks}

        # Populate schedule grid with allocations
        for alloc in allocations:
            # Skip reservations for now (handle in future version)
            if isinstance(alloc, dict) and alloc.get("type") == "reservation":
                continue

            dia_id = alloc.dia_semana_id
            bloco = alloc.codigo_bloco

            if dia_id not in weekdays or bloco not in time_blocks:
                continue

            # Extract course information
            codigo_disciplina = (
                alloc.demanda.codigo_disciplina if alloc.demanda else "N/A"
            )
            nome_disciplina = alloc.demanda.nome_disciplina if alloc.demanda else ""
            turma_disciplina = alloc.demanda.turma_disciplina if alloc.demanda else ""
            professor_disciplina = (
                alloc.demanda.professores_disciplina if alloc.demanda else ""
            )

            # Format cell content
            cell_content = {
                "codigo": codigo_disciplina,
                "nome": nome_disciplina,
                "turma": turma_disciplina,
                "professor": professor_disciplina,
            }

            schedule_grid[dia_id][bloco].append(cell_content)

        # Build table data
        table_data = []

        # Header row
        header_row = [Paragraph("HORÁRIO", self.styles["DayHeader"])]
        for dia_id in sorted(weekdays.keys()):
            header_row.append(Paragraph(weekdays[dia_id], self.styles["DayHeader"]))
        table_data.append(header_row)

        # Data rows (one row per time block)
        for block in time_blocks:
            block_info = self.parser.MAP_SCHEDULE_TIMES.get(block, {})
            start_time = block_info.get("inicio", block)
            end_time = block_info.get("fim", "")

            # Time column
            time_str = f"{start_time}-{end_time}" if end_time else start_time
            row = [Paragraph(time_str, self.styles["TimeSlot"])]

            # Day columns
            for dia_id in sorted(weekdays.keys()):
                cell_allocations = schedule_grid[dia_id][block]

                if cell_allocations:
                    # Format cell content
                    cell_text = self._format_cell_content(cell_allocations)
                    row.append(Paragraph(cell_text, self.styles["CellContent"]))
                else:
                    row.append("")

            table_data.append(row)

        return table_data

    def _format_cell_content(self, allocations: List[Dict[str, str]]) -> str:
        """
        Format cell content for PDF display.

        Args:
            allocations: List of allocation dictionaries

        Returns:
            Formatted HTML string for cell content
        """
        if not allocations:
            return ""

        # Handle multiple allocations in same time slot (shouldn't happen, but be safe)
        formatted_items = []

        for alloc in allocations:
            # codigo = alloc.get("codigo", "N/A")
            codigo = None
            nome = alloc.get("nome", "")
            turma = alloc.get("turma", "")
            professor = alloc.get("professor", "")

            # Build formatted text
            lines = []

            # Line 1: Course code + name on same line
            # Let Paragraph handle word wrapping naturally
            if codigo and nome:
                # Truncate only if extremely long (>80 chars) to prevent overflow
                nome_display = nome if len(nome) <= 80 else nome[:77] + "..."
                lines.append(f"{codigo} - <b>{nome_display}</b>")
            elif codigo:
                lines.append(f"{codigo}")
            elif nome:
                nome_display = nome if len(nome) <= 80 else nome[:77] + "..."
                lines.append(f"<b>{nome_display}</b>")

            # Line 2: Professor (shortened name for space savings)
            if professor:
                prof_display = self._shorten_professor_name(professor)
                lines.append(f"Prof(a). {prof_display}")

            formatted_items.append("<br/>".join(lines))

        # Join multiple allocations with separator
        return "<br/>---<br/>".join(formatted_items)

    def _sort_time_block(self, block_code: str) -> int:
        """
        Sort time blocks chronologically.

        Args:
            block_code: Block code (e.g., "M1", "T3", "N2")

        Returns:
            Sort key (minutes since midnight)
        """
        block_info = self.parser.MAP_SCHEDULE_TIMES.get(block_code, {})
        start_time = block_info.get("inicio", "00:00")

        try:
            hours, minutes = map(int, start_time.split(":"))
            return hours * 60 + minutes
        except (ValueError, AttributeError):
            return 0

    def _shorten_professor_name(self, full_name: str) -> str:
        """
        Shorten professor name: keep first name, abbreviate rest.

        Examples:
            "Maria José da Silva Santos" -> "Maria J.S.S."
            "João Carlos" -> "João C."
            "Pedro" -> "Pedro"

        Args:
            full_name: Full professor name

        Returns:
            Shortened name with initials
        """
        if not full_name:
            return ""

        # Common Portuguese connectors to skip
        connectors = {"da", "de", "do", "das", "dos", "e", "Jr"}

        parts = full_name.strip().split()
        if len(parts) <= 1:
            return full_name

        # Keep first name, abbreviate the rest
        result = [parts[0]]
        for part in parts[1:]:
            if part.lower() in connectors:
                continue  # Skip connectors
            if part:
                result.append(f"{part[0].upper()}.")

        return " ".join(result)
