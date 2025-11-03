"""
Autonomous Allocation PDF Report Generator - Human-readable allocation decision reports
"""

import io
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import Color, black, white, grey, lightgrey, green, red, blue
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Suppress ReportLab logging completely
logging.getLogger("reportlab").setLevel(logging.ERROR)
logging.getLogger("reportlab.lib").setLevel(logging.ERROR)
logging.getLogger("reportlab.pdfgen").setLevel(logging.ERROR)
logging.getLogger("reportlab.platypus").setLevel(logging.ERROR)
logging.getLogger("reportlab.pdfbase").setLevel(logging.ERROR)
logging.getLogger("reportlab.pdfbase.pdfmetrics").setLevel(logging.ERROR)
logging.getLogger("reportlab.pdfbase.ttfonts").setLevel(logging.ERROR)

# Import existing styles from statistics service
from src.services.statistics_report_service import StatisticsReportService
from src.utils.pdf_fonts import (
    register_pdf_fonts,
    get_default_font,
    get_table_header_font,
    get_table_cell_font,
)


def _register_unicode_fonts():
    """
    Register Unicode-compatible fonts from static folder for PDF generation.

    Uses Space Mono and Grotesk Google Fonts which have excellent Unicode support.
    These fonts are bundled in static/ and support special characters and accents.
    """
    # Use the centralized font registration utility
    return register_pdf_fonts()


# Register fonts on module import
_register_unicode_fonts()


