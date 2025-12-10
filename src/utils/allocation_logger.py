"""
Allocation Decision Logger - Detailed logging for autonomous allocation decisions
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Check if DEBUG mode is enabled
DEBUG_MODE = os.environ.get("DEBUG", "False").lower() == "true"

# Configure detailed allocation logger (only if DEBUG is enabled)
allocation_logger = logging.getLogger("allocation_decisions")
if DEBUG_MODE:
    allocation_logger.setLevel(logging.DEBUG)

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Create file handler for allocation decisions
    file_handler = logging.FileHandler("logs/autonomous_allocation_decisions.log")
    file_handler.setLevel(logging.DEBUG)

    # Create detailed formatter
    detailed_formatter = logging.Formatter(
        "%(asctime)s - ALLOCATION_DECISION - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(detailed_formatter)
    allocation_logger.addHandler(file_handler)
else:
    # Disable logging in production
    allocation_logger.setLevel(logging.CRITICAL)  # Higher than any actual logs


@dataclass
class AllocationDecision:
    """Detailed record of an allocation decision."""

    timestamp: str
    semester_id: int
    demanda_id: int
    disciplina_codigo: str
    disciplina_nome: str
    turma: str
    vagas: int
    professores: str

    # Allocation result
    allocated: bool
    allocated_room_id: Optional[int]
    allocated_room_name: Optional[str]
    allocation_phase: str  # "hard_rules", "soft_scoring", "atomic_allocation"

    # Scoring details
    final_score: Optional[int]
    scoring_breakdown: Optional[Dict[str, Any]]

    # Room candidates considered
    total_candidates_evaluated: int
    top_3_candidates: List[Dict[str, Any]]

    # Rules and preferences
    hard_rules_found: List[str]
    hard_rules_satisfied: List[str]
    professor_preferences: List[str]
    professor_preferences_satisfied: List[str]

    # Historical data
    historical_allocations_count: int
    historical_frequency_bonus: int

    # Conflict information
    conflicts_detected: int
    conflict_details: List[str]

    # Decision reasoning
    decision_reason: str
    skipped_reason: Optional[str]


class AllocationDecisionLogger:
    """Logger for detailed allocation decision tracking."""

    def __init__(self):
        self.decisions: List[AllocationDecision] = []
        self.session_start = datetime.now().isoformat()
        # Cache for hybrid detection data (Phase 0 results)
        self.hybrid_data: Dict[str, Any] = {
            "detected_count": 0,
            "detection_semester_id": None,
            "hybrid_disciplines": [],
            "details": {},
        }

    def log_allocation_attempt(
        self,
        semester_id: int,
        demanda: Any,
        phase: str,
        allocated: bool,
        allocated_room: Optional[Any] = None,
        final_score: Optional[int] = None,
        scoring_breakdown: Optional[Dict] = None,
        candidates_evaluated: List[Any] = None,
        hard_rules: List[Any] = None,
        professor_prefs: Dict[str, List[int]] = None,
        historical_count: int = 0,
        conflicts: List[Dict] = None,
        decision_reason: str = "",
        skipped_reason: Optional[str] = None,
    ):
        """Log a detailed allocation decision."""

        # Prepare top 3 candidates for logging
        top_candidates = []
        if candidates_evaluated:
            for i, candidate in enumerate(candidates_evaluated[:3]):
                if hasattr(candidate, "sala"):
                    top_candidates.append(
                        {
                            "rank": i + 1,
                            "room_id": candidate.sala.id,
                            "room_name": candidate.sala.nome,
                            "score": getattr(candidate, "score", 0),
                            "has_conflicts": getattr(candidate, "has_conflicts", False),
                        }
                    )

        # Process hard rules
        hard_rules_found = []
        hard_rules_satisfied = []
        if hard_rules:
            for rule in hard_rules:
                rule_desc = f"{rule.tipo_regra}: {rule.descricao}"
                hard_rules_found.append(rule_desc)
                # Note: We'd need to check satisfaction separately

        # Process professor preferences
        prof_prefs = []
        prof_prefs_satisfied = []
        if professor_prefs:
            if professor_prefs.get("preferred_rooms"):
                prof_prefs.append(
                    f"Preferred rooms: {len(professor_prefs['preferred_rooms'])}"
                )
            if professor_prefs.get("preferred_characteristics"):
                prof_prefs.append(
                    f"Preferred characteristics: {len(professor_prefs['preferred_characteristics'])}"
                )

        # Process conflicts
        conflict_details = []
        if conflicts:
            for conflict in conflicts:
                conflict_details.append(
                    f"Day {conflict.get('dia_sigaa')}, Block {conflict.get('codigo_bloco')}"
                )

        # Create decision record
        decision = AllocationDecision(
            timestamp=datetime.now().isoformat(),
            semester_id=semester_id,
            demanda_id=getattr(demanda, "id", 0),
            disciplina_codigo=getattr(demanda, "codigo_disciplina", ""),
            disciplina_nome=getattr(demanda, "nome_disciplina", ""),
            turma=getattr(demanda, "turma_disciplina", ""),
            vagas=getattr(demanda, "vagas_disciplina", 0),
            professores=getattr(demanda, "professores_disciplina", ""),
            allocated=allocated,
            allocated_room_id=(
                getattr(allocated_room, "id", None) if allocated_room else None
            ),
            allocated_room_name=(
                getattr(allocated_room, "nome", None) if allocated_room else None
            ),
            allocation_phase=phase,
            final_score=final_score,
            scoring_breakdown=scoring_breakdown,
            total_candidates_evaluated=(
                len(candidates_evaluated) if candidates_evaluated else 0
            ),
            top_3_candidates=top_candidates,
            hard_rules_found=hard_rules_found,
            hard_rules_satisfied=hard_rules_satisfied,
            professor_preferences=prof_prefs,
            professor_preferences_satisfied=prof_prefs_satisfied,
            historical_allocations_count=historical_count,
            historical_frequency_bonus=historical_count,  # 1 point per allocation
            conflicts_detected=len(conflicts) if conflicts else 0,
            conflict_details=conflict_details,
            decision_reason=decision_reason,
            skipped_reason=skipped_reason,
        )

        self.decisions.append(decision)

        # Only log to file if DEBUG mode is enabled
        if DEBUG_MODE:
            log_message = {"event": "allocation_decision", "decision": asdict(decision)}

            if allocated:
                allocation_logger.info(
                    f"ALLOCATED: {json.dumps(log_message, indent=2, default=str)}"
                )
            else:
                allocation_logger.warning(
                    f"SKIPPED: {json.dumps(log_message, indent=2, default=str)}"
                )

    def log_phase_summary(self, phase: str, stats: Dict[str, Any]):
        """Log summary statistics for a phase."""
        # Only log to file if DEBUG mode is enabled
        if DEBUG_MODE:
            summary_message = {
                "event": "phase_summary",
                "phase": phase,
                "timestamp": datetime.now().isoformat(),
                "statistics": stats,
            }
            allocation_logger.info(
                f"PHASE_SUMMARY: {json.dumps(summary_message, indent=2, default=str)}"
            )

    def log_session_summary(self, total_stats: Dict[str, Any]):
        """Log final session summary."""
        # Only log to file if DEBUG mode is enabled
        if DEBUG_MODE:
            summary_message = {
                "event": "session_summary",
                "session_start": self.session_start,
                "session_end": datetime.now().isoformat(),
                "total_decisions": len(self.decisions),
                "statistics": total_stats,
            }
            allocation_logger.info(
                f"SESSION_SUMMARY: {json.dumps(summary_message, indent=2, default=str)}"
            )

    def get_all_decisions(self) -> List[Dict[str, Any]]:
        """Get all allocation decisions for PDF report generation."""
        return [asdict(decision) for decision in self.decisions]

    def get_allocation_report(self, disciplina_codigo: str = None) -> Dict[str, Any]:
        """Generate a detailed report for a specific discipline or all decisions."""
        decisions_to_analyze = self.decisions
        if disciplina_codigo:
            decisions_to_analyze = [
                d for d in self.decisions if d.disciplina_codigo == disciplina_codigo
            ]

        if not decisions_to_analyze:
            return {"error": "No decisions found for the specified criteria"}

        # Analyze decisions
        allocated_count = sum(1 for d in decisions_to_analyze if d.allocated)
        skipped_count = len(decisions_to_analyze) - allocated_count

        # Score analysis
        scores = [
            d.final_score for d in decisions_to_analyze if d.final_score is not None
        ]
        avg_score = sum(scores) / len(scores) if scores else 0

        # Phase analysis
        phase_distribution = {}
        for decision in decisions_to_analyze:
            phase = decision.allocation_phase
            phase_distribution[phase] = phase_distribution.get(phase, 0) + 1

        # Top rooms used
        allocated_rooms = [
            d.allocated_room_name
            for d in decisions_to_analyze
            if d.allocated and d.allocated_room_name
        ]
        room_usage = {}
        for room in allocated_rooms:
            room_usage[room] = room_usage.get(room, 0) + 1

        return {
            "discipline_filter": disciplina_codigo or "All",
            "total_decisions": len(decisions_to_analyze),
            "allocated_count": allocated_count,
            "skipped_count": skipped_count,
            "success_rate": (allocated_count / len(decisions_to_analyze)) * 100,
            "average_score": round(avg_score, 2),
            "score_range": {
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
            },
            "phase_distribution": phase_distribution,
            "most_used_rooms": sorted(
                room_usage.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "decisions": [
                asdict(d) for d in decisions_to_analyze[-10:]
            ],  # Last 10 decisions
        }

    def get_hybrid_summary(self) -> Dict[str, Any]:
        """Get hybrid discipline detection summary for PDF reports.

        Returns cached Phase 0 hybrid detection data including:
        - detected_count: Number of hybrid disciplines found
        - detection_semester_id: Which semester was analyzed
        - hybrid_disciplines: List of discipline codes
        - details: Per-discipline breakdown with lab/classroom days
        """
        return self.hybrid_data

    # =========================================================================
    # PHASE 0: HYBRID DETECTION LOGGING
    # =========================================================================

    def log_hybrid_detection_phase(
        self,
        detection_semester_id: int,
        current_semester_id: int,
        hybrid_disciplines: list,
        detection_details: dict,
    ):
        """Log detailed Phase 0 hybrid detection results."""
        # ALWAYS cache hybrid data for PDF reports (even in production)
        self.hybrid_data["detected_count"] = len(hybrid_disciplines)
        self.hybrid_data["detection_semester_id"] = detection_semester_id
        self.hybrid_data["hybrid_disciplines"] = hybrid_disciplines

        # Build details dict for PDF report
        for codigo, info in detection_details.items():
            day_names = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}
            lab_days = info.lab_days if hasattr(info, "lab_days") else []
            classroom_days = (
                info.classroom_days if hasattr(info, "classroom_days") else []
            )

            self.hybrid_data["details"][codigo] = {
                "lab_days": lab_days,
                "lab_days_names": [day_names.get(d, str(d)) for d in lab_days],
                "classroom_days": classroom_days,
                "classroom_days_names": [
                    day_names.get(d, str(d)) for d in classroom_days
                ],
                "lab_room_types": (
                    list(info.lab_room_types) if hasattr(info, "lab_room_types") else []
                ),
                "historical_lab_rooms": (
                    info.historical_lab_rooms
                    if hasattr(info, "historical_lab_rooms")
                    else {}
                ),
            }

        # Only log to file if DEBUG mode is enabled
        if not DEBUG_MODE:
            return

        log_message = {
            "event": "phase0_hybrid_detection",
            "timestamp": datetime.now().isoformat(),
            "detection_semester_id": detection_semester_id,
            "current_semester_id": current_semester_id,
            "total_hybrid_detected": len(hybrid_disciplines),
            "hybrid_discipline_codes": hybrid_disciplines,
            "details": self.hybrid_data["details"],
        }

        allocation_logger.info(
            f"HYBRID_DETECTION_PHASE: {json.dumps(log_message, indent=2, default=str)}"
        )

    def log_hybrid_discipline_detail(
        self,
        codigo_disciplina: str,
        lab_days: list,
        classroom_days: list,
        lab_room_ids: dict,
    ):
        """Log detailed info for a single hybrid discipline."""
        if not DEBUG_MODE:
            return

        log_message = {
            "event": "hybrid_discipline_detected",
            "timestamp": datetime.now().isoformat(),
            "codigo_disciplina": codigo_disciplina,
            "lab_days": lab_days,
            "classroom_days": classroom_days,
            "lab_room_ids_by_day": lab_room_ids,
            "day_names": {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"},
        }

        allocation_logger.info(
            f"HYBRID_DISCIPLINE: {json.dumps(log_message, indent=2, default=str)}"
        )

    def log_hybrid_scoring_applied(
        self,
        demanda_id: int,
        codigo_disciplina: str,
        day_id: int,
        room_id: int,
        room_name: str,
        room_type_id: int,
        is_hybrid: bool,
        is_lab_day: bool,
        is_lab_room: bool,
        hybrid_bonus_applied: int,
        final_score: int,
    ):
        """Log when hybrid bonus is applied or not applied during scoring."""
        if not DEBUG_MODE:
            return

        day_names = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}

        log_message = {
            "event": "hybrid_scoring",
            "timestamp": datetime.now().isoformat(),
            "demanda_id": demanda_id,
            "codigo_disciplina": codigo_disciplina,
            "day_id": day_id,
            "day_name": day_names.get(day_id, str(day_id)),
            "room_id": room_id,
            "room_name": room_name,
            "room_type_id": room_type_id,
            "is_hybrid_discipline": is_hybrid,
            "is_lab_day": is_lab_day,
            "is_lab_room": is_lab_room,
            "hybrid_bonus_applied": hybrid_bonus_applied,
            "final_score": final_score,
            "decision": "BONUS_APPLIED" if hybrid_bonus_applied > 0 else "NO_BONUS",
        }

        if is_hybrid:
            allocation_logger.info(
                f"HYBRID_SCORING: {json.dumps(log_message, indent=2, default=str)}"
            )

    def log_no_hybrid_disciplines_found(
        self, detection_semester_id: int, reason: str = ""
    ):
        """Log when no hybrid disciplines are found."""
        if not DEBUG_MODE:
            return

        log_message = {
            "event": "no_hybrid_disciplines",
            "timestamp": datetime.now().isoformat(),
            "detection_semester_id": detection_semester_id,
            "reason": reason
            or "No disciplines found with 2+ rooms including non-classroom",
        }

        allocation_logger.warning(
            f"NO_HYBRID_DISCIPLINES: {json.dumps(log_message, indent=2, default=str)}"
        )
