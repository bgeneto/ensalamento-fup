"""
Autonomous Allocation Service - RF-006 Phase 1 Implementation

Core service for autonomous room allocation following the three-phase algorithm:
1. Hard Rules Allocation - prioritize most restrictive constraints
2. Soft Rules Scoring - combine preferences with historical frequency
3. Atomic Block Allocation - prevent conflicts using atomic scheduling

Implements RF-006 requirements:
- RF-006.2: Atomic block parsing
- RF-006.3: Professor lookup
- RF-006.4: Hard rules allocation
- RF-006.5: Soft rules scoring
- RF-006.6: Historical frequency bonus (NEW)
- RF-006.7: Atomic block allocation to database
"""

from typing import List, Dict, Tuple, Optional, Set, NamedTuple, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from datetime import datetime

from src.repositories.alocacao import AlocacaoRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.regra import RegraRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.sala import SalaRepository
from src.repositories.semestre import SemestreRepository
from src.utils.sigaa_parser import SigaaScheduleParser
from src.services.allocation_suggestions import AllocationSuggestionsService
from src.services.manual_allocation_service import ManualAllocationService
from src.services.room_scoring_service import RoomScoringService
from src.schemas.allocation import AlocacaoSemestralCreate
from src.models.inventory import Sala
from src.models.academic import Professor
from src.models.allocation import Regra
from src.config.settings import settings


logger = logging.getLogger(__name__)


@dataclass
class AllocationCandidate:
    """Internal structure for room-demand allocation candidates."""

    sala: Sala
    demanda_id: int
    score: int = 0
    hard_rules_compliant: bool = False
    professor_name: Optional[str] = None
    professor_id: Optional[int] = None
    atomic_blocks: List[Tuple[str, int]] = None
    conflicts_found: bool = False

    def __post_init__(self):
        if self.atomic_blocks is None:
            self.atomic_blocks = []


