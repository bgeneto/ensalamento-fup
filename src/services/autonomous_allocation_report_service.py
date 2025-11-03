"""
Autonomous Allocation PDF Report Generator - Human-readable allocation decision reports
"""

import io
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import Color, black, white, grey, lightgrey, green, red, blue
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Suppress ReportLab logging completely
logging.getLogger('reportlab').setLevel(logging.ERROR)
logging.getLogger('reportlab.lib').setLevel(logging.ERROR)
logging.getLogger('reportlab.pdfgen').setLevel(logging.ERROR)
logging.getLogger('reportlab.platypus').setLevel(logging.ERROR)
logging.getLogger('reportlab.pdfbase').setLevel(logging.ERROR)
logging.getLogger('reportlab.pdfbase.pdfmetrics').setLevel(logging.ERROR)
logging.getLogger('reportlab.pdfbase.ttfonts').setLevel(logging.ERROR)

# Import existing styles from statistics service
from src.services.statistics_report_service import StatisticsReportService


class AutonomousAllocationReportService:
    """Service for generating human-readable PDF reports of autonomous allocation decisions."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.stats_service = StatisticsReportService()
    
    def _setup_custom_styles(self):
        """Setup custom styles for the allocation report."""
        
        # Title styles
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Title'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.darkblue,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section header styles
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.darkblue,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderColor=colors.lightgrey,
            borderPadding=5
        ))
        
        # Decision styles
        self.styles.add(ParagraphStyle(
            name='DecisionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            backgroundColor=colors.lightgrey
        ))
        
        # Success/Failure styles
        self.styles.add(ParagraphStyle(
            name='SuccessText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.green,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='FailureText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.red,
            fontName='Helvetica-Bold'
        ))
        
        # Score breakdown styles
        self.styles.add(ParagraphStyle(
            name='ScoreDetail',
            parent=self.styles['Normal'],
            fontSize=9,
            leftIndent=20,
            spaceAfter=2,
            fontName='Helvetica'
        ))
        
        # Table styles
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='TableCell',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))
    
    def generate_autonomous_allocation_report(
        self,
        allocation_results: Dict[str, Any],
        allocation_decisions: List[Dict[str, Any]],
        semester_name: str,
        execution_time: float = 0.0
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
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            title=f"Relatório de Alocação Autônoma - {semester_name}",
            author="Sistema de Ensalamento FUP/UnB"
        )
        
        # Build document content
        story = []
        
        # Title page
        story.extend(self._build_title_page(semester_name, allocation_results, execution_time))
        
        # Executive summary
        story.extend(self._build_executive_summary(allocation_results))
        
        # Phase-by-phase analysis
        story.extend(self._build_phase_analysis(allocation_results))
        
        # Detailed allocation decisions
        story.extend(self._build_allocation_decisions(allocation_decisions))
        
        # Scoring analysis
        story.extend(self._build_scoring_analysis(allocation_decisions))
        
        # Room utilization analysis
        story.extend(self._build_room_utilization_analysis(allocation_decisions))
        
        # Recommendations
        story.extend(self._build_recommendations(allocation_results, allocation_decisions))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
    
    def _build_title_page(self, semester_name: str, results: Dict[str, Any], execution_time: float) -> List[Any]:
        """Build title page with key metrics."""
        content = []
        
        # Main title
        content.append(Paragraph("RELATÓRIO DE ALOCAÇÃO AUTÔNOMA", self.styles['ReportTitle']))
        content.append(Spacer(1, 10))
        
        # Semester and execution info
        content.append(Paragraph(f"Semestre: {semester_name}", self.styles['Heading3']))
        content.append(Paragraph(f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", self.styles['Normal']))
        content.append(Paragraph(f"Tempo de Execução: {execution_time:.2f} segundos", self.styles['Normal']))
        
        # Key metrics box
        content.append(Spacer(1, 20))
        
        metrics_data = [
            ['MÉTRICA', 'VALOR', 'DETALHES'],
            ['Total de Demandas Processadas', str(results.get('total_demands_processed', 0)), '100%'],
            ['Alocações Realizadas', str(results.get('allocations_completed', 0)), f"{results.get('progress_percentage', 0):.1f}%"],
            ['Conflitos Encontrados', str(results.get('conflicts_found', 0)), 'Durante análise'],
            ['Demandas Não Alocadas', str(results.get('demands_skipped', 0)), 'Requerem intervenção manual']
        ]
        
        metrics_table = Table(metrics_data, colWidths=[80*mm, 30*mm, 30*mm])
        metrics_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        content.append(metrics_table)
        content.append(PageBreak())
        
        return content
    
    def _build_executive_summary(self, results: Dict[str, Any]) -> List[Any]:
        """Build executive summary section."""
        content = []
        
        content.append(Paragraph("RESUMO EXECUTIVO", self.styles['SectionHeader']))
        
        # Overall performance
        success_rate = results.get('progress_percentage', 0)
        if success_rate >= 80:
            performance_text = "EXCELENTE"
            performance_color = colors.green
        elif success_rate >= 60:
            performance_text = "BOM"
            performance_color = colors.orange
        else:
            performance_text = "REQUER ATENCAO"
            performance_color = colors.red
        
        content.append(Paragraph(
            f"<b>Performance Geral:</b> {performance_text} ({success_rate:.1f}% de sucesso)",
            ParagraphStyle('PerformanceText', parent=self.styles['Normal'], 
                          fontName='Helvetica-Bold', 
                          textColor=performance_color)
        ))
        
        content.append(Spacer(1, 10))
        
        # Phase summary
        phase1 = results.get('phase1_hard_rules', {})
        phase2 = results.get('phase2_soft_scoring', {})
        phase3 = results.get('phase3_atomic_allocation', {})
        
        summary_text = f"""
        <b>Fase 1 - Regras Obrigatórias:</b> {phase1.get('allocations', 0)} alocações realizadas, {phase1.get('conflicts', 0)} conflitos.<br/>
        <b>Fase 2 - Avaliação por Pontuação:</b> {phase2.get('candidates_scored', 0)} demandas avaliadas, {phase2.get('conflicts', 0)} conflitos detectados.<br/>
        <b>Fase 3 - Alocação Atômica:</b> {phase3.get('allocations', 0)} alocações finais, {phase3.get('conflicts', 0)} conflitos restantes.<br/>
        <br/>
        <b>Próximos Passos:</b> {results.get('next_steps', 'Análise manual das demandas não alocadas')}
        """
        
        content.append(Paragraph(summary_text, self.styles['Normal']))
        content.append(Spacer(1, 15))
        
        return content
    
    def _build_phase_analysis(self, results: Dict[str, Any]) -> List[Any]:
        """Build detailed phase analysis section."""
        content = []
        
        content.append(Paragraph("ANÁLISE DETALHADA POR FASE", self.styles['SectionHeader']))
        
        # Phase 1 Analysis
        content.append(Paragraph("Fase 1: Regras Obrigatórias", self.styles['Heading3']))
        phase1 = results.get('phase1_hard_rules', {})
        
        if phase1.get('allocations', 0) > 0:
            content.append(Paragraph(
                f"<b>Sucesso:</b> {phase1.get('allocations', 0)} demandas alocadas automaticamente por satisfazerem todas as regras obrigatórias.",
                self.styles['SuccessText']
            ))
        else:
            content.append(Paragraph(
                "<b>Observacao:</b> Nenhuma demanda alocada nesta fase. Isso pode indicar ausencia de regras obrigatorias especificas.",
                self.styles['Normal']
            ))
        
        content.append(Paragraph(
            f"Conflitos encontrados: {phase1.get('conflicts', 0)}",
            self.styles['Normal']
        ))
        
        # Phase 2 Analysis
        content.append(Spacer(1, 10))
        content.append(Paragraph("Fase 2: Avaliação por Pontuação", self.styles['Heading3']))
        phase2 = results.get('phase2_soft_scoring', {})
        
        content.append(Paragraph(
            f"<b>Demandas Avaliadas:</b> {phase2.get('candidates_scored', 0)}",
            self.styles['Normal']
        ))
        content.append(Paragraph(
            f"<b>Candidatos Gerados:</b> {phase2.get('candidates_generated', 0)}",
            self.styles['Normal']
        ))
        content.append(Paragraph(
            f"<b>Conflitos Detectados:</b> {phase2.get('conflicts', 0)}",
            self.styles['Normal']
        ))
        
        # Phase 3 Analysis
        content.append(Spacer(1, 10))
        content.append(Paragraph("Fase 3: Alocação Atômica", self.styles['Heading3']))
        phase3 = results.get('phase3_atomic_allocation', {})
        
        if phase3.get('allocations', 0) > 0:
            content.append(Paragraph(
                f"<b>Alocações Realizadas:</b> {phase3.get('allocations', 0)} demandas alocadas com base na pontuação mais alta.",
                self.styles['SuccessText']
            ))
        else:
            content.append(Paragraph(
                "<b>Falha na Alocação:</b> Nenhuma alocação realizada na fase final. Verificar conflitos de horário.",
                self.styles['WarningText']
            ))
        
        content.append(Spacer(1, 15))
        
        return content
    
    def _build_allocation_decisions(self, decisions: List[Dict[str, Any]]) -> List[Any]:
        """Build detailed allocation decisions section."""
        content = []
        
        content.append(Paragraph("DECISÕES DE ALOCAÇÃO DETALHADAS", self.styles['SectionHeader']))
        
        # Group decisions by allocation status
        allocated_decisions = [d for d in decisions if d.get('allocated', False)]
        skipped_decisions = [d for d in decisions if not d.get('allocated', False)]
        
        # Show allocated decisions
        if allocated_decisions:
            content.append(Paragraph("Demandas Alocadas com Sucesso", self.styles['Heading3']))
            
            for decision in allocated_decisions[:10]:  # Limit to first 10
                disciplina = decision.get('disciplina_codigo', 'N/A')
                nome = decision.get('disciplina_nome', 'N/A')
                sala = decision.get('allocated_room_name', 'N/A')
                score = decision.get('final_score', 0)
                phase = decision.get('allocation_phase', 'N/A')
                
                content.append(Paragraph(
                    f"<b>{disciplina} - {nome}</b>",
                    self.styles['DecisionHeader']
                ))
                
                details = f"""
                • Sala Alocada: <b>{sala}</b><br/>
                • Pontuação Final: <b>{score}</b><br/>
                • Fase de Alocação: {phase}<br/>
                • Vagas: {decision.get('vagas', 0)}<br/>
                • Professor(es): {decision.get('professores', 'N/A')}
                """
                
                content.append(Paragraph(details, self.styles['Normal']))
                content.append(Spacer(1, 8))
        
        # Show skipped decisions with reasons
        if skipped_decisions:
            content.append(Spacer(1, 15))
            content.append(Paragraph("Demandas Não Alocadas", self.styles['Heading3']))
            
            # Group by skip reason
            reason_groups = {}
            for decision in skipped_decisions[:15]:  # Limit to first 15
                reason = decision.get('skipped_reason', 'Motivo não especificado')
                if reason not in reason_groups:
                    reason_groups[reason] = []
                reason_groups[reason].append(decision)
            
            for reason, decisions_list in reason_groups.items():
                content.append(Paragraph(
                    f"Motivo: {reason} ({len(decisions_list)} demandas)",
                    self.styles['DecisionHeader']
                ))
                
                for decision in decisions_list[:5]:  # Limit to 5 per reason
                    disciplina = decision.get('disciplina_codigo', 'N/A')
                    nome = decision.get('disciplina_nome', 'N/A')
                    score = decision.get('final_score', 0)
                    
                    content.append(Paragraph(
                        f"• <b>{disciplina}</b> - {nome} (Pontuação: {score})",
                        self.styles['ScoreDetail']
                    ))
                
                if len(decisions_list) > 5:
                    content.append(Paragraph(
                        f"• ... e mais {len(decisions_list) - 5} demandas",
                        self.styles['ScoreDetail']
                    ))
                
                content.append(Spacer(1, 8))
        
        content.append(PageBreak())
        
        return content
    
    def _build_scoring_analysis(self, decisions: List[Dict[str, Any]]) -> List[Any]:
        """Build scoring analysis section."""
        content = []
        
        content.append(Paragraph("ANÁLISE DE PONTUAÇÃO", self.styles['SectionHeader']))
        
        # Analyze score distribution
        scores = [d.get('final_score', 0) for d in decisions if d.get('final_score') is not None]
        
        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            
            content.append(Paragraph("Distribuição de Pontuações", self.styles['Heading3']))
            
            score_stats = [
                ['MÉTRICA', 'VALOR'],
                ['Pontuação Média', f'{avg_score:.1f}'],
                ['Pontuação Máxima', str(max_score)],
                ['Pontuação Mínima', str(min_score)],
                ['Total Avaliado', str(len(scores))]
            ]
            
            score_table = Table(score_stats, colWidths=[60*mm, 30*mm])
            score_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ]))
            
            content.append(score_table)
            content.append(Spacer(1, 15))
        
        # Show scoring breakdown examples
        content.append(Paragraph("Exemplos de Análise de Pontuação", self.styles['Heading3']))
        
        # Get examples of different score ranges
        high_score_examples = [d for d in decisions if d.get('final_score', 0) >= 12][:3]
        medium_score_examples = [d for d in decisions if 6 <= d.get('final_score', 0) < 12][:2]
        low_score_examples = [d for d in decisions if 0 < d.get('final_score', 0) < 6][:2]
        
        for examples, title in [(high_score_examples, "Pontuações Altas (≥12)"), 
                                (medium_score_examples, "Pontuações Médias (6-11)"),
                                (low_score_examples, "Pontuações Baixas (1-5)")]:
            if examples:
                content.append(Paragraph(title, self.styles['Normal']))
                for decision in examples:
                    breakdown = decision.get('scoring_breakdown', {})
                    if breakdown:
                        score_text = f"""
                        <b>{decision.get('disciplina_codigo', 'N/A')}</b> - Total: {decision.get('final_score', 0)}<br/>
                        • Capacidade: {breakdown.get('capacity_points', 0)} pontos<br/>
                        • Regras Obrigatórias: {breakdown.get('hard_rules_points', 0)} pontos<br/>
                        • Preferências: {breakdown.get('soft_preference_points', 0)} pontos<br/>
                        • Histórico: {breakdown.get('historical_frequency_points', 0)} pontos
                        """
                        content.append(Paragraph(score_text, self.styles['ScoreDetail']))
                content.append(Spacer(1, 10))
        
        return content
    
    def _build_room_utilization_analysis(self, decisions: List[Dict[str, Any]]) -> List[Any]:
        """Build room utilization analysis section."""
        content = []
        
        content.append(Paragraph("ANÁLISE DE UTILIZAÇÃO DE SALAS", self.styles['SectionHeader']))
        
        # Count room usage
        room_usage = {}
        for decision in decisions:
            if decision.get('allocated', False):
                room_name = decision.get('allocated_room_name', 'N/A')
                if room_name != 'N/A':
                    room_usage[room_name] = room_usage.get(room_name, 0) + 1
        
        if room_usage:
            # Sort by usage
            sorted_rooms = sorted(room_usage.items(), key=lambda x: x[1], reverse=True)
            
            content.append(Paragraph("Salas Mais Utilizadas", self.styles['Heading3']))
            
            room_data = [['Sala', 'Alocações', 'Percentual']]
            total_allocations = sum(room_usage.values())
            
            for room_name, count in sorted_rooms[:10]:  # Top 10 rooms
                percentage = (count / total_allocations * 100) if total_allocations > 0 else 0
                room_data.append([room_name, str(count), f'{percentage:.1f}%'])
            
            room_table = Table(room_data, colWidths=[60*mm, 25*mm, 25*mm])
            room_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            content.append(room_table)
        
        content.append(Spacer(1, 15))
        
        return content
    
    def _build_recommendations(self, results: Dict[str, Any], decisions: List[Dict[str, Any]]) -> List[Any]:
        """Build recommendations section."""
        content = []
        
        content.append(Paragraph("RECOMENDAÇÕES", self.styles['SectionHeader']))
        
        recommendations = []
        
        # Analyze success rate
        success_rate = results.get('progress_percentage', 0)
        if success_rate < 60:
            recommendations.append({
                'priority': 'ALTA',
                'action': 'Revisar regras de alocação e preferências',
                'reason': 'Taxa de sucesso baixa indica possíveis conflitos sistemáticos'
            })
        elif success_rate < 80:
            recommendations.append({
                'priority': 'MÉDIA',
                'action': 'Analisar demandas não alocadas manualmente',
                'reason': 'Algumas demandas podem necessitar intervenção manual'
            })
        
        # Check for conflicts
        total_conflicts = results.get('conflicts_found', 0)
        if total_conflicts > 0:
            recommendations.append({
                'priority': 'MÉDIA',
                'action': 'Investigar conflitos de horário',
                'reason': f'{total_conflicts} conflitos detectados podem indicar sobreposição de horários'
            })
        
        # Check phase performance
        phase1 = results.get('phase1_hard_rules', {})
        phase3 = results.get('phase3_atomic_allocation', {})
        
        if phase1.get('allocations', 0) == 0 and phase3.get('allocations', 0) > 0:
            recommendations.append({
                'priority': 'BAIXA',
                'action': 'Considerar criar mais regras obrigatórias',
                'reason': 'Alocações feitas apenas por pontuação, regras poderiam otimizar'
            })
        
        # Add default recommendation if none
        if not recommendations:
            recommendations.append({
                'priority': 'INFORMATIVA',
                'action': 'Monitorar resultados próximos semestres',
                'reason': 'Processo executado com sucesso, manter configurações atuais'
            })
        
        # Display recommendations
        for i, rec in enumerate(recommendations, 1):
            priority_color = colors.red if rec['priority'] == 'ALTA' else colors.orange if rec['priority'] == 'MÉDIA' else colors.blue
            
            content.append(Paragraph(
                f"{i}. {rec['action']}",
                ParagraphStyle('RecommendationTitle', parent=self.styles['Normal'], 
                              fontName='Helvetica-Bold', 
                              textColor=priority_color)
            ))
            
            content.append(Paragraph(
                f"   Prioridade: {rec['priority']} - {rec['reason']}",
                self.styles['ScoreDetail']
            ))
            content.append(Spacer(1, 8))
        
        # Footer
        content.append(Spacer(1, 20))
        content.append(Paragraph(
            "---",
            self.styles['Normal']
        ))
        content.append(Paragraph(
            f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} pelo Sistema de Ensalamento FUP/UnB",
            self.styles['Normal']
        ))
        
        return content
