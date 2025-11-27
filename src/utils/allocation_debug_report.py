"""
Comprehensive Allocation Debug Report Generator

Generates detailed human-readable logs for autonomous allocation pipeline debugging.
Provides complete visibility into scoring decisions, block allocations, and algorithm choices.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BlockScore:
    """Detailed scoring breakdown for a single block."""
    block_code: str
    day_id: int
    day_name: str
    room_id: int
    room_name: str
    room_capacity: int
    room_type: str
    building: str

    # Score components
    capacity_score: int = 0
    hard_rule_score: int = 0
    soft_preference_score: int = 0
    historical_score: int = 0
    professor_room_pref_score: int = 0
    professor_char_pref_score: int = 0
    total_score: int = 0

    # Details
    capacity_adequate: bool = False
    hard_rules_matched: List[str] = field(default_factory=list)
    soft_rules_matched: List[str] = field(default_factory=list)
    historical_allocations: int = 0
    has_conflict: bool = False
    conflict_with: Optional[str] = None  # "discipline_code (turma)"


@dataclass
class DemandAllocationDecision:
    """Complete allocation decision record for a demand."""
    demanda_id: int
    codigo_disciplina: str
    nome_disciplina: str
    turma: str
    professores: str
    vagas: int
    horario_sigaa: str

    # Block groups
    block_groups: List[Dict[str, Any]] = field(default_factory=list)

    # Phase info
    phase: str = ""  # "hard_rules", "soft_scoring", "atomic_allocation", "partial"

    # Decision
    allocated: bool = False
    allocated_rooms: List[Dict[str, Any]] = field(default_factory=list)

    # Candidate analysis
    candidates_evaluated: int = 0
    top_candidates: List[Dict[str, Any]] = field(default_factory=list)

    # Rules
    hard_rules: List[str] = field(default_factory=list)
    soft_rules: List[str] = field(default_factory=list)
    professor_preferences: Dict[str, Any] = field(default_factory=dict)

    # Reasoning
    decision_reason: str = ""
    skip_reason: Optional[str] = None


class AllocationDebugReport:
    """
    Generates comprehensive debug reports for autonomous allocation.

    Outputs a detailed, human-readable log file showing:
    - All demands processed with full details
    - Per-block scoring breakdown for every room candidate
    - Why each room was chosen or rejected
    - Conflict information
    - Hard/soft rule compliance
    - Historical frequency bonuses
    - Final allocation decisions with reasoning
    """

    def __init__(self, output_dir: str = "logs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_file = self.output_dir / f"allocation_debug_{self.session_id}.log"

        # Tracking
        self.demands_processed: List[DemandAllocationDecision] = []
        self.phase_stats: Dict[str, Dict[str, int]] = {}
        self.start_time = datetime.now()

        # Scoring config reference
        self.scoring_weights = self._load_scoring_config()

        # Initialize report file
        self._init_report()

    def _load_scoring_config(self) -> Dict[str, Any]:
        """Load scoring configuration for reference."""
        try:
            from src.config.scoring_config import SCORING_WEIGHTS
            return {
                "CAPACITY_ADEQUATE": SCORING_WEIGHTS.CAPACITY_ADEQUATE,
                "HARD_RULE_COMPLIANCE": SCORING_WEIGHTS.HARD_RULE_COMPLIANCE,
                "PREFERRED_ROOM": SCORING_WEIGHTS.PREFERRED_ROOM,
                "PREFERRED_CHARACTERISTIC": SCORING_WEIGHTS.PREFERRED_CHARACTERISTIC,
                "HISTORICAL_FREQUENCY_PER_ALLOCATION": SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION,
                "HISTORICAL_FREQUENCY_MAX_CAP": SCORING_WEIGHTS.HISTORICAL_FREQUENCY_MAX_CAP,
            }
        except Exception:
            return {
                "CAPACITY_ADEQUATE": 3,
                "HARD_RULE_COMPLIANCE": 20,
                "PREFERRED_ROOM": 4,
                "PREFERRED_CHARACTERISTIC": 4,
                "HISTORICAL_FREQUENCY_PER_ALLOCATION": 2,
                "HISTORICAL_FREQUENCY_MAX_CAP": 20,
            }

    def _init_report(self):
        """Initialize the report file with header."""
        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("AUTONOMOUS ALLOCATION DEBUG REPORT\n")
            f.write("=" * 100 + "\n")
            f.write(f"Session ID: {self.session_id}\n")
            f.write(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 100 + "\n\n")

            # Scoring configuration reference
            f.write("SCORING CONFIGURATION:\n")
            f.write("-" * 50 + "\n")
            for key, value in self.scoring_weights.items():
                f.write(f"  {key}: {value} points\n")
            f.write("\n")
            f.write("SCORING FORMULA:\n")
            f.write("  Total = Capacity + HardRules + SoftPreferences + Historical + ProfPrefs\n")
            f.write("  - Capacity: +3 if room fits demand\n")
            f.write("  - HardRules: +20 per satisfied hard rule\n")
            f.write("  - Historical: +2 per past allocation (max 20)\n")
            f.write("  - ProfRoom: +4 if professor prefers this room\n")
            f.write("  - ProfChar: +4 per matching characteristic\n")
            f.write("-" * 100 + "\n\n")

    def _write(self, text: str):
        """Append text to report file."""
        with open(self.report_file, 'a', encoding='utf-8') as f:
            f.write(text)

    def log_phase_start(self, phase: str, description: str):
        """Log the start of a phase."""
        self._write("\n" + "=" * 100 + "\n")
        self._write(f"PHASE: {phase.upper()}\n")
        self._write(f"Description: {description}\n")
        self._write(f"Time: {datetime.now().strftime('%H:%M:%S')}\n")
        self._write("=" * 100 + "\n\n")

        self.phase_stats[phase] = {
            "demands_processed": 0,
            "allocations_made": 0,
            "conflicts_found": 0,
            "skipped": 0,
        }

    def log_demand_start(
        self,
        demanda_id: int,
        codigo: str,
        nome: str,
        turma: str,
        professores: str,
        vagas: int,
        horario_sigaa: str,
        block_groups: List[Dict[str, Any]],
    ):
        """Log start of processing a demand."""
        self._write("-" * 80 + "\n")
        self._write(f"DEMAND #{demanda_id}: {codigo} - {nome} (T{turma})\n")
        self._write("-" * 80 + "\n")
        self._write(f"  Professor(es): {professores}\n")
        self._write(f"  Vagas: {vagas}\n")
        self._write(f"  Horário SIGAA: {horario_sigaa}\n")
        self._write("  Block Groups:\n")

        for bg in block_groups:
            day_name = bg.get('day_name', f"Day{bg.get('day_id', '?')}")
            blocks = bg.get('blocks', [])
            self._write(f"    • {day_name}: {', '.join(blocks)}\n")

        self._write("\n")

    def log_hard_rules(self, rules: List[Dict[str, Any]]):
        """Log hard rules applicable to the demand."""
        if rules:
            self._write("  HARD RULES (must satisfy):\n")
            for rule in rules:
                tipo = rule.get('tipo_regra', 'UNKNOWN')
                desc = rule.get('descricao', 'No description')
                self._write(f"    🔒 [{tipo}] {desc}\n")
        else:
            self._write("  HARD RULES: None\n")
        self._write("\n")

    def log_soft_rules(self, rules: List[Dict[str, Any]]):
        """Log soft rules/preferences."""
        if rules:
            self._write("  SOFT PREFERENCES:\n")
            for rule in rules:
                tipo = rule.get('tipo_regra', 'UNKNOWN')
                desc = rule.get('descricao', 'No description')
                prio = rule.get('prioridade', 1)
                self._write(f"    ⭐ [{tipo}] P{prio}: {desc}\n")
        else:
            self._write("  SOFT PREFERENCES: None\n")
        self._write("\n")

    def log_professor_preferences(self, prefs: Dict[str, Any]):
        """Log professor preferences."""
        if prefs:
            self._write("  PROFESSOR PREFERENCES:\n")
            if prefs.get('preferred_rooms'):
                rooms = prefs['preferred_rooms']
                self._write(f"    🏢 Preferred Rooms: {rooms}\n")
            if prefs.get('preferred_characteristics'):
                chars = prefs['preferred_characteristics']
                self._write(f"    ✨ Preferred Characteristics: {chars}\n")
        else:
            self._write("  PROFESSOR PREFERENCES: None\n")
        self._write("\n")

    def log_block_group_scoring(
        self,
        day_id: int,
        day_name: str,
        blocks: List[str],
        room_scores: List[Dict[str, Any]],
        max_rooms_to_show: int = 10,
    ):
        """Log detailed scoring for a block group (day)."""
        self._write(f"  SCORING FOR {day_name} ({', '.join(blocks)}):\n")
        self._write("  " + "-" * 70 + "\n")

        # Header
        self._write(f"  {'Rank':<5} {'Room':<20} {'Cap':<6} {'Score':<7} {'Breakdown':<40}\n")
        self._write("  " + "-" * 70 + "\n")

        for i, rs in enumerate(room_scores[:max_rooms_to_show], 1):
            room_name = rs.get('room_name', 'Unknown')[:18]
            capacity = rs.get('room_capacity', 0)
            total = rs.get('total_score', 0)

            # Build breakdown string
            breakdown_parts = []
            if rs.get('capacity_score', 0) > 0:
                breakdown_parts.append(f"Cap:{rs['capacity_score']}")
            if rs.get('hard_rule_score', 0) > 0:
                breakdown_parts.append(f"Hard:{rs['hard_rule_score']}")
            if rs.get('historical_score', 0) > 0:
                hist_allocs = rs.get('historical_allocations', 0)
                breakdown_parts.append(f"Hist:{rs['historical_score']}({hist_allocs}x)")
            if rs.get('professor_room_score', 0) > 0:
                breakdown_parts.append(f"PrfR:{rs['professor_room_score']}")
            if rs.get('professor_char_score', 0) > 0:
                breakdown_parts.append(f"PrfC:{rs['professor_char_score']}")

            breakdown = " + ".join(breakdown_parts) if breakdown_parts else "No bonus"

            # Conflict indicator
            conflict = "⚠️CONFLICT" if rs.get('has_conflict') else ""

            self._write(f"  {i:<5} {room_name:<20} {capacity:<6} {total:<7} {breakdown:<40} {conflict}\n")

        if len(room_scores) > max_rooms_to_show:
            self._write(f"  ... and {len(room_scores) - max_rooms_to_show} more rooms\n")

        self._write("\n")

    def log_full_room_scoring_detail(
        self,
        room_name: str,
        room_capacity: int,
        demand_vagas: int,
        scoring_breakdown: Dict[str, Any],
    ):
        """Log complete scoring detail for a specific room (verbose mode)."""
        self._write(f"    DETAILED SCORING FOR: {room_name} (Cap: {room_capacity})\n")
        self._write("    " + "~" * 50 + "\n")

        # Capacity check
        cap_ok = room_capacity >= demand_vagas
        cap_score = scoring_breakdown.get('capacity_score', 0)
        self._write(f"      Capacity Check: {room_capacity} >= {demand_vagas}? ")
        self._write(f"{'✓ YES' if cap_ok else '✗ NO'} → +{cap_score} pts\n")

        # Hard rules
        hard_rules = scoring_breakdown.get('hard_rules_satisfied', [])
        hard_score = scoring_breakdown.get('hard_rule_score', 0)
        self._write(f"      Hard Rules: {len(hard_rules)} satisfied → +{hard_score} pts\n")
        for rule in hard_rules:
            self._write(f"        • {rule}\n")

        # Historical
        hist_count = scoring_breakdown.get('historical_allocations', 0)
        hist_score = scoring_breakdown.get('historical_score', 0)
        self._write(f"      Historical: {hist_count} past allocations × 2 pts = ")
        self._write(f"{hist_count * 2} (capped at 20) → +{hist_score} pts\n")

        # Professor preferences
        prof_room = scoring_breakdown.get('professor_room_score', 0)
        prof_char = scoring_breakdown.get('professor_char_score', 0)
        self._write(f"      Professor Room Pref: +{prof_room} pts\n")
        self._write(f"      Professor Char Pref: +{prof_char} pts\n")

        # Total
        total = scoring_breakdown.get('total_score', 0)
        self._write("      ─────────────────────────────\n")
        self._write(f"      TOTAL SCORE: {total} pts\n")
        self._write("\n")

    def log_allocation_decision(
        self,
        day_name: str,
        blocks: List[str],
        chosen_room: str,
        score: int,
        reason: str,
    ):
        """Log the allocation decision for a block group."""
        self._write(f"  ✅ ALLOCATED: {day_name} ({', '.join(blocks)})\n")
        self._write(f"     → Room: {chosen_room}\n")
        self._write(f"     → Score: {score} pts\n")
        self._write(f"     → Reason: {reason}\n")
        self._write("\n")

    def log_allocation_skipped(
        self,
        day_name: str,
        blocks: List[str],
        reason: str,
        conflict_details: Optional[List[str]] = None,
    ):
        """Log when allocation is skipped."""
        self._write(f"  ❌ SKIPPED: {day_name} ({', '.join(blocks)})\n")
        self._write(f"     → Reason: {reason}\n")
        if conflict_details:
            for detail in conflict_details[:5]:
                self._write(f"       • {detail}\n")
        self._write("\n")

    def log_conflict_detected(
        self,
        room_name: str,
        day_id: int,
        block_code: str,
        conflicting_discipline: str,
        conflicting_turma: str,
    ):
        """Log a specific conflict."""
        self._write(f"      ⚠️ CONFLICT: {room_name} on Day{day_id}/{block_code} ")
        self._write(f"already has {conflicting_discipline} (T{conflicting_turma})\n")

    def log_demand_summary(
        self,
        demanda_id: int,
        allocated: bool,
        rooms_used: List[str],
        total_blocks: int,
        allocated_blocks: int,
        is_split: bool,
    ):
        """Log summary for a demand."""
        status = "ALLOCATED" if allocated else "NOT ALLOCATED"
        self._write(f"  SUMMARY: {status}\n")

        if allocated:
            self._write(f"    Blocks: {allocated_blocks}/{total_blocks} allocated\n")
            if is_split:
                self._write(f"    🔀 SPLIT ALLOCATION across {len(rooms_used)} rooms:\n")
                for room in rooms_used:
                    self._write(f"       • {room}\n")
            else:
                self._write(f"    Single room: {rooms_used[0] if rooms_used else 'N/A'}\n")

        self._write("\n")

    def log_phase_end(self, phase: str, stats: Dict[str, int]):
        """Log end of phase with statistics."""
        self._write("\n" + "-" * 80 + "\n")
        self._write(f"PHASE {phase.upper()} COMPLETE\n")
        self._write("-" * 80 + "\n")
        self._write(f"  Demands Processed: {stats.get('demands_processed', 0)}\n")
        self._write(f"  Allocations Made: {stats.get('allocations_made', 0)}\n")
        self._write(f"  Conflicts Found: {stats.get('conflicts_found', 0)}\n")
        self._write(f"  Skipped: {stats.get('skipped', 0)}\n")
        self._write("-" * 80 + "\n\n")

        self.phase_stats[phase] = stats

    def log_final_summary(self, total_stats: Dict[str, Any]):
        """Log final report summary."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        self._write("\n" + "=" * 100 + "\n")
        self._write("FINAL SUMMARY\n")
        self._write("=" * 100 + "\n")
        self._write(f"Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self._write(f"Duration: {duration:.2f} seconds\n")
        self._write("\n")

        # Overall stats
        self._write("OVERALL STATISTICS:\n")
        self._write("-" * 50 + "\n")
        self._write(f"  Total Demands: {total_stats.get('total_demands', 0)}\n")
        self._write(f"  Fully Allocated: {total_stats.get('fully_allocated', 0)}\n")
        self._write(f"  Partially Allocated: {total_stats.get('partially_allocated', 0)}\n")
        self._write(f"  Not Allocated: {total_stats.get('not_allocated', 0)}\n")
        self._write(f"  Split Allocations: {total_stats.get('split_allocations', 0)}\n")
        self._write(f"  Total Conflicts: {total_stats.get('total_conflicts', 0)}\n")
        self._write("\n")

        # Per-phase breakdown
        self._write("PER-PHASE BREAKDOWN:\n")
        self._write("-" * 50 + "\n")
        for phase, stats in self.phase_stats.items():
            self._write(f"  {phase}:\n")
            for key, value in stats.items():
                self._write(f"    {key}: {value}\n")

        self._write("\n")
        self._write("=" * 100 + "\n")
        self._write(f"Report saved to: {self.report_file}\n")
        self._write("=" * 100 + "\n")

        logger.info(f"Allocation debug report saved to: {self.report_file}")

    def get_report_path(self) -> str:
        """Get the path to the generated report."""
        return str(self.report_file)


# Convenience function to create a debug reporter
def create_allocation_debug_report(output_dir: str = "logs") -> AllocationDebugReport:
    """Create a new allocation debug report instance."""
    return AllocationDebugReport(output_dir)