class AutonomousAllocationReportService:
    """Service for generating human-readable PDF reports of autonomous allocation decisions."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.stats_service = StatisticsReportService()

    def _setup_custom_styles(self):
        """Setup custom styles for the allocation report with Unicode font support."""

        # Use Google Fonts from static folder for Unicode support
        base_font = get_default_font(bold=False)
        base_font_bold = get_default_font(bold=True)

        # Title styles
        self.styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=self.styles["Title"],
                fontSize=18,
                spaceAfter=20,
                textColor=colors.darkblue,
                alignment=TA_CENTER,
                fontName=base_font_bold,
            )
        )

        # Section header styles
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.darkblue,
                fontName=base_font_bold,
                borderWidth=0,
                borderColor=colors.lightgrey,
                borderPadding=5,
            )
        )

        # Decision styles
        self.styles.add(
            ParagraphStyle(
                name="DecisionHeader",
                parent=self.styles["Heading3"],
                fontSize=12,
                spaceBefore=15,
                spaceAfter=8,
                textColor=colors.black,
                fontName=base_font_bold,
                backgroundColor=colors.lightgrey,
            )
        )

        # Success/Failure styles
        self.styles.add(
            ParagraphStyle(
                name="SuccessText",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.green,
                fontName=base_font_bold,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="FailureText",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.red,
                fontName=base_font_bold,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="WarningText",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.orange,
                fontName=base_font_bold,
            )
        )

        # Score breakdown styles
        self.styles.add(
            ParagraphStyle(
                name="ScoreDetail",
                parent=self.styles["Normal"],
                fontSize=9,
                leftIndent=20,
                spaceAfter=2,
                fontName=base_font,
            )
        )

        # Table styles
        self.styles.add(
            ParagraphStyle(
                name="TableHeader",
                parent=self.styles["Normal"],
                fontSize=9,
                fontName=base_font_bold,
                alignment=TA_CENTER,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="TableCell",
                parent=self.styles["Normal"],
                fontSize=8,
                alignment=TA_LEFT,
                fontName=base_font,
            )
        )

    def generate_autonomous_allocation_report(
        self,
        allocation_results: Dict[str, Any],
        allocation_decisions: List[Dict[str, Any]],
        semester_name: str,
        execution_time: float = 0.0,
    ) -> bytes:
        """
        Generate comprehensive human-readable PDF report of autonomous allocation.

        Args:
            allocation_results: Results from autonomous allocation execution
            allocation_decisions: Detailed decision data from allocation logger
            semester_name: Name of the semester (e.g., "2025-1")
            execution_time: Total execution time in seconds

        Returns:
            bytes: PDF file content
        """
        buffer = io.BytesIO()

        # Create PDF document with reduced margins for better table rendering
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=12 * mm,
            leftMargin=12 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title=f"Relatório de Alocação Autônoma - {semester_name}",
            author="Sistema de Ensalamento FUP/UnB",
        )

        # Build document content
        story = []

        # Title page with key metrics
        story.extend(
            self._build_title_page(semester_name, allocation_results, execution_time)
        )

        # Executive summary with visual performance indicators
        story.extend(self._build_executive_summary(allocation_results))

        # Critical insights - What went right/wrong
        story.extend(
            self._build_critical_insights(allocation_results, allocation_decisions)
        )

        # Phase-by-phase analysis with success metrics
        story.extend(self._build_phase_analysis(allocation_results))

        # Detailed allocation decisions with scoring breakdowns
        story.extend(self._build_detailed_allocation_decisions(allocation_decisions))

        # Candidate fallback analysis - How many tries per demand
        story.extend(self._build_candidate_fallback_analysis(allocation_decisions))

        # Conflict analysis - Where and why conflicts occurred
        story.extend(
            self._build_conflict_analysis(allocation_decisions, allocation_results)
        )

        # Room utilization with capacity analysis
        story.extend(self._build_room_utilization_analysis(allocation_decisions))

        # Time slot utilization - Busiest times
        story.extend(self._build_time_slot_analysis(allocation_decisions))

        # Scoring effectiveness - Which factors mattered most
        story.extend(self._build_scoring_effectiveness(allocation_decisions))

        # Top unallocated demands - Manual intervention needed
        story.extend(self._build_unallocated_demands_analysis(allocation_decisions))

        # Actionable recommendations with priorities
        story.extend(
            self._build_recommendations(allocation_results, allocation_decisions)
        )

        # Build PDF
        doc.build(story)

        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content

    def _build_title_page(
        self, semester_name: str, results: Dict[str, Any], execution_time: float
    ) -> List[Any]:
        """Build title page with key metrics."""
        content = []

        # Main title
        content.append(
            Paragraph("RELATÓRIO DE ALOCAÇÃO AUTÔNOMA", self.styles["ReportTitle"])
        )
        content.append(Spacer(1, 10))

        # Semester and execution info
        content.append(Paragraph(f"Semestre: {semester_name}", self.styles["Heading3"]))
        content.append(
            Paragraph(
                f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                self.styles["Normal"],
            )
        )
        content.append(
            Paragraph(
                f"Tempo de Execução: {execution_time:.2f} segundos",
                self.styles["Normal"],
            )
        )

        # Key metrics box
        content.append(Spacer(1, 20))

        metrics_data = [
            ["MÉTRICA", "VALOR", "DETALHES"],
            [
                "Total de Demandas Processadas",
                str(results.get("total_demands_processed", 0)),
                "100%",
            ],
            [
                "Alocações Realizadas",
                str(results.get("allocations_completed", 0)),
                f"{results.get('progress_percentage', 0):.1f}%",
            ],
            [
                "Conflitos Encontrados",
                str(results.get("conflicts_found", 0)),
                "Durante análise",
            ],
            [
                "Demandas Não Alocadas",
                str(results.get("demands_skipped", 0)),
                "Intervenção manual",
            ],
        ]

        metrics_table = Table(metrics_data, colWidths=[80 * mm, 30 * mm, 30 * mm])
        metrics_table.setStyle(
            TableStyle(
                [
                    # Header row
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), get_table_header_font()),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Data rows
                    ("FONTNAME", (0, 1), (-1, -1), get_table_cell_font()),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    # Borders
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.lightgrey],
                    ),
                ]
            )
        )

        content.append(metrics_table)
        content.append(PageBreak())

        return content

    def _build_executive_summary(self, results: Dict[str, Any]) -> List[Any]:
        """Build executive summary section."""
        content = []

        content.append(Paragraph("RESUMO EXECUTIVO", self.styles["SectionHeader"]))

        # Overall performance
        success_rate = results.get("progress_percentage", 0)
        if success_rate >= 80:
            performance_text = "EXCELENTE"
            performance_color = colors.green
        elif success_rate >= 60:
            performance_text = "BOM"
            performance_color = colors.orange
        else:
            performance_text = "REQUER ATENCAO"
            performance_color = colors.red

        content.append(
            Paragraph(
                f"<b>Performance Geral:</b> {performance_text} ({success_rate:.1f}% de sucesso)",
                ParagraphStyle(
                    "PerformanceText",
                    parent=self.styles["Normal"],
                    fontName=get_table_header_font(),
                    textColor=performance_color,
                ),
            )
        )

        content.append(Spacer(1, 10))

        # Phase summary
        phase1 = results.get("phase1_hard_rules", {})
        phase2 = results.get("phase2_soft_scoring", {})
        phase3 = results.get("phase3_atomic_allocation", {})

        summary_text = f"""
        <b>Fase 1 - Regras Obrigatórias:</b> {phase1.get('allocations', 0)} alocações realizadas, {phase1.get('conflicts', 0)} conflitos.<br/>
        <b>Fase 2 - Avaliação por Pontuação:</b> {phase2.get('candidates_scored', 0)} demandas avaliadas, {phase2.get('conflicts', 0)} conflitos detectados.<br/>
        <b>Fase 3 - Alocação Atômica:</b> {phase3.get('allocations', 0)} alocações finais, {phase3.get('conflicts', 0)} conflitos restantes.<br/>
        <br/>
        <b>Próximos Passos:</b> {results.get('next_steps', 'Análise manual das demandas não alocadas')}
        """

        content.append(Paragraph(summary_text, self.styles["Normal"]))
        content.append(Spacer(1, 15))

        return content

    def _build_critical_insights(
        self, results: Dict[str, Any], decisions: List[Dict[str, Any]]
    ) -> List[Any]:
        """Build critical insights section - What went right/wrong."""
        content = []

        content.append(Paragraph("ANÁLISE CRÍTICA", self.styles["SectionHeader"]))

        # Calculate key insights
        total_demands = results.get("total_demands_processed", 0)
        allocated = results.get("allocations_completed", 0)
        skipped = results.get("demands_skipped", 0)
        conflicts = results.get("conflicts_found", 0)

        # Success factors
        content.append(Paragraph("✅ Fatores de Sucesso", self.styles["Heading3"]))

        success_factors = []

        phase1_allocs = results.get("phase1_hard_rules", {}).get("allocations", 0)
        if phase1_allocs > 0:
            success_factors.append(
                f"• <b>{phase1_allocs}</b> demandas alocadas automaticamente por regras obrigatórias (0% de conflitos)"
            )

        phase3_allocs = results.get("phase3_atomic_allocation", {}).get(
            "allocations", 0
        )
        if phase3_allocs > 0:
            success_factors.append(
                f"• <b>{phase3_allocs}</b> demandas alocadas por pontuação inteligente (sistema de scoring funcionou)"
            )

        # Candidate fallback success
        multi_candidate_success = len(
            [
                d
                for d in decisions
                if d.get("allocated") and d.get("candidate_attempt_number", 1) > 1
            ]
        )
        if multi_candidate_success > 0:
            success_factors.append(
                f"• <b>{multi_candidate_success}</b> demandas alocadas usando candidatos alternativos (fallback funcionou)"
            )

        if not success_factors:
            success_factors.append(
                "• Nenhum fator de sucesso significativo identificado"
            )

        for factor in success_factors:
            content.append(Paragraph(factor, self.styles["Normal"]))

        content.append(Spacer(1, 10))

        # Problem areas
        content.append(Paragraph("⚠️ Áreas Problemáticas", self.styles["Heading3"]))

        problems = []

        if skipped > total_demands * 0.2:  # More than 20% skipped
            problems.append(
                f"• <b>{skipped}</b> demandas não alocadas ({skipped/total_demands*100:.1f}% do total) - CRÍTICO"
            )

        if conflicts > allocated:
            problems.append(
                f"• <b>{conflicts}</b> conflitos detectados durante alocação - indica sobreposição de horários"
            )

        # Check for demands that exhausted all candidates
        exhausted_candidates = [
            d
            for d in decisions
            if not d.get("allocated")
            and "candidates" in str(d.get("skipped_reason", ""))
        ]
        if len(exhausted_candidates) > 0:
            problems.append(
                f"• <b>{len(exhausted_candidates)}</b> demandas esgotaram TODOS os candidatos - necessita revisão manual"
            )

        # Check for low-scoring allocations
        low_score_allocs = [
            d for d in decisions if d.get("allocated") and d.get("final_score", 0) < 8
        ]
        if len(low_score_allocs) > 0:
            problems.append(
                f"• <b>{len(low_score_allocs)}</b> demandas alocadas com pontuação baixa (<8) - pode indicar alocação subótima"
            )

        if not problems:
            problems.append("• Nenhuma área problemática crítica identificada ✓")

        for problem in problems:
            color = colors.red if "CRÍTICO" in problem else colors.orange
            content.append(
                Paragraph(
                    problem,
                    ParagraphStyle(
                        "ProblemText", parent=self.styles["Normal"], textColor=color
                    ),
                )
            )

        content.append(Spacer(1, 15))

        return content

    def _build_candidate_fallback_analysis(
        self, decisions: List[Dict[str, Any]]
    ) -> List[Any]:
        """Analyze how many candidate attempts were needed per demand."""
        content = []

        content.append(
            Paragraph(
                "ANÁLISE DE TENTATIVAS DE CANDIDATOS", self.styles["SectionHeader"]
            )
        )

        # Count attempts distribution
        allocated_decisions = [d for d in decisions if d.get("allocated")]

        if allocated_decisions:
            # Count by number of attempts (simulated from data)
            first_try_success = len(
                [
                    d
                    for d in allocated_decisions
                    if d.get("candidate_attempt_number", 1) == 1
                ]
            )
            multi_try_success = len(allocated_decisions) - first_try_success

            content.append(Paragraph("Eficiência de Alocação", self.styles["Heading3"]))

            efficiency_text = f"""
            • <b>{first_try_success}</b> demandas alocadas no <b>primeiro candidato</b> ({first_try_success/len(allocated_decisions)*100:.1f}%)<br/>
            • <b>{multi_try_success}</b> demandas necessitaram <b>múltiplas tentativas</b> ({multi_try_success/len(allocated_decisions)*100:.1f}%)<br/>
            <br/>
            <b>Interpretação:</b> {'✓ Excelente - maioria alocada no primeiro candidato' if first_try_success/len(allocated_decisions) > 0.7 else '⚠️ Considerar revisar pontuação - muitos candidatos alternativos necessários'}
            """

            content.append(Paragraph(efficiency_text, self.styles["Normal"]))

        content.append(Spacer(1, 15))
        return content

    def _build_conflict_analysis(
        self, decisions: List[Dict[str, Any]], results: Dict[str, Any]
    ) -> List[Any]:
        """Detailed analysis of where and why conflicts occurred."""
        content = []

        content.append(
            Paragraph("ANÁLISE DETALHADA DE CONFLITOS", self.styles["SectionHeader"])
        )

        total_conflicts = results.get("conflicts_found", 0)

        if total_conflicts > 0:
            # Conflict distribution by phase
            phase1_conflicts = results.get("phase1_hard_rules", {}).get("conflicts", 0)
            phase2_conflicts = results.get("phase2_soft_scoring", {}).get(
                "conflicts", 0
            )
            phase3_conflicts = results.get("phase3_atomic_allocation", {}).get(
                "conflicts", 0
            )

            conflict_data = [
                ["FASE", "CONFLITOS", "% DO TOTAL"],
                [
                    "Fase 1 - Regras Obrigatórias",
                    str(phase1_conflicts),
                    (
                        f"{phase1_conflicts/total_conflicts*100:.1f}%"
                        if total_conflicts > 0
                        else "0%"
                    ),
                ],
                [
                    "Fase 2 - Avaliação",
                    str(phase2_conflicts),
                    (
                        f"{phase2_conflicts/total_conflicts*100:.1f}%"
                        if total_conflicts > 0
                        else "0%"
                    ),
                ],
                [
                    "Fase 3 - Alocação Atômica",
                    str(phase3_conflicts),
                    (
                        f"{phase3_conflicts/total_conflicts*100:.1f}%"
                        if total_conflicts > 0
                        else "0%"
                    ),
                ],
                ["TOTAL", str(total_conflicts), "100%"],
            ]

            conflict_table = Table(conflict_data, colWidths=[70 * mm, 30 * mm, 30 * mm])
            conflict_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.darkred),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, 0), get_table_header_font()),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTNAME", (0, 1), (-1, -1), get_table_cell_font()),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -2),
                            [colors.white, colors.lightgrey],
                        ),
                        ("BACKGROUND", (0, -1), (-1, -1), colors.lightyellow),
                        ("FONTNAME", (0, -1), (-1, -1), get_table_header_font()),
                    ]
                )
            )

            content.append(conflict_table)
            content.append(Spacer(1, 10))

            # Interpretation
            interpretation = ""
            if phase3_conflicts > total_conflicts * 0.5:
                interpretation = "⚠️ <b>Maioria dos conflitos na Fase 3</b> - indica que candidatos bem pontuados têm conflitos de horário. Considerar ajustar pesos de pontuação ou revisar horários."
            elif phase2_conflicts > total_conflicts * 0.5:
                interpretation = "ℹ️ <b>Conflitos detectados na avaliação</b> - sistema identificou conflitos antes de tentar alocar (bom funcionamento)."
            else:
                interpretation = "✓ <b>Conflitos distribuídos</b> - comportamento normal do sistema de alocação."

            content.append(Paragraph(interpretation, self.styles["Normal"]))
        else:
            content.append(
                Paragraph(
                    "✓ Nenhum conflito detectado - todas as alocações foram bem-sucedidas!",
                    self.styles["SuccessText"],
                )
            )

        content.append(Spacer(1, 15))
        return content

    def _build_time_slot_analysis(self, decisions: List[Dict[str, Any]]) -> List[Any]:
        """Analyze time slot utilization patterns."""
        content = []

        content.append(
            Paragraph("ANÁLISE DE OCUPAÇÃO POR HORÁRIO", self.styles["SectionHeader"])
        )

        allocated_decisions = [d for d in decisions if d.get("allocated")]

        if allocated_decisions:
            # Extract schedule patterns (M1-M6, T1-T6, N1-N6)
            schedule_counts = {}
            for decision in allocated_decisions:
                schedule = decision.get("horario_sigaa", "")
                # Count M (morning), T (afternoon), N (night) occurrences
                if "M" in schedule:
                    schedule_counts["Matutino (M)"] = (
                        schedule_counts.get("Matutino (M)", 0) + 1
                    )
                if "T" in schedule:
                    schedule_counts["Vespertino (T)"] = (
                        schedule_counts.get("Vespertino (T)", 0) + 1
                    )
                if "N" in schedule:
                    schedule_counts["Noturno (N)"] = (
                        schedule_counts.get("Noturno (N)", 0) + 1
                    )

            if schedule_counts:
                content.append(
                    Paragraph("Distribuição por Turno", self.styles["Heading3"])
                )

                total_slots = sum(schedule_counts.values())
                schedule_data = [["TURNO", "ALOCAÇÕES", "% DO TOTAL"]]

                for turno, count in sorted(
                    schedule_counts.items(), key=lambda x: x[1], reverse=True
                ):
                    percentage = (count / total_slots * 100) if total_slots > 0 else 0
                    schedule_data.append([turno, str(count), f"{percentage:.1f}%"])

                schedule_table = Table(
                    schedule_data, colWidths=[60 * mm, 30 * mm, 30 * mm]
                )
                schedule_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("FONTNAME", (0, 0), (-1, 0), get_table_header_font()),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("FONTNAME", (0, 1), (-1, -1), get_table_cell_font()),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.lightgrey],
                            ),
                        ]
                    )
                )

                content.append(schedule_table)
                content.append(Spacer(1, 10))

                # Interpretation
                max_turno = max(schedule_counts, key=schedule_counts.get)
                max_count = schedule_counts[max_turno]
                interpretation = f"<b>Turno mais ocupado:</b> {max_turno} com {max_count} alocações. "

                if max_count / total_slots > 0.5:
                    interpretation += (
                        "⚠️ Considerar balancear melhor a distribuição entre turnos."
                    )
                else:
                    interpretation += "✓ Distribuição equilibrada entre turnos."

                content.append(Paragraph(interpretation, self.styles["Normal"]))

        content.append(Spacer(1, 15))
        return content

    def _build_scoring_effectiveness(
        self, decisions: List[Dict[str, Any]]
    ) -> List[Any]:
        """Analyze which scoring factors were most effective."""
        content = []

        content.append(
            Paragraph(
                "EFETIVIDADE DO SISTEMA DE PONTUAÇÃO", self.styles["SectionHeader"]
            )
        )

        allocated_decisions = [
            d for d in decisions if d.get("allocated") and d.get("scoring_breakdown")
        ]

        if allocated_decisions:
            # Aggregate scoring factors
            total_capacity = sum(
                d.get("scoring_breakdown", {}).get("capacity_points", 0)
                for d in allocated_decisions
            )
            total_hard_rules = sum(
                d.get("scoring_breakdown", {}).get("hard_rules_points", 0)
                for d in allocated_decisions
            )
            total_preferences = sum(
                d.get("scoring_breakdown", {}).get("soft_preference_points", 0)
                for d in allocated_decisions
            )
            total_historical = sum(
                d.get("scoring_breakdown", {}).get("historical_frequency_points", 0)
                for d in allocated_decisions
            )

            total_points = (
                total_capacity + total_hard_rules + total_preferences + total_historical
            )

            if total_points > 0:
                scoring_data = [
                    ["FATOR DE PONTUAÇÃO", "PONTOS TOTAIS", "% DO TOTAL", "IMPACTO"],
                    [
                        "Capacidade da Sala",
                        str(total_capacity),
                        f"{total_capacity/total_points*100:.1f}%",
                        (
                            "Alto"
                            if total_capacity / total_points > 0.4
                            else (
                                "Médio"
                                if total_capacity / total_points > 0.2
                                else "Baixo"
                            )
                        ),
                    ],
                    [
                        "Regras Obrigatórias",
                        str(total_hard_rules),
                        f"{total_hard_rules/total_points*100:.1f}%",
                        (
                            "Alto"
                            if total_hard_rules / total_points > 0.4
                            else (
                                "Médio"
                                if total_hard_rules / total_points > 0.2
                                else "Baixo"
                            )
                        ),
                    ],
                    [
                        "Preferências do Professor",
                        str(total_preferences),
                        f"{total_preferences/total_points*100:.1f}%",
                        (
                            "Alto"
                            if total_preferences / total_points > 0.4
                            else (
                                "Médio"
                                if total_preferences / total_points > 0.2
                                else "Baixo"
                            )
                        ),
                    ],
                    [
                        "Histórico de Uso",
                        str(total_historical),
                        f"{total_historical/total_points*100:.1f}%",
                        (
                            "Alto"
                            if total_historical / total_points > 0.4
                            else (
                                "Médio"
                                if total_historical / total_points > 0.2
                                else "Baixo"
                            )
                        ),
                    ],
                ]

                scoring_table = Table(
                    scoring_data, colWidths=[60 * mm, 30 * mm, 25 * mm, 25 * mm]
                )
                scoring_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("FONTNAME", (0, 0), (-1, 0), get_table_header_font()),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("FONTNAME", (0, 1), (-1, -1), get_table_cell_font()),
                            ("FONTSIZE", (0, 1), (-1, -1), 8),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.lightgrey],
                            ),
                        ]
                    )
                )

                content.append(scoring_table)
                content.append(Spacer(1, 10))

                # Interpretation
                factors_sorted = [
                    ("Capacidade", total_capacity),
                    ("Regras Obrigatórias", total_hard_rules),
                    ("Preferências", total_preferences),
                    ("Histórico", total_historical),
                ]
                factors_sorted.sort(key=lambda x: x[1], reverse=True)

                top_factor = factors_sorted[0][0]
                interpretation = f"<b>Fator mais influente:</b> {top_factor}. "

                if total_historical < total_points * 0.1:
                    interpretation += "⚠️ Histórico de uso com baixo impacto - considerar aumentar peso se deseja priorizar continuidade."
                elif total_preferences < total_points * 0.1:
                    interpretation += "ℹ️ Preferências de professores com baixo impacto - verificar se preferências estão cadastradas."
                else:
                    interpretation += (
                        "✓ Distribuição balanceada entre fatores de pontuação."
                    )

                content.append(Paragraph(interpretation, self.styles["Normal"]))

        content.append(Spacer(1, 15))
        return content

    def _build_unallocated_demands_analysis(
        self, decisions: List[Dict[str, Any]]
    ) -> List[Any]:
        """Detailed analysis of unallocated demands requiring manual intervention."""
        content = []

        content.append(
            Paragraph(
                "DEMANDAS NÃO ALOCADAS - INTERVENÇÃO MANUAL",
                self.styles["SectionHeader"],
            )
        )

        skipped_decisions = [d for d in decisions if not d.get("allocated")]

        if skipped_decisions:
            content.append(
                Paragraph(
                    f"Total de demandas não alocadas: <b>{len(skipped_decisions)}</b>",
                    self.styles["Heading3"],
                )
            )

            # Group by skip reason
            reason_groups = {}
            for decision in skipped_decisions:
                reason = decision.get("skipped_reason", "Motivo não especificado")
                if reason not in reason_groups:
                    reason_groups[reason] = []
                reason_groups[reason].append(decision)

            # Show top reasons with demands
            content.append(Spacer(1, 10))
            content.append(Paragraph("Principais Motivos", self.styles["Normal"]))

            for reason, demands_list in sorted(
                reason_groups.items(), key=lambda x: len(x[1]), reverse=True
            )[:5]:
                content.append(
                    Paragraph(
                        f"<b>{reason}</b> ({len(demands_list)} demandas)",
                        self.styles["DecisionHeader"],
                    )
                )

                # Show top 3 demands for this reason
                for decision in demands_list[:3]:
                    disciplina = decision.get("disciplina_codigo", "N/A")
                    nome = decision.get("disciplina_nome", "N/A")
                    vagas = decision.get("vagas", 0)
                    horario = decision.get("horario_sigaa", "N/A")

                    demand_text = f"• <b>{disciplina}</b> - {nome[:50]}{'...' if len(nome) > 50 else ''} | Vagas: {vagas} | Horário: {horario}"
                    content.append(Paragraph(demand_text, self.styles["ScoreDetail"]))

                if len(demands_list) > 3:
                    content.append(
                        Paragraph(
                            f"   ... e mais {len(demands_list) - 3} demandas",
                            self.styles["ScoreDetail"],
                        )
                    )

                content.append(Spacer(1, 8))

            # Action items
            content.append(Spacer(1, 10))
            content.append(Paragraph("Ações Recomendadas", self.styles["Heading3"]))

            actions = [
                "1. Revisar manualmente as demandas listadas acima",
                "2. Verificar se há salas disponíveis em horários alternativos",
                "3. Considerar ajustar horários de demandas para evitar conflitos",
                "4. Verificar se regras obrigatórias estão muito restritivas",
                "5. Considerar criar novas salas ou aumentar capacidade das existentes",
            ]

            for action in actions:
                content.append(Paragraph(action, self.styles["Normal"]))
        else:
            content.append(
                Paragraph(
                    "✓ Todas as demandas foram alocadas com sucesso! Nenhuma intervenção manual necessária.",
                    self.styles["SuccessText"],
                )
            )

        content.append(PageBreak())
        return content

    def _build_phase_analysis(self, results: Dict[str, Any]) -> List[Any]:
        """Build detailed phase analysis section."""
        content = []

        content.append(
            Paragraph("ANÁLISE DETALHADA POR FASE", self.styles["SectionHeader"])
        )

        # Phase 1 Analysis
        content.append(
            Paragraph("Fase 1: Regras Obrigatórias", self.styles["Heading3"])
        )
        phase1 = results.get("phase1_hard_rules", {})

        if phase1.get("allocations", 0) > 0:
            content.append(
                Paragraph(
                    f"<b>Sucesso:</b> {phase1.get('allocations', 0)} demandas alocadas automaticamente por satisfazerem todas as regras obrigatórias.",
                    self.styles["SuccessText"],
                )
            )
        else:
            content.append(
                Paragraph(
                    "<b>Observacao:</b> Nenhuma demanda alocada nesta fase. Isso pode indicar ausencia de regras obrigatorias especificas.",
                    self.styles["Normal"],
                )
            )

        content.append(
            Paragraph(
                f"Conflitos encontrados: {phase1.get('conflicts', 0)}",
                self.styles["Normal"],
            )
        )

        # Phase 2 Analysis
        content.append(Spacer(1, 10))
        content.append(
            Paragraph("Fase 2: Avaliação por Pontuação", self.styles["Heading3"])
        )
        phase2 = results.get("phase2_soft_scoring", {})

        content.append(
            Paragraph(
                f"<b>Demandas Avaliadas:</b> {phase2.get('candidates_scored', 0)}",
                self.styles["Normal"],
            )
        )
        content.append(
            Paragraph(
                f"<b>Candidatos Gerados:</b> {phase2.get('candidates_generated', 0)}",
                self.styles["Normal"],
            )
        )
        content.append(
            Paragraph(
                f"<b>Conflitos Detectados:</b> {phase2.get('conflicts', 0)}",
                self.styles["Normal"],
            )
        )

        # Phase 3 Analysis
        content.append(Spacer(1, 10))
        content.append(Paragraph("Fase 3: Alocação Atômica", self.styles["Heading3"]))
        phase3 = results.get("phase3_atomic_allocation", {})

        if phase3.get("allocations", 0) > 0:
            content.append(
                Paragraph(
                    f"<b>Alocações Realizadas:</b> {phase3.get('allocations', 0)} demandas alocadas com base na pontuação mais alta.",
                    self.styles["SuccessText"],
                )
            )
        else:
            content.append(
                Paragraph(
                    "<b>Falha na Alocação:</b> Nenhuma alocação realizada na fase final. Verificar conflitos de horário.",
                    self.styles["WarningText"],
                )
            )

        content.append(Spacer(1, 15))

        return content

    def _build_detailed_allocation_decisions(
        self, decisions: List[Dict[str, Any]]
    ) -> List[Any]:
        """Build detailed allocation decisions section with comprehensive scoring breakdowns."""
        content = []

        content.append(
            Paragraph(
                "DECISÕES DE ALOCAÇÃO DETALHADAS COM ANÁLISE DE PONTUAÇÃO",
                self.styles["SectionHeader"],
            )
        )

        # Get only allocated decisions with scoring information
        allocated_decisions = [
            d
            for d in decisions
            if d.get("allocated", False) and d.get("scoring_breakdown")
        ]

        if allocated_decisions:
            content.append(
                Paragraph(
                    f"Análise detalhada de <b>{len(allocated_decisions)}</b> alocações realizadas",
                    self.styles["Heading3"],
                )
            )

            # Sort by final score descending to show best allocations first
            allocated_decisions.sort(
                key=lambda x: x.get("final_score", 0), reverse=True
            )

            # Show ALL allocations with detailed scoring
            for i, decision in enumerate(allocated_decisions):
                disciplina_codigo = decision.get("disciplina_codigo", "N/A")
                disciplina_nome = decision.get("disciplina_nome", "N/A")
                allocated_room = decision.get("allocated_room_name", "N/A")
                final_score = decision.get("final_score", 0)
                allocation_phase = decision.get("allocation_phase", "N/A")

                # Discipline header
                content.append(
                    Paragraph(
                        f"<b>{disciplina_codigo}</b> - {disciplina_nome[:60]}{'...' if len(disciplina_nome) > 60 else ''}",
                        self.styles["DecisionHeader"],
                    )
                )

                # Allocation summary
                allocation_summary = f"""
                <b>Sala Alocada:</b> {allocated_room}<br/>
                <b>Pontuação Final:</b> {final_score} pontos<br/>
                <b>Fase de Alocação:</b> {allocation_phase}<br/>
                <b>Turma:</b> {decision.get('turma', 'N/A')}<br/>
                <b>Professor:</b> {decision.get('professores', 'N/A')[:50]}{'...' if len(decision.get('professores', '')) > 50 else ''}
                """

                content.append(Paragraph(allocation_summary, self.styles["Normal"]))

                # Detailed scoring breakdown
                scoring_breakdown = decision.get("scoring_breakdown", {})

                if scoring_breakdown:
                    content.append(Spacer(1, 5))
                    content.append(
                        Paragraph(
                            "<b>🔍 Detalhamento da Pontuação:</b>",
                            self.styles["Normal"],
                        )
                    )

                    # Create scoring breakdown table
                    breakdown_data = [
                        ["FATOR", "PONTOS", "EXPLICAÇÃO"],
                        [
                            "Capacidade da Sala",
                            str(scoring_breakdown.get("capacity_points", 0)),
                            (
                                "Sala adequada para o número de vagas"
                                if scoring_breakdown.get("capacity_satisfied", False)
                                else "Capacidade insuficiente"
                            ),
                        ],
                        [
                            "Regras Obrigatórias",
                            str(scoring_breakdown.get("hard_rules_points", 0)),
                            self._format_hard_rules_explanation(scoring_breakdown),
                        ],
                        [
                            "Preferências Professor",
                            str(scoring_breakdown.get("soft_preference_points", 0)),
                            self._format_preferences_explanation(scoring_breakdown),
                        ],
                        [
                            "Histórico de Uso",
                            str(
                                scoring_breakdown.get("historical_frequency_points", 0)
                            ),
                            f"{scoring_breakdown.get('historical_allocations', 0)} alocações anteriores nesta sala",
                        ],
                        [
                            "TOTAL",
                            str(final_score),
                            "Pontuação final que determinou esta alocação",
                        ],
                    ]

                    breakdown_table = Table(
                        breakdown_data, colWidths=[50 * mm, 20 * mm, 70 * mm]
                    )
                    breakdown_table.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                                ("FONTNAME", (0, 0), (-1, 0), get_table_header_font()),
                                ("FONTSIZE", (0, 0), (-1, 0), 8),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                                ("FONTNAME", (0, 1), (-1, -2), get_table_cell_font()),
                                ("FONTSIZE", (0, 1), (-1, -2), 7),
                                ("ALIGN", (0, 1), (1, -2), "CENTER"),
                                ("ALIGN", (2, 1), (2, -2), "LEFT"),
                                ("VALIGN", (0, 1), (-1, -2), "MIDDLE"),
                                # Total row styling
                                ("BACKGROUND", (0, -1), (-1, -1), colors.lightyellow),
                                (
                                    "FONTNAME",
                                    (0, -1),
                                    (-1, -1),
                                    get_table_header_font(),
                                ),
                                ("FONTSIZE", (0, -1), (-1, -1), 8),
                            ]
                        )
                    )

                    content.append(breakdown_table)

                    # Decision reasoning
                    content.append(Spacer(1, 5))
                    content.append(
                        Paragraph(
                            "<b>💡 Por que esta sala foi escolhida:</b>",
                            self.styles["Normal"],
                        )
                    )

                    reasoning = self._generate_decision_reasoning(
                        decision, scoring_breakdown
                    )
                    content.append(Paragraph(reasoning, self.styles["ScoreDetail"]))

                content.append(Spacer(1, 10))

                # Add page break every 3 allocations to avoid overcrowding
                if (i + 1) % 3 == 0 and i < 19:
                    content.append(PageBreak())

            # Summary note - now showing all allocations
            content.append(
                Paragraph(
                    f"<i>Análise completa de todas as {len(allocated_decisions)} alocações realizadas.</i>",
                    self.styles["Normal"],
                )
            )

        else:
            content.append(
                Paragraph(
                    "ℹ️ Nenhuma decisão de alocação com informações de pontuação disponíveis.",
                    self.styles["Normal"],
                )
            )

        content.append(PageBreak())
        return content

    def _format_hard_rules_explanation(self, scoring_breakdown: Dict) -> str:
        """Format explanation for hard rules satisfied."""
        hard_rules_satisfied = scoring_breakdown.get("hard_rules_satisfied", [])

        if not hard_rules_satisfied:
            return "Nenhuma regra obrigatória atendida"

        if len(hard_rules_satisfied) == 1:
            return f"Regra atendida: {hard_rules_satisfied[0]}"
        else:
            return f"{len(hard_rules_satisfied)} regras obrigatórias atendidas"

    def _format_preferences_explanation(self, scoring_breakdown: Dict) -> str:
        """Format explanation for professor preferences satisfied."""
        soft_preferences_satisfied = scoring_breakdown.get(
            "soft_preferences_satisfied", []
        )

        if not soft_preferences_satisfied:
            return "Nenhuma preferência atendida"

        if len(soft_preferences_satisfied) == 1:
            return f"Preferência atendida: {soft_preferences_satisfied[0]}"
        else:
            return f"{len(soft_preferences_satisfied)} preferências atendidas"

    def _generate_decision_reasoning(
        self, decision: Dict, scoring_breakdown: Dict
    ) -> str:
        """Generate human-readable reasoning for why this allocation was chosen."""
        reasoning_parts = []

        final_score = decision.get("final_score", 0)
        allocation_phase = decision.get("allocation_phase", "")

        # Phase-based reasoning
        if allocation_phase == "hard_rules":
            reasoning_parts.append(
                "• Alocação obrigatória por regras específicas da disciplina"
            )
        elif allocation_phase == "atomic_allocation":
            reasoning_parts.append(
                "• Alocação por pontuação inteligente após avaliação de múltiplas opções"
            )

        # Score-based reasoning
        if final_score >= 15:
            reasoning_parts.append(
                "• Pontuação excelente - combinação ideal de fatores"
            )
        elif final_score >= 10:
            reasoning_parts.append(
                "• Boa pontuação - equilíbrio entre capacidade e preferências"
            )
        elif final_score >= 5:
            reasoning_parts.append("• Pontuação adequada - foco em capacidade básica")
        else:
            reasoning_parts.append(
                "• Pontuação baixa - alocação necessária apesar de limitações"
            )

        # Factor-specific insights
        hard_points = scoring_breakdown.get("hard_rules_points", 0)
        if hard_points > 0:
            reasoning_parts.append(
                f"• Regras obrigatórias contribuíram com {hard_points} pontos"
            )

        pref_points = scoring_breakdown.get("soft_preference_points", 0)
        if pref_points > 0:
            reasoning_parts.append(
                f"• Preferências do professor contribuíram com {pref_points} pontos"
            )

        hist_points = scoring_breakdown.get("historical_frequency_points", 0)
        if hist_points > 0:
            hist_count = scoring_breakdown.get("historical_allocations", 0)
            reasoning_parts.append(
                f"• Histórico de {hist_count} usos anteriores nesta sala"
            )

        capacity_satisfied = scoring_breakdown.get("capacity_satisfied", False)
        if capacity_satisfied:
            reasoning_parts.append("• Capacidade da sala adequada para a demanda")

        return "\n".join(reasoning_parts)

    def _build_allocation_decisions(self, decisions: List[Dict[str, Any]]) -> List[Any]:
        """Build detailed allocation decisions section."""
        content = []

        content.append(
            Paragraph("DECISÕES DE ALOCAÇÃO DETALHADAS", self.styles["SectionHeader"])
        )

        # Group decisions by allocation status
        allocated_decisions = [d for d in decisions if d.get("allocated", False)]
        skipped_decisions = [d for d in decisions if not d.get("allocated", False)]

        # Show allocated decisions
        if allocated_decisions:
            content.append(
                Paragraph("Demandas Alocadas com Sucesso", self.styles["Heading3"])
            )

            for decision in allocated_decisions[:10]:  # Limit to first 10
                disciplina = decision.get("disciplina_codigo", "N/A")
                nome = decision.get("disciplina_nome", "N/A")
                sala = decision.get("allocated_room_name", "N/A")
                score = decision.get("final_score", 0)
                phase = decision.get("allocation_phase", "N/A")

                content.append(
                    Paragraph(
                        f"<b>{disciplina} - {nome}</b>", self.styles["DecisionHeader"]
                    )
                )

                details = f"""
                • Sala Alocada: <b>{sala}</b><br/>
                • Pontuação Final: <b>{score}</b><br/>
                • Fase de Alocação: {phase}<br/>
                • Vagas: {decision.get('vagas', 0)}<br/>
                • Professor(es): {decision.get('professores', 'N/A')}
                """

                content.append(Paragraph(details, self.styles["Normal"]))
                content.append(Spacer(1, 8))

        # Show skipped decisions with reasons
        if skipped_decisions:
            content.append(Spacer(1, 15))
            content.append(Paragraph("Demandas Não Alocadas", self.styles["Heading3"]))

            # Group by skip reason
            reason_groups = {}
            for decision in skipped_decisions[:15]:  # Limit to first 15
                reason = decision.get("skipped_reason", "Motivo não especificado")
                if reason not in reason_groups:
                    reason_groups[reason] = []
                reason_groups[reason].append(decision)

            for reason, decisions_list in reason_groups.items():
                content.append(
                    Paragraph(
                        f"Motivo: {reason} ({len(decisions_list)} demandas)",
                        self.styles["DecisionHeader"],
                    )
                )

                for decision in decisions_list[:5]:  # Limit to 5 per reason
                    disciplina = decision.get("disciplina_codigo", "N/A")
                    nome = decision.get("disciplina_nome", "N/A")
                    score = decision.get("final_score", 0)

                    content.append(
                        Paragraph(
                            f"• <b>{disciplina}</b> - {nome} (Pontuação: {score})",
                            self.styles["ScoreDetail"],
                        )
                    )

                if len(decisions_list) > 5:
                    content.append(
                        Paragraph(
                            f"• ... e mais {len(decisions_list) - 5} demandas",
                            self.styles["ScoreDetail"],
                        )
                    )

                content.append(Spacer(1, 8))

        content.append(PageBreak())

        return content

    def _build_scoring_analysis(self, decisions: List[Dict[str, Any]]) -> List[Any]:
        """Build scoring analysis section."""
        content = []

        content.append(Paragraph("ANÁLISE DE PONTUAÇÃO", self.styles["SectionHeader"]))

        # Analyze score distribution
        scores = [
            d.get("final_score", 0)
            for d in decisions
            if d.get("final_score") is not None
        ]

        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)

            content.append(
                Paragraph("Distribuição de Pontuações", self.styles["Heading3"])
            )

            score_stats = [
                ["MÉTRICA", "VALOR"],
                ["Pontuação Média", f"{avg_score:.1f}"],
                ["Pontuação Máxima", str(max_score)],
                ["Pontuação Mínima", str(min_score)],
                ["Total Avaliado", str(len(scores))],
            ]

            score_table = Table(score_stats, colWidths=[60 * mm, 30 * mm])
            score_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, 0), get_table_header_font()),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTNAME", (0, 1), (-1, -1), get_table_cell_font()),
                    ]
                )
            )

            content.append(score_table)
            content.append(Spacer(1, 15))

        # Show scoring breakdown examples
        content.append(
            Paragraph("Exemplos de Análise de Pontuação", self.styles["Heading3"])
        )

        # Get examples of different score ranges
        high_score_examples = [d for d in decisions if d.get("final_score", 0) >= 12][
            :3
        ]
        medium_score_examples = [
            d for d in decisions if 6 <= d.get("final_score", 0) < 12
        ][:2]
        low_score_examples = [d for d in decisions if 0 < d.get("final_score", 0) < 6][
            :2
        ]

        for examples, title in [
            (high_score_examples, "Pontuações Altas (≥12)"),
            (medium_score_examples, "Pontuações Médias (6-11)"),
            (low_score_examples, "Pontuações Baixas (1-5)"),
        ]:
            if examples:
                content.append(Paragraph(title, self.styles["Normal"]))
                for decision in examples:
                    breakdown = decision.get("scoring_breakdown", {})
                    if breakdown:
                        score_text = f"""
                        <b>{decision.get('disciplina_codigo', 'N/A')}</b> - Total: {decision.get('final_score', 0)}<br/>
                        • Capacidade: {breakdown.get('capacity_points', 0)} pontos<br/>
                        • Regras Obrigatórias: {breakdown.get('hard_rules_points', 0)} pontos<br/>
                        • Preferências: {breakdown.get('soft_preference_points', 0)} pontos<br/>
                        • Histórico: {breakdown.get('historical_frequency_points', 0)} pontos
                        """
                        content.append(
                            Paragraph(score_text, self.styles["ScoreDetail"])
                        )
                content.append(Spacer(1, 10))

        return content

    def _build_room_utilization_analysis(
        self, decisions: List[Dict[str, Any]]
    ) -> List[Any]:
        """Build comprehensive room utilization analysis section."""
        content = []

        content.append(
            Paragraph("ANÁLISE DE UTILIZAÇÃO DE SALAS", self.styles["SectionHeader"])
        )

        # Count room usage with capacity analysis
        room_usage = {}
        room_capacities = {}
        room_total_students = {}

        for decision in decisions:
            if decision.get("allocated", False):
                room_name = decision.get("allocated_room_name", "N/A")
                if room_name != "N/A":
                    room_usage[room_name] = room_usage.get(room_name, 0) + 1
                    # Track capacity usage
                    room_capacity = decision.get("room_capacity", 0)
                    demand_vagas = decision.get("vagas", 0)
                    if room_capacity > 0:
                        room_capacities[room_name] = room_capacity
                        room_total_students[room_name] = (
                            room_total_students.get(room_name, 0) + demand_vagas
                        )

        if room_usage:
            # Sort by usage
            sorted_rooms = sorted(room_usage.items(), key=lambda x: x[1], reverse=True)

            content.append(Paragraph("Salas Mais Utilizadas", self.styles["Heading3"]))

            room_data = [["Sala", "Alocações", "% Total", "Taxa Ocupação Média"]]
            total_allocations = sum(room_usage.values())

            for room_name, count in sorted_rooms[:15]:  # Top 15 rooms
                percentage = (
                    (count / total_allocations * 100) if total_allocations > 0 else 0
                )

                # Calculate average occupancy rate
                if room_name in room_capacities and room_capacities[room_name] > 0:
                    avg_students_per_alloc = (
                        room_total_students.get(room_name, 0) / count
                    )
                    occupancy_rate = (
                        avg_students_per_alloc / room_capacities[room_name]
                    ) * 100
                    occupancy_str = f"{occupancy_rate:.0f}%"
                else:
                    occupancy_str = "N/A"

                room_data.append(
                    [room_name, str(count), f"{percentage:.1f}%", occupancy_str]
                )

            room_table = Table(
                room_data, colWidths=[45 * mm, 25 * mm, 22 * mm, 35 * mm]
            )
            room_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, 0), get_table_header_font()),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTNAME", (0, 1), (-1, -1), get_table_cell_font()),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.lightgrey],
                        ),
                    ]
                )
            )

            content.append(room_table)
            content.append(Spacer(1, 10))

            # Analysis interpretation
            top_3_rooms = sorted_rooms[:3]
            top_3_usage = sum(count for _, count in top_3_rooms)
            top_3_percentage = (
                (top_3_usage / total_allocations * 100) if total_allocations > 0 else 0
            )

            interpretation = f"<b>Concentração de uso:</b> As 3 salas mais utilizadas ({', '.join(name for name, _ in top_3_rooms)}) representam {top_3_percentage:.1f}% das alocações. "

            if top_3_percentage > 40:
                interpretation += "⚠️ Alta concentração - considerar distribuir melhor a carga entre salas."
            else:
                interpretation += "✓ Distribuição equilibrada entre salas disponíveis."

            content.append(Paragraph(interpretation, self.styles["Normal"]))

        content.append(Spacer(1, 15))

        return content

    def _build_recommendations(
        self, results: Dict[str, Any], decisions: List[Dict[str, Any]]
    ) -> List[Any]:
        """Build actionable recommendations section with priorities."""
        content = []

        content.append(
            Paragraph("RECOMENDAÇÕES PRIORITÁRIAS", self.styles["SectionHeader"])
        )

        recommendations = []

        # Analyze success rate
        success_rate = results.get("progress_percentage", 0)
        total_demands = results.get("total_demands_processed", 0)
        allocated = results.get("allocations_completed", 0)
        skipped = results.get("demands_skipped", 0)

        # Critical recommendations (HIGH priority)
        if success_rate < 50:
            recommendations.append(
                {
                    "priority": "🔴 CRÍTICO",
                    "action": f"Taxa de sucesso muito baixa ({success_rate:.1f}%) - REQUER AÇÃO IMEDIATA",
                    "reason": f"{skipped} de {total_demands} demandas não foram alocadas. Sistema pode estar mal configurado.",
                    "steps": [
                        "1. Verificar se há salas suficientes cadastradas no sistema",
                        "2. Revisar todas as regras obrigatórias - podem estar muito restritivas",
                        "3. Analisar conflitos de horário - pode haver sobreposição excessiva",
                        "4. Considerar ajustar pesos do sistema de pontuação",
                    ],
                }
            )
        elif success_rate < 70:
            recommendations.append(
                {
                    "priority": "🟠 ALTO",
                    "action": f"Taxa de sucesso baixa ({success_rate:.1f}%) - necessita melhorias",
                    "reason": f"{skipped} demandas não alocadas indicam gargalos no sistema.",
                    "steps": [
                        "1. Identificar demandas com mais conflitos e revisar horários",
                        "2. Verificar se regras obrigatórias estão bem balanceadas",
                        "3. Analisar distribuição de demandas por turno (pode estar desbalanceada)",
                    ],
                }
            )

        # Check for conflicts
        total_conflicts = results.get("conflicts_found", 0)
        if (
            total_conflicts > allocated * 0.5
        ):  # More conflicts than successful allocations
            recommendations.append(
                {
                    "priority": "🟠 ALTO",
                    "action": f"Excesso de conflitos detectados ({total_conflicts} conflitos)",
                    "reason": "Número de conflitos superior a alocações bem-sucedidas indica problemas estruturais.",
                    "steps": [
                        "1. Revisar matriz de horários - pode haver sobreposição excessiva",
                        "2. Verificar se salas estão sendo compartilhadas adequadamente",
                        "3. Considerar criar mais salas ou redistribuir demandas entre turnos",
                    ],
                }
            )
        elif total_conflicts > 0:
            recommendations.append(
                {
                    "priority": "🟡 MÉDIO",
                    "action": f"Conflitos de horário detectados ({total_conflicts} conflitos)",
                    "reason": "Conflitos normais do processo de alocação, mas podem ser reduzidos.",
                    "steps": [
                        "1. Analisar padrões de conflito mais comuns",
                        "2. Sugerir ajustes de horário para demandas problemáticas",
                        "3. Verificar se candidatos alternativos estão sendo bem avaliados",
                    ],
                }
            )

        # Check for exhausted candidates
        exhausted_candidates = [
            d
            for d in decisions
            if not d.get("allocated")
            and "candidates" in str(d.get("skipped_reason", "")).lower()
        ]
        if len(exhausted_candidates) > total_demands * 0.1:  # More than 10%
            recommendations.append(
                {
                    "priority": "🟠 ALTO",
                    "action": f"{len(exhausted_candidates)} demandas esgotaram TODOS os candidatos",
                    "reason": "Demandas não têm opções viáveis - pode indicar falta de salas adequadas.",
                    "steps": [
                        "1. Listar demandas afetadas e analisar requisitos (capacidade, tipo, etc.)",
                        "2. Verificar se há salas disponíveis que não estão sendo consideradas",
                        "3. Considerar relaxar algumas regras obrigatórias para estas demandas",
                        "4. Avaliar necessidade de criar novas salas ou ajustar capacidades",
                    ],
                }
            )

        # Check scoring effectiveness
        allocated_decisions = [d for d in decisions if d.get("allocated")]
        low_score_allocs = [
            d for d in allocated_decisions if d.get("final_score", 0) < 8
        ]
        if len(low_score_allocs) > len(allocated_decisions) * 0.2:  # More than 20%
            recommendations.append(
                {
                    "priority": "🟡 MÉDIO",
                    "action": f"{len(low_score_allocs)} alocações com pontuação baixa (<8 pontos)",
                    "reason": "Muitas alocações subótimas podem indicar sistema de pontuação ineficaz.",
                    "steps": [
                        "1. Revisar pesos do sistema de pontuação (capacidade, preferências, histórico)",
                        "2. Verificar se preferências de professores estão cadastradas",
                        "3. Analisar se histórico de uso está sendo considerado adequadamente",
                        "4. Considerar aumentar peso de fatores mais importantes",
                    ],
                }
            )

        # Phase-specific recommendations
        phase1_allocs = results.get("phase1_hard_rules", {}).get("allocations", 0)
        phase3_allocs = results.get("phase3_atomic_allocation", {}).get(
            "allocations", 0
        )

        if phase1_allocs == 0 and phase3_allocs > 0 and total_demands > 20:
            recommendations.append(
                {
                    "priority": "🔵 BAIXO",
                    "action": "Nenhuma alocação por regras obrigatórias",
                    "reason": "Todas as alocações foram por pontuação. Regras obrigatórias poderiam otimizar processo.",
                    "steps": [
                        "1. Identificar demandas que sempre usam mesmas salas (padrões recorrentes)",
                        "2. Criar regras obrigatórias para estes casos (ex: labs específicos)",
                        "3. Isso reduzirá tempo de processamento e melhorará previsibilidade",
                    ],
                }
            )

        # Success case
        if success_rate >= 90 and total_conflicts < allocated * 0.3:
            recommendations.append(
                {
                    "priority": "✅ ÓTIMO",
                    "action": f"Sistema funcionando muito bem! ({success_rate:.1f}% de sucesso)",
                    "reason": "Resultados excelentes com baixo índice de conflitos.",
                    "steps": [
                        "1. Manter configurações atuais para próximos semestres",
                        "2. Documentar configurações de sucesso como baseline",
                        "3. Monitorar métricas para detectar degradação futura",
                        "4. Considerar usar este semestre como referência para calibração",
                    ],
                }
            )

        # Add default recommendation if none
        if not recommendations:
            recommendations.append(
                {
                    "priority": "ℹ️ INFO",
                    "action": "Resultados dentro do esperado",
                    "reason": "Sistema operando normalmente sem problemas críticos.",
                    "steps": [
                        "1. Continuar monitorando métricas de alocação",
                        "2. Analisar manualmente demandas não alocadas",
                        "3. Coletar feedback de coordenadores e professores",
                    ],
                }
            )

        # Display recommendations
        for i, rec in enumerate(recommendations, 1):
            # Priority styling
            if "CRÍTICO" in rec["priority"]:
                priority_color = colors.red
            elif "ALTO" in rec["priority"]:
                priority_color = colors.orange
            elif "MÉDIO" in rec["priority"]:
                priority_color = colors.blue
            elif "ÓTIMO" in rec["priority"]:
                priority_color = colors.green
            else:
                priority_color = colors.grey

            content.append(
                Paragraph(
                    f"<b>{rec['priority']}</b> - {rec['action']}",
                    ParagraphStyle(
                        f"RecommendationTitle{i}",
                        parent=self.styles["Heading3"],
                        textColor=priority_color,
                        fontSize=11,
                    ),
                )
            )

            content.append(
                Paragraph(
                    f"<b>Justificativa:</b> {rec['reason']}",
                    self.styles["Normal"],
                )
            )

            if rec.get("steps"):
                content.append(
                    Paragraph("<b>Passos Recomendados:</b>", self.styles["Normal"])
                )
                for step in rec["steps"]:
                    content.append(Paragraph(step, self.styles["ScoreDetail"]))

            content.append(Spacer(1, 12))

        # Footer
        content.append(Spacer(1, 15))
        content.append(Paragraph("-" * 76, self.styles["Normal"]))
        content.append(Spacer(1, 5))
        content.append(
            Paragraph(
                f"<b>Relatório gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</b>",
                ParagraphStyle(
                    "Footer",
                    parent=self.styles["Normal"],
                    alignment=TA_CENTER,
                    fontSize=8,
                ),
            )
        )
        content.append(
            Paragraph(
                "Sistema de Ensalamento FUP/UnB - Alocação Autônoma Inteligente",
                ParagraphStyle(
                    "FooterSub",
                    parent=self.styles["Normal"],
                    alignment=TA_CENTER,
                    fontSize=7,
                    textColor=colors.grey,
                ),
            )
        )

        return content