@dataclass
class PhaseResult:
    """Result of a single allocation phase."""

    allocations_completed: int = 0
    conflicts_found: int = 0
    demands_skipped: int = 0
    details: List[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = []


class DemandPriority(NamedTuple):
    """Priority ordering for demand allocation."""

    demanda_id: int
    priority_score: int  # Higher = allocate first
    hard_rules_count: int
    has_specific_room_constraint: bool
    has_professor_mobility: bool


class AutonomousAllocationService:
    """
    Core service implementing RF-006 autonomous allocation algorithm.

    Three-phase algorithm:
    1. Hard Rules Phase: Allocate demands with mandatory constraints
    2. Soft Scoring Phase: Score remaining demands with preferences + frequency
    3. Atomic Allocation Phase: Allocate highest-scored demands without conflicts
    """

    def __init__(self, session: Session):
        """Initialize with required repositories and services."""
        self.session = session
        self.parser = SigaaScheduleParser()
        self.suggestions_service = AllocationSuggestionsService(session)
        self.manual_service = ManualAllocationService(session)
        self.scoring_service = RoomScoringService(session)

        # Core repositories
        self.alocacao_repo = AlocacaoRepository(session)
        self.demanda_repo = DisciplinaRepository(session)
        self.regra_repo = RegraRepository(session)
        self.prof_repo = ProfessorRepository(session)
        self.sala_repo = SalaRepository(session)
        self.semestre_repo = SemestreRepository(session)

    def execute_autonomous_allocation(self, semester_id: int) -> Dict:
        """
        Execute the complete autonomous allocation algorithm for a semester.

        Returns summary of allocation results, conflicts, and next steps.

        Args:
            semester_id: The semester to allocate rooms for

        Returns:
            Dict with allocation results and statistics
        """
        import time

        start_time = time.time()

        logger.info(f"Starting autonomous allocation for semester {semester_id}")

        # Phase 0: Gather semester data
        semester = self.semestre_repo.get_by_id(semester_id)
        if not semester:
            return {
                "success": False,
                "error": f"Semestre {semester_id} não encontrado.",
            }

        unallocated_demands = self.manual_service.get_unallocated_demands(semester_id)
        if not unallocated_demands:
            return {"success": True, "message": "Todas as demandas já foram alocadas."}

        # Parse all demand schedules first (RF-006.2)
        parse_start = time.time()
        demand_blocks = self._parse_all_demand_schedules(unallocated_demands)
        parse_time = time.time() - parse_start

        # Phase 1: Hard Rules Allocation (RF-006.4)
        phase1_start = time.time()
        phase1_result = self._execute_hard_rules_phase(
            semester_id, unallocated_demands, demand_blocks
        )
        phase1_time = time.time() - phase1_start

        # Get remaining unallocated demands
        remaining_demands = self.manual_service.get_unallocated_demands(semester_id)

        # Phase 2: Soft Scoring Phase (RF-006.5 + RF-006.6)
        phase2_start = time.time()
        phase2_result, phase2_candidates = self._execute_soft_scoring_phase(
            semester_id, remaining_demands, demand_blocks
        )
        phase2_time = time.time() - phase2_start

        # Phase 3: Atomic Allocation Phase (RF-006.7)
        phase3_start = time.time()
        phase3_result = self._execute_atomic_allocation_phase(
            semester_id, remaining_demands, phase2_candidates
        )
        phase3_time = time.time() - phase3_start

        total_time = time.time() - start_time

        # Compile final results
        total_allocated = (
            phase1_result.allocations_completed + phase3_result.allocations_completed
        )
        total_conflicts = (
            phase1_result.conflicts_found
            + phase2_result.conflicts_found
            + phase3_result.conflicts_found
        )

        result = {
            "success": True,
            "semester_id": semester_id,
            "total_demands_processed": len(unallocated_demands),
            "allocations_completed": total_allocated,
            "conflicts_found": total_conflicts,
            "demands_skipped": phase1_result.demands_skipped
            + phase2_result.demands_skipped
            + phase3_result.demands_skipped,
            "phase1_hard_rules": {
                "allocations": phase1_result.allocations_completed,
                "conflicts": phase1_result.conflicts_found,
                "skipped": phase1_result.demands_skipped,
                "details": phase1_result.details[:10],  # Limit detail logs
            },
            "phase2_soft_scoring": {
                "candidates_scored": len(remaining_demands),
                "conflicts": phase2_result.conflicts_found,
                "skipped": phase2_result.demands_skipped,
                "details": phase2_result.details[:10],
            },
            "phase3_atomic_allocation": {
                "allocations": phase3_result.allocations_completed,
                "conflicts": phase3_result.conflicts_found,
                "skipped": phase3_result.demands_skipped,
                "details": phase3_result.details[:10],
            },
            "progress_percentage": (
                (total_allocated / len(unallocated_demands) * 100)
                if unallocated_demands
                else 100
            ),
            "next_steps": "Phase 2: Manual fine-tuning of autonomous results",
            "performance": {
                "total_execution_time": round(total_time, 2),
                "phase1_time": round(phase1_time, 2),
                "phase2_time": round(phase2_time, 2),
                "phase3_time": round(phase3_time, 2),
                "schedule_parsing_time": round(parse_time, 2),
                "allocations_per_second": (
                    round(total_allocated / total_time, 2) if total_time > 0 else 0
                ),
            },
        }

        logger.info(
            f"Autonomous allocation complete for semester {semester_id}: {total_allocated} allocations, {total_conflicts} conflicts in {total_time:.2f}s"
        )

        # Write detailed debug log if enabled
        if settings.DEBUG:
            self._write_detailed_allocation_log(
                semester_id,
                unallocated_demands,
                phase1_result,
                phase2_result,
                phase3_result,
                result,
            )

        return result

    def _parse_all_demand_schedules(
        self, demands: List[Any]
    ) -> Dict[int, List[Tuple[str, int]]]:
        """
        Parse all demand schedules into atomic blocks (RF-006.2).

        Args:
            demands: List of DemandaRead objects (Pydantic DTOs)

        Returns:
            Dict[demanda_id, List[Tuple[bloco_codigo, dia_sigaa]]]
        """
        demand_blocks = {}

        for demanda in demands:
            demanda_id = demanda.id
            try:
                atomic_blocks = self.parser.split_to_atomic_tuples(
                    demanda.horario_sigaa_bruto
                )
                demand_blocks[demanda_id] = atomic_blocks
                logger.debug(
                    f"Parsed {len(atomic_blocks)} blocks for demand {demanda_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to parse schedule for demand {demanda_id}: {e}")
                demand_blocks[demanda_id] = []

        return demand_blocks

    def _execute_hard_rules_phase(
        self,
        semester_id: int,
        demands: List[Any],
        demand_blocks: Dict[int, List[Tuple[str, int]]],
    ) -> PhaseResult:
        """
        Phase 1: Allocate demands with hard rules constraints (RF-006.4).

        Args:
            demands: List of DemandaRead objects (Pydantic DTOs)

        Prioritizes demands by restrictiveness, allocates those that MUST go to specific rooms/types.
        """
        result = PhaseResult()
        logger.info("Executing hard rules allocation phase")

        # Get priority ordering for hard rules allocation
        prioritized_demands = self._prioritize_demands_for_hard_rules(demands)

        # Create lookup dict for demands by ID
        demanda_lookup = {d.id: d for d in demands}

        for priority_item in prioritized_demands:
            demanda_id = priority_item.demanda_id
            demanda = demanda_lookup.get(demanda_id)

            if not demanda:
                continue

            # Find hard rules for this demand
            hard_rules = self.regra_repo.find_rules_by_disciplina(
                demanda.codigo_disciplina
            )
            hard_rules = [
                rule for rule in hard_rules if rule.prioridade == 0
            ]  # Only hard rules

            if not hard_rules:
                continue  # No hard rules, skip in this phase

            # Find rooms that satisfy ALL hard rules
            # Convert Pydantic object to dict for compatibility with existing methods
            demanda_dict = demanda.model_dump()
            compatible_rooms = self._find_hard_rules_compatible_rooms(
                demanda_dict, hard_rules
            )

            if not compatible_rooms:
                result.demands_skipped += 1
                result.details.append(
                    f"Demand {demanda_id}: No rooms satisfy hard rules"
                )
                continue

            # Try to allocate to first available room
            allocation_success = False
            failed_room_details = []  # Track room-specific failure details

            for room in compatible_rooms:
                candidate = AllocationCandidate(
                    sala=room,
                    demanda_id=demanda_id,
                    atomic_blocks=demand_blocks.get(demanda_id, []),
                    hard_rules_compliant=True,
                )

                # Check for conflicts
                conflicts = self._check_allocation_conflicts(candidate, semester_id)

                if not conflicts:
                    # Allocate
                    success = self._allocate_atomic_blocks(candidate, semester_id)
                    if success:
                        result.allocations_completed += 1
                        result.details.append(
                            f"Demand {demanda_id}: Hard rules allocated to {room.nome}"
                        )
                        allocation_success = True
                        break
                else:
                    result.conflicts_found += len(conflicts)
                    # Capture specific conflict details
                    conflict_details = [
                        f"Dia {c['dia_sigaa']}, Bloco {c['codigo_bloco']}"
                        for c in conflicts
                    ]
                    room_conflict_detail = (
                        f"Room {room.nome}: conflicts at {', '.join(conflict_details)}"
                    )
                    failed_room_details.append(room_conflict_detail)

            if not allocation_success:
                result.demands_skipped += 1
                if failed_room_details:
                    conflict_summary = "; ".join(failed_room_details)
                    result.details.append(
                        f"Demand {demanda_id}: Hard rules allocation failed - {conflict_summary}"
                    )
                else:
                    result.details.append(
                        f"Demand {demanda_id}: Hard rules allocation failed (conflicts)"
                    )

        return result

    def _execute_soft_scoring_phase(
        self,
        semester_id: int,
        demands: List[Any],
        demand_blocks: Dict[int, List[Tuple[str, int]]],
    ) -> Tuple[PhaseResult, Dict[int, List[AllocationCandidate]]]:
        """
        Phase 2: Score remaining demands with soft preferences and historical frequency (RF-006.5 + RF-006.6).

        Args:
            demands: List of DemandaRead objects (Pydantic DTOs)

        Returns:
            Tuple of (PhaseResult, Dict[demanda_id, List[AllocationCandidate]] with valid candidates)

        Creates candidate scoring for all demand-room combinations.
        """
        result = PhaseResult()
        phase2_candidates = {}  # Store valid candidates for Phase 3
        logger.info("Executing soft scoring allocation phase")

        # Professor lookup for all demands (RF-006.3)
        professor_map = self._lookup_professors_for_demands_from_objects(demands)

        for demanda in demands:
            demanda_id = demanda.id

            # Use the shared scoring service
            candidates = self.scoring_service.score_room_candidates_for_demand(
                demanda_id,
                semester_id,
                professor_override=professor_map.get(demanda_id),
            )

            # Filter out candidates with conflicts (already done by service, but keep for compatibility)
            valid_candidates = [c for c in candidates if not c.has_conflicts]

            # Count conflicts detected during scoring
            result.conflicts_found += len(candidates) - len(valid_candidates)

            if valid_candidates:
                # Convert RoomCandidates to AllocationCandidates for compatibility
                allocation_candidates = []
                for candidate in valid_candidates:
                    alloc_candidate = AllocationCandidate(
                        sala=candidate.sala,
                        demanda_id=demanda_id,
                        score=candidate.score,
                        professor_name=demanda.professores_disciplina,
                        professor_id=(
                            professor_map.get(demanda_id).id
                            if professor_map.get(demanda_id)
                            else None
                        ),
                    )
                    # Add atomic blocks (parse from schedule)
                    alloc_candidate.atomic_blocks = self.parser.split_to_atomic_tuples(
                        demanda.horario_sigaa_bruto
                    )
                    allocation_candidates.append(alloc_candidate)

                phase2_candidates[demanda_id] = allocation_candidates

                # Log top candidate for debugging
                top_candidate = allocation_candidates[0]
                result.details.append(
                    f"Demand {demanda_id}: Top score {top_candidate.score} for room {top_candidate.sala.nome}"
                )
            else:
                result.demands_skipped += 1
                result.details.append(
                    f"Demand {demanda_id}: No conflict-free room candidates"
                )

        return result, phase2_candidates

    def _execute_atomic_allocation_phase(
        self,
        semester_id: int,
        demands: List[Any],
        phase2_candidates: Optional[Dict[int, List[AllocationCandidate]]] = None,
    ) -> PhaseResult:
        """
        Phase 3: Allocate highest-scored demands using atomic block allocation (RF-006.7).

        Args:
            demands: List of DemandaRead objects (Pydantic DTOs)
            phase2_candidates: Optional candidates from Phase 2 (semester-filtered and scored)

        Iterative allocation of top-scored candidates without creating conflicts.
        """
        result = PhaseResult()
        logger.info("Executing atomic allocation phase")

        # Get remaining unallocated demands
        remaining = self.manual_service.get_unallocated_demands(semester_id)
        if not remaining:
            return result

        # Create lookup dict for remaining demands by ID
        remaining_ids = {d.id: d for d in remaining}

        for demanda in demands:
            demanda_id = demanda.id
            if demanda_id not in remaining_ids:
                continue  # Already allocated

            # Try to use Phase 2 candidates if available (preferred approach)
            if phase2_candidates and demanda_id in phase2_candidates:
                valid_candidates = phase2_candidates[demanda_id]
                # Sort by score descending
                valid_candidates.sort(key=lambda c: c.score, reverse=True)

                # Try top candidates first
                allocation_success = False
                for candidate in valid_candidates:
                    # Double-check for conflicts (room availability could have changed)
                    conflicts = self._check_allocation_conflicts(candidate, semester_id)
                    if not conflicts:
                        success = self._allocate_atomic_blocks(candidate, semester_id)
                        if success:
                            result.allocations_completed += 1
                            result.details.append(
                                f"Demand {demanda_id}: Atomic allocated to room {candidate.sala.nome} (score: {candidate.score})"
                            )
                            allocation_success = True
                            break
                    else:
                        result.conflicts_found += len(conflicts)

                if not allocation_success:
                    result.demands_skipped += 1
                    result.details.append(
                        f"Demand {demanda_id}: No conflict-free candidates available from Phase 2"
                    )

            else:
                # Fallback: Use suggestion service (with semester isolation fix)
                try:
                    # Get demand object
                    demanda_obj = remaining_ids[demanda_id]

                    # Calculate candidates directly (similar to Phase 2) with semester isolation
                    professor = self._lookup_professors_for_demands_from_objects(
                        [demanda_obj]
                    ).get(demanda_id)
                    candidates = self._score_room_candidates_for_demand(
                        demanda_obj, professor, semester_id
                    )

                    # Filter out candidates with conflicts in current semester
                    valid_candidates = []
                    for candidate in candidates:
                        conflicts = self._check_allocation_conflicts(
                            candidate, semester_id
                        )
                        if not conflicts:
                            valid_candidates.append(candidate)

                    if valid_candidates:
                        # Sort by score and try top candidates
                        valid_candidates.sort(key=lambda c: c.score, reverse=True)

                        allocation_success = False
                        for candidate in valid_candidates[:3]:  # Try top 3
                            success = self._allocate_atomic_blocks(
                                candidate, semester_id
                            )
                            if success:
                                result.allocations_completed += 1
                                result.details.append(
                                    f"Demand {demanda_id}: Atomic allocated to room {candidate.sala.nome} (score: {candidate.score})"
                                )
                                allocation_success = True
                                break

                        if not allocation_success:
                            result.demands_skipped += 1
                            result.details.append(
                                f"Demand {demanda_id}: Top candidates failed allocation (conflicts)"
                            )
                    else:
                        result.demands_skipped += 1
                        result.details.append(
                            f"Demand {demanda_id}: No conflict-free candidates available"
                        )

                except Exception as e:
                    logger.error(f"Error allocating demand {demanda_id}: {e}")
                    result.demands_skipped += 1

        return result

    def _prioritize_demands_for_hard_rules(
        self, demands: List[Any]
    ) -> List[DemandPriority]:
        """
        Prioritize demands for hard rules allocation based on restrictiveness.

        Args:
            demands: List of DemandaRead objects (Pydantic DTOs)

        Higher priority = more restrictive constraints = allocate first.
        """
        priorities = []

        for demanda in demands:
            demanda_id = demanda.id
            hard_rules = self.regra_repo.find_rules_by_disciplina(
                demanda.codigo_disciplina
            )
            hard_rules = [r for r in hard_rules if r.prioridade == 0]

            # Calculate priority score
            hard_rules_count = len(hard_rules)
            has_specific_room = any(
                r.tipo_regra == "DISCIPLINA_SALA" for r in hard_rules
            )
            has_professor = bool(demanda.professores_disciplina.strip())

            # Priority scoring: specific room constraints get highest priority
            priority_score = hard_rules_count * 10
            if has_specific_room:
                priority_score += 50  # Must allocate specific rooms first
            if has_professor:
                # Check if professor has mobility constraints
                prof_name = demanda.professores_disciplina.strip()
                professor = self.prof_repo.get_by_nome_completo(prof_name)
                if professor and not professor.tem_baixa_mobilidade:
                    priority_score += 5  # Professors with mobility constraints

            priorities.append(
                DemandPriority(
                    demanda_id=demanda_id,
                    priority_score=priority_score,
                    hard_rules_count=hard_rules_count,
                    has_specific_room_constraint=has_specific_room,
                    has_professor_mobility=has_professor,
                )
            )

        # Sort by priority score descending (highest first)
        priorities.sort(key=lambda p: p.priority_score, reverse=True)
        return priorities

    def _find_hard_rules_compatible_rooms(
        self, demanda: Dict, hard_rules: List[Regra]
    ) -> List[Sala]:
        """
        Find rooms that satisfy ALL hard rules for a demand.
        """
        all_rooms = self.sala_repo.get_all()
        compatible_rooms = []

        for room in all_rooms:
            # Check if room satisfies ALL hard rules
            all_satisfied = True
            for rule in hard_rules:
                if not self.suggestions_service._check_rule_compliance(
                    room, demanda, rule
                ):
                    all_satisfied = False
                    break

            if all_satisfied:
                compatible_rooms.append(room)

        return compatible_rooms

    def _lookup_professors_for_demands(
        self, demands: List[Dict]
    ) -> Dict[int, Optional[Professor]]:
        """
        Lookup professors for demands (RF-006.3).

        Returns Dict[demanda_id, Professor] for successful lookups.
        """
        professor_map = {}

        for demanda in demands:
            demanda_id = demanda["id"]
            prof_text = demanda.get("professores_disciplina", "").strip()

            if prof_text:
                # Support multiple professors (take first match)
                prof_names = [name.strip() for name in prof_text.split(",")]
                professor = None

                for prof_name in prof_names:
                    professor = self.prof_repo.get_by_nome_completo(prof_name)
                    if professor:
                        break

                professor_map[demanda_id] = professor

        return professor_map

    def _lookup_professors_for_demands_from_objects(
        self, demands: List[Any]
    ) -> Dict[int, Optional[Professor]]:
        """
        Lookup professors for demands from Pydantic objects (RF-006.3).

        Args:
            demands: List of DemandaRead objects (Pydantic DTOs)

        Returns:
            Dict[demanda_id, Professor] for successful lookups.
        """
        professor_map = {}

        for demanda in demands:
            demanda_id = demanda.id
            prof_text = demanda.professores_disciplina.strip()

            if prof_text:
                # Support multiple professors (take first match)
                prof_names = [name.strip() for name in prof_text.split(",")]
                professor = None

                for prof_name in prof_names:
                    professor = self.prof_repo.get_by_nome_completo(prof_name)
                    if professor:
                        break

                professor_map[demanda_id] = professor

        return professor_map

    def _score_room_candidates_for_demand(
        self, demanda: Any, professor: Optional[Professor], semester_id: int
    ) -> List[AllocationCandidate]:
        """
        Score all possible room candidates for a demand (RF-006.5 + RF-006.6).

        Args:
            demanda: DemandaRead Pydantic object

        Includes historical frequency bonus for discipline-room pairs.
        """
        candidates = []
        demanda_id = demanda.id

        # Get professor preferences (match expectation of _calculate_compatibility_score)
        professor_prefs = self._get_professor_preferences_for_professor(professor)

        # Get all rooms
        all_rooms = self.sala_repo.get_all()

        for room in all_rooms:
            candidate = AllocationCandidate(
                sala=room,
                demanda_id=demanda_id,
                professor_name=demanda.professores_disciplina,
                professor_id=professor.id if professor else None,
            )

            # Parse atomic blocks
            candidate.atomic_blocks = self.parser.split_to_atomic_tuples(
                demanda.horario_sigaa_bruto
            )

            # Calculate base score using existing suggestion service
            score_calc = self.suggestions_service._calculate_compatibility_score(
                room, demanda, [], professor_prefs  # No hard rules, pass prefs dict
            )

            candidate.score = score_calc.total_score

            # Add historical frequency bonus (RF-006.6)
            frequency_bonus = self._calculate_historical_frequency_bonus(
                demanda.codigo_disciplina, room.id, semester_id
            )
            candidate.score += frequency_bonus

            candidates.append(candidate)

        return candidates

    def _get_professor_preferences_for_professor(
        self, professor: Optional[Professor]
    ) -> Dict:
        """Get professor preferences dict from Professor object (different from string version)."""
        prefs = {"preferred_rooms": [], "preferred_characteristics": []}

        if not professor:
            return prefs

        # Get room preferences
        stmt = self.session.execute(
            text(
                "SELECT sala_id FROM professor_prefere_sala WHERE professor_id = :prof_id"
            ),
            {"prof_id": professor.id},
        )
        room_prefs = [row[0] for row in stmt.fetchall()]
        prefs["preferred_rooms"].extend(room_prefs)

        # Get characteristic preferences
        stmt = self.session.execute(
            text(
                "SELECT caracteristica_id FROM professor_prefere_caracteristica WHERE professor_id = :prof_id"
            ),
            {"prof_id": professor.id},
        )
        char_prefs = [row[0] for row in stmt.fetchall()]
        prefs["preferred_characteristics"].extend(char_prefs)

        return prefs

    def _calculate_historical_frequency_bonus(
        self, disciplina_codigo: str, sala_id: int, exclude_semester_id: int
    ) -> int:
        """
        Calculate historical frequency bonus (RF-006.6).

        Returns bonus points based on how many times this discipline has been
        allocated to this room in previous semesters.

        Args:
            disciplina_codigo: Discipline code to look up history for
            sala_id: Room ID to check frequency with
            exclude_semester_id: Current semester to exclude from history

        Returns:
            int: Bonus points (1 point per historical allocation)
        """
        # Find all alocacoes_semestrais for this discipline in other semesters
        frequency = self.alocacao_repo.get_discipline_room_frequency(
            disciplina_codigo, sala_id, exclude_semester_id
        )

        return frequency  # Direct 1:1 bonus points

    def _check_allocation_conflicts(
        self, candidate: AllocationCandidate, semester_id: int
    ) -> List[Dict]:
        """
        Check for conflicts when allocating atomic blocks for a candidate.

        IMPORTANT: Conflicts are checked within the CURRENT semester only (not across all semesters).
        This ensures proper semester-based isolation of allocations.
        """
        conflicts = []

        for bloco_codigo, dia_sigaa in candidate.atomic_blocks:
            # Check for conflicts IN THE CURRENT SEMESTER only
            has_conflict = self.alocacao_repo.check_conflict(
                candidate.sala.id, dia_sigaa, bloco_codigo, semestre_id=semester_id
            )

            if has_conflict:
                conflicts.append(
                    {
                        "dia_sigaa": dia_sigaa,
                        "codigo_bloco": bloco_codigo,
                        "sala_id": candidate.sala.id,
                    }
                )

        return conflicts

    def _allocate_atomic_blocks(
        self, candidate: AllocationCandidate, semester_id: int
    ) -> bool:
        """
        Allocate atomic blocks for a candidate (RF-006.7).

        Creates one database record per atomic block.
        """
        try:
            for bloco_codigo, dia_sigaa in candidate.atomic_blocks:
                allocation_dto = AlocacaoSemestralCreate(
                    semestre_id=semester_id,
                    demanda_id=candidate.demanda_id,
                    sala_id=candidate.sala.id,
                    dia_semana_id=dia_sigaa,
                    codigo_bloco=bloco_codigo,
                )

                self.alocacao_repo.create(allocation_dto)

            logger.info(
                f"Allocated {len(candidate.atomic_blocks)} blocks for demand {candidate.demanda_id} to room {candidate.sala.id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to allocate blocks for demand {candidate.demanda_id}: {e}"
            )
            self.session.rollback()
            return False

    def _write_detailed_allocation_log(
        self,
        semester_id: int,
        unallocated_demands: List[Any],
        phase1_result: PhaseResult,
        phase2_result: PhaseResult,
        phase3_result: PhaseResult,
        final_result: Dict,
    ) -> None:
        """
        Write detailed autonomous allocation log when DEBUG is enabled.

        Creates a detailed log file with comprehensive statistics about the allocation process.
        """
        from pathlib import Path

        log_file = settings.LOGS_DIR / "autonomous_allocation.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Gather comprehensive statistics
        stats = self._gather_allocation_statistics(semester_id, unallocated_demands)

        # Format detailed log content
        log_content = f"""
{'='*80}
AUTONOMOUS ALLOCATION DETAILED LOG - {timestamp}
{'='*80}

SEMESTER INFORMATION
Semester ID: {semester_id}
Execution Timestamp: {timestamp}

INITIAL STATE
Total Unallocated Demands: {len(unallocated_demands)}
Total Demands Processed: {stats['total_demands_in_semester']}
Allocated Demands (Before): {stats['previously_allocated']}
Unallocated Demands (Before): {len(unallocated_demands)}

RULES STATISTICS
Hard Rules (Prioridade=0):
  - Total Hard Rules: {stats['total_hard_rules']}
  - Discipline-Specific Rules: {stats['discipline_specific_rules']}
  - Room-Specific Rules: {stats['room_specific_rules']}
  - Type-Specific Rules: {stats['type_specific_rules']}
  - Characteristic-Specific Rules: {stats['characteristic_specific_rules']}

PROFESSOR STATISTICS
Total Professors in Demands: {stats['total_professors_in_demands']}
Professors with Reduced Mobility: {stats['professors_with_reduced_mobility']}
Professors with Room Preferences: {stats['professors_with_room_prefs']}
Professors with Characteristic Preferences: {stats['professors_with_char_prefs']}

ALLOCATION PHASES

PHASE 1 - HARD RULES ALLOCATION
-------------------------------
Allocations Completed: {phase1_result.allocations_completed}
Conflicts Detected: {phase1_result.conflicts_found}
Demands Skipped: {phase1_result.demands_skipped}

Details:
{chr(10).join(f"  - {detail}" for detail in phase1_result.details) if phase1_result.details else "  No details available"}

PHASE 2 - SOFT SCORING PHASE
---------------------------
Candidates Scored: {phase2_result.allocations_completed}
Conflicts Detected: {phase2_result.conflicts_found}
Demands Skipped: {phase2_result.demands_skipped}

Details:
{chr(10).join(f"  - {detail}" for detail in phase2_result.details) if phase2_result.details else "  No details available"}

PHASE 3 - ATOMIC ALLOCATION PHASE
--------------------------------
Allocations Completed: {phase3_result.allocations_completed}
Conflicts Detected: {phase3_result.conflicts_found}
Demands Skipped: {phase3_result.demands_skipped}

Details:
{chr(10).join(f"  - {detail}" for detail in phase3_result.details) if phase3_result.details else "  No details available"}

FINAL RESULTS
Total Allocations Completed: {final_result['allocations_completed']}
Total Conflicts Found: {final_result['conflicts_found']}
Demands Still Unallocated: {final_result['demands_skipped']}
Allocation Success Rate: {final_result.get('progress_percentage', 0):.1f}%

CURRENT ALLOCATION STATUS
Allocated Demands (Final): {stats['previously_allocated'] + final_result['allocations_completed']}
Unallocated Demands (Final): {final_result['demands_skipped']}
Total Allocation Percentage: {((stats['previously_allocated'] + final_result['allocations_completed']) / stats['total_demands_in_semester'] * 100):.1f}%

DATABASE STATISTICS
Total Database Allocations: {stats['total_db_allocations']}
Total Database Conflicts: {stats['total_db_conflicts']}
Average Allocations per Room: {stats['avg_allocations_per_room']:.1f}

EXECUTION PERFORMANCE
Total Execution Time: {final_result.get('performance', {}).get('total_execution_time', 'N/A')} seconds
Phase Breakdown:
  - Schedule Parsing: {final_result.get('performance', {}).get('schedule_parsing_time', 'N/A')}s
  - Phase 1 (Hard Rules): {final_result.get('performance', {}).get('phase1_time', 'N/A')}s
  - Phase 2 (Soft Scoring): {final_result.get('performance', {}).get('phase2_time', 'N/A')}s
  - Phase 3 (Atomic Allocation): {final_result.get('performance', {}).get('phase3_time', 'N/A')}s
Throughput: {final_result.get('performance', {}).get('allocations_per_second', 'N/A')} allocations/second

{'='*80}
END OF AUTONOMOUS ALLOCATION LOG
{'='*80}

"""

        # Write to log file
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_content)
                f.write("\n")
        except Exception as e:
            logger.warning(f"Failed to write detailed allocation log: {e}")

    def _gather_allocation_statistics(
        self, semester_id: int, unallocated_demands: List[Any]
    ) -> Dict:
        """
        Gather comprehensive statistics for the detailed log.

        Returns detailed statistics about rules, professors, rooms, etc.
        """
        stats = {
            "total_demands_in_semester": 0,
            "previously_allocated": 0,
            "total_hard_rules": 0,
            "discipline_specific_rules": 0,
            "room_specific_rules": 0,
            "type_specific_rules": 0,
            "characteristic_specific_rules": 0,
            "total_professors_in_demands": 0,
            "professors_with_reduced_mobility": 0,
            "professors_with_room_prefs": 0,
            "professors_with_char_prefs": 0,
            "total_db_allocations": 0,
            "total_db_conflicts": 0,
            "avg_allocations_per_room": 0.0,
        }

        # Count total demands in semester
        semester_allocations = self.alocacao_repo.get_by_semestre(semester_id)
        stats["total_demands_in_semester"] = len(
            set(a.demanda_id for a in semester_allocations)
        ) + len(unallocated_demands)
        stats["previously_allocated"] = len(
            set(a.demanda_id for a in semester_allocations)
        )

        # Analyze rules
        all_discipline_codes = [d.codigo_disciplina for d in unallocated_demands]
        all_rules = []
        for code in set(all_discipline_codes):
            all_rules.extend(self.regra_repo.find_rules_by_disciplina(code))

        stats["total_hard_rules"] = sum(1 for r in all_rules if r.prioridade == 0)
        stats["discipline_specific_rules"] = sum(
            1 for r in all_rules if r.tipo_regra == "DISCIPLINA_SALA"
        )
        stats["room_specific_rules"] = sum(
            1 for r in all_rules if r.tipo_regra == "DISCIPLINA_SALA"
        )
        stats["type_specific_rules"] = sum(
            1 for r in all_rules if r.tipo_regra == "DISCIPLINA_TIPO_SALA"
        )
        stats["characteristic_specific_rules"] = sum(
            1 for r in all_rules if r.tipo_regra == "DISCIPLINA_CARACTERISTICA"
        )

        # Analyze professors
        professor_ids = set()
        for demanda in unallocated_demands:
            prof_text = demanda.professores_disciplina.strip()
            if prof_text:
                prof_names = [name.strip() for name in prof_text.split(",")]
                for prof_name in prof_names:
                    prof = self.prof_repo.get_by_nome_completo(prof_name)
                    if prof:
                        professor_ids.add(prof.id)

        stats["total_professors_in_demands"] = len(professor_ids)

        # Check professor preferences and mobility
        reduced_mobility_count = 0
        room_prefs_count = 0
        char_prefs_count = 0

        for prof_id in professor_ids:
            prof = self.prof_repo.get_by_id(prof_id)
            if prof:
                if prof.tem_baixa_mobilidade:
                    reduced_mobility_count += 1

                # Check preferences
                prefs = self._get_professor_preferences_for_professor(prof)
                if prefs["preferred_rooms"]:
                    room_prefs_count += 1
                if prefs["preferred_characteristics"]:
                    char_prefs_count += 1

        stats["professors_with_reduced_mobility"] = reduced_mobility_count
        stats["professors_with_room_prefs"] = room_prefs_count
        stats["professors_with_char_prefs"] = char_prefs_count

        # Database statistics for current semester only
        all_allocs = self.alocacao_repo.get_by_semestre(semester_id)
        stats["total_db_allocations"] = len(all_allocs)

        # Get all rooms to calculate average allocations per room
        all_rooms = self.sala_repo.get_all()
        if all_rooms:
            # Calculate average based on semester-allocated rooms
            allocated_rooms = set(a.sala_id for a in all_allocs)
            stats["avg_allocations_per_room"] = (
                len(all_allocs) / len(allocated_rooms) if allocated_rooms else 0.0
            )

        # Conflicts count within the current semester only
        stats["total_db_conflicts"] = sum(
            len(self.alocacao_repo.get_conflicts_in_room(room.id, semester_id))
            for room in all_rooms
        )

        return stats
