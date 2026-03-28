"""
Room Scoring Service - Advanced Scoring for Manual & Autonomous Allocation

Provides unified scoring algorithm for room-demand compatibility with:
- Historical frequency bonus (RF-006.6)
- Hard rules compliance
- Professor preferences
- Semester-isolated conflict detection

Used by both ManualAllocationService and AutonomousAllocationService for consistency.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config.scoring_config import SCORING_WEIGHTS
from src.models.academic import Professor
from src.models.inventory import Sala
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.optimized_allocation_repo import OptimizedAllocationRepository
from src.repositories.professor import ProfessorRepository
from src.repositories.regra import RegraRepository
from src.repositories.sala import SalaRepository
from src.schemas.manual_allocation import CompatibilityScore
from src.services.hybrid_discipline_service import REGULAR_CLASSROOM_TYPE_ID
from src.utils.sigaa_parser import SigaaScheduleParser

logger = logging.getLogger(__name__)


@dataclass
class ContinuityScoringContext:
    """Optional context for future continuity-aware scoring phases.

    This context is intentionally neutral in the initial infrastructure step:
    the scorer accepts it, but does not yet alter room ranking.
    """

    is_hybrid: bool = False
    discipline_existing_room_ids: List[int] = field(default_factory=list)
    professor_anchor_room_id: Optional[int] = None
    professor_anchor_building_id: Optional[int] = None
    professor_anchor_room_type_id: Optional[int] = None
    future_day_coverage_count: int = 0
    future_day_coverage_by_room_id: Dict[int, int] = field(default_factory=dict)


@dataclass
class ScoringBreakdown:
    """Detailed breakdown of how a room scored."""

    total_score: int = 0
    capacity_points: int = 0
    hard_rules_points: int = 0
    soft_preference_points: int = 0
    historical_frequency_points: int = 0
    discipline_continuity_points: int = 0
    professor_anchor_points: int = 0
    future_coverage_points: int = 0
    fragmentation_penalty: int = 0

    # Details for each category
    capacity_satisfied: bool = False
    hard_rules_compliant: bool = True
    hard_rules_satisfied: List[str] = None  # Names of satisfied rules
    soft_preferences_satisfied: List[str] = None  # Names of satisfied preferences
    historical_allocations: int = (
        0  # How many times this discipline was allocated to this room
    )

    def __post_init__(self):
        if self.hard_rules_satisfied is None:
            self.hard_rules_satisfied = []
        if self.soft_preferences_satisfied is None:
            self.soft_preferences_satisfied = []


@dataclass
class RoomCandidate:
    """Internal structure for room-demand candidate scoring."""

    sala: Sala
    score: int = 0
    has_conflicts: bool = False
    rule_violations: List[str] = None
    scoring_breakdown: ScoringBreakdown = None

    def __post_init__(self):
        if self.rule_violations is None:
            self.rule_violations = []
        if self.scoring_breakdown is None:
            self.scoring_breakdown = ScoringBreakdown()


@dataclass
class BlockGroup:
    """Group of atomic blocks on the same day.

    Represents a set of time blocks that must be allocated together
    because they are on the same day. Different days can be allocated
    to different rooms for hybrid disciplines.
    """

    day_id: int  # SIGAA day code (2=MON, 3=TUE, ..., 7=SAT)
    day_name: str  # Human readable (SEG, TER, etc.)
    blocks: List[str] = None  # Block codes (M1, M2, etc.)

    def __post_init__(self):
        if self.blocks is None:
            self.blocks = []

    @property
    def block_count(self) -> int:
        """Number of atomic blocks in this group."""
        return len(self.blocks)

    def get_atomic_tuples(self) -> List[tuple]:
        """Get list of (block_code, day_id) tuples for this group."""
        return [(block, self.day_id) for block in self.blocks]


@dataclass
class BlockGroupScoringBreakdown:
    """Detailed scoring breakdown for a specific block group + room combination."""

    total_score: int = 0
    capacity_points: int = 0
    hard_rules_points: int = 0
    soft_preference_points: int = 0
    historical_frequency_points: int = 0
    hybrid_bonus_points: int = 0  # Bonus for hybrid discipline room type match
    discipline_continuity_points: int = 0
    professor_anchor_points: int = 0
    future_coverage_points: int = 0
    fragmentation_penalty: int = 0

    # Details
    capacity_satisfied: bool = False
    hard_rules_compliant: bool = True
    hard_rules_satisfied: List[str] = None
    soft_preferences_satisfied: List[str] = None
    historical_allocations: int = 0  # Count for THIS DAY specifically
    hybrid_room_type_match: bool = False  # True if room type matches hybrid pattern

    def __post_init__(self):
        if self.hard_rules_satisfied is None:
            self.hard_rules_satisfied = []
        if self.soft_preferences_satisfied is None:
            self.soft_preferences_satisfied = []


@dataclass
class BlockGroupRoomScore:
    """Scoring result for a specific block group + room combination."""

    block_group: BlockGroup
    room_id: int
    room_name: str
    room_capacity: int
    room_type: str
    building_name: str
    score: int
    breakdown: BlockGroupScoringBreakdown
    has_conflict: bool = False
    conflict_details: List[str] = None

    def __post_init__(self):
        if self.conflict_details is None:
            self.conflict_details = []


class RoomScoringService:
    """
    Unified service for advanced room-demand compatibility scoring.

    Provides consistent scoring across manual and autonomous allocation systems.
    """

    def __init__(self, session: Session):
        """Initialize with required repositories."""
        self.session = session
        self.alocacao_repo = AlocacaoRepository(session)
        self.optimized_alocacao_repo = OptimizedAllocationRepository(session)
        self.demanda_repo = DisciplinaRepository(session)
        self.regra_repo = RegraRepository(session)
        self.prof_repo = ProfessorRepository(session)
        self.sala_repo = SalaRepository(session)
        self.parser = SigaaScheduleParser()

        # Hybrid discipline detection service (injected via set_hybrid_detection_service)
        self._hybrid_detection_service = None
        self._rules_cache: Dict[str, List[Any]] = {}
        self._available_rooms_cache: Dict[Tuple[str, ...], List[Any]] = {}
        self._professor_lookup_cache: Dict[str, Optional[Professor]] = {}
        self._professor_preferences_cache: Dict[int, Dict] = {}
        self._room_characteristics_cache: Dict[int, set[int]] = {}
        self._characteristic_name_cache: Dict[int, str] = {}
        self._historical_frequency_cache: Dict[Tuple[str, int, int], int] = {}
        self._historical_frequency_day_cache: Dict[Tuple[str, int, int, int], int] = {}
        self._historical_room_occupancy_cache: Dict[Tuple[int, int], int] = {}

    def set_hybrid_detection_service(self, hybrid_service) -> None:
        """
        Set the hybrid discipline detection service for hybrid-aware scoring.

        Args:
            hybrid_service: HybridDisciplineDetectionService instance
        """
        self._hybrid_detection_service = hybrid_service

    def clear_runtime_caches(self) -> None:
        """Clear mutable runtime caches used during scoring."""
        self._available_rooms_cache.clear()

    def _get_rules_for_disciplina(self, codigo_disciplina: str) -> List[Any]:
        if codigo_disciplina not in self._rules_cache:
            self._rules_cache[codigo_disciplina] = (
                self.regra_repo.find_rules_by_disciplina(codigo_disciplina)
            )
        return self._rules_cache[codigo_disciplina]

    def _get_available_rooms(self, required_blocks: List[str]) -> List[Any]:
        cache_key = tuple(sorted({block for block in required_blocks if block}))
        cached = self._available_rooms_cache.get(cache_key)
        if cached is None:
            cached = self.sala_repo.get_available_for_allocation(
                required_blocks=list(cache_key)
            )
            self._available_rooms_cache[cache_key] = cached
        return cached

    def _get_demanda_codigo_disciplina(self, demanda: Any) -> Optional[str]:
        """Extract discipline code from DTOs or dict-shaped demand objects."""
        if demanda is None:
            return None
        if hasattr(demanda, "codigo_disciplina"):
            return getattr(demanda, "codigo_disciplina")
        if isinstance(demanda, dict):
            return demanda.get("codigo_disciplina")
        return None

    def _has_explicit_non_classroom_override(
        self,
        room: Sala,
        demanda: Any,
        rules: List[Any],
    ) -> bool:
        """Return whether explicit room/type rules intentionally allow this room."""
        explicit_rules = [
            rule
            for rule in rules
            if rule.tipo_regra in {"DISCIPLINA_TIPO_SALA", "DISCIPLINA_SALA"}
        ]
        return any(
            self._check_rule_compliance(room, demanda, rule) for rule in explicit_rules
        )

    def is_room_type_eligible_for_demand(
        self,
        room: Sala,
        demanda: Any,
        rules: Optional[List[Any]] = None,
        continuity_context: Optional[ContinuityScoringContext] = None,
    ) -> bool:
        """Apply the default room-type policy before scoring.

        Policy:
        - Regular classrooms are always eligible.
        - Specialized rooms are eligible only when explicitly allowed by room/type
          rules, when the discipline is hybrid, or when the demand is already in
          progress in that room and continuity must be preserved.
        """
        if room.tipo_sala_id == REGULAR_CLASSROOM_TYPE_ID:
            return True

        if (
            continuity_context is not None
            and room.id in continuity_context.discipline_existing_room_ids
        ):
            return True

        if rules is None:
            codigo_disciplina = self._get_demanda_codigo_disciplina(demanda)
            rules = (
                self._get_rules_for_disciplina(codigo_disciplina)
                if codigo_disciplina
                else []
            )

        if self._has_explicit_non_classroom_override(room, demanda, rules):
            return True

        codigo_disciplina = self._get_demanda_codigo_disciplina(demanda)
        if (
            codigo_disciplina
            and self._hybrid_detection_service is not None
            and self._hybrid_detection_service.is_hybrid(codigo_disciplina)
        ):
            return True

        return False

    def _build_room_occupancy_lookup(
        self, room_ids: List[int], semester_id: int
    ) -> Dict[int, int]:
        unique_room_ids = sorted(set(room_ids))
        if not unique_room_ids:
            return {}

        occupancy = self.optimized_alocacao_repo.get_room_occupancy_batch(
            unique_room_ids,
            semester_id,
        )

        unresolved_room_ids = []
        for room_id in unique_room_ids:
            if occupancy.get(room_id, 0) > 0:
                continue

            cached = self._historical_room_occupancy_cache.get((room_id, semester_id))
            if cached is not None:
                occupancy[room_id] = cached
            else:
                unresolved_room_ids.append(room_id)

        previous_semester_id = semester_id - 1
        while unresolved_room_ids and previous_semester_id > 0:
            previous_occupancy = self.optimized_alocacao_repo.get_room_occupancy_batch(
                unresolved_room_ids,
                previous_semester_id,
            )
            next_unresolved = []
            for room_id in unresolved_room_ids:
                historical_count = previous_occupancy.get(room_id, 0)
                if historical_count > 0:
                    occupancy[room_id] = historical_count
                    self._historical_room_occupancy_cache[(room_id, semester_id)] = (
                        historical_count
                    )
                else:
                    next_unresolved.append(room_id)

            unresolved_room_ids = next_unresolved
            previous_semester_id -= 1

        for room_id in unresolved_room_ids:
            occupancy[room_id] = 0
            self._historical_room_occupancy_cache[(room_id, semester_id)] = 0

        return occupancy

    def _sort_room_candidates(
        self,
        candidates: List[RoomCandidate],
        semester_id: int,
    ) -> Dict[int, int]:
        occupancy_lookup = self._build_room_occupancy_lookup(
            [candidate.sala.id for candidate in candidates],
            semester_id,
        )
        candidates.sort(
            key=lambda candidate: (
                candidate.score,
                not candidate.has_conflicts,
                occupancy_lookup.get(candidate.sala.id, 0),
            ),
            reverse=True,
        )
        return occupancy_lookup

    def _build_conflict_lookup(
        self,
        room_ids: List[int],
        atomic_blocks: List[tuple[str, int]],
        semester_id: int,
    ) -> Dict[Tuple[int, int, str], bool]:
        """Resolve room/block conflicts for many candidate rooms in one batch."""
        unique_room_ids = sorted(set(room_ids))
        if not unique_room_ids or not atomic_blocks:
            return {}

        slots = list(
            dict.fromkeys(
                (room_id, day_id, block_code)
                for room_id in unique_room_ids
                for block_code, day_id in atomic_blocks
            )
        )
        return self.optimized_alocacao_repo.check_conflicts_batch(slots, semester_id)

    def _collect_atomic_conflicts_from_lookup(
        self,
        sala_id: int,
        atomic_blocks: List[tuple[str, int]],
        conflict_map: Dict[Tuple[int, int, str], bool],
    ) -> List[Dict]:
        """Build atomic conflict details from a precomputed lookup."""
        conflicts = []
        for bloco_codigo, dia_sigaa in atomic_blocks:
            if conflict_map.get((sala_id, dia_sigaa, bloco_codigo), False):
                conflicts.append(
                    {
                        "dia_sigaa": dia_sigaa,
                        "codigo_bloco": bloco_codigo,
                        "sala_id": sala_id,
                    }
                )
        return conflicts

    def _collect_block_group_conflicts_from_lookup(
        self,
        sala_id: int,
        block_group: BlockGroup,
        conflict_map: Dict[Tuple[int, int, str], bool],
    ) -> List[str]:
        """Build block-group conflict descriptions from a precomputed lookup."""
        conflicts = []
        for block_code in block_group.blocks:
            if conflict_map.get((sala_id, block_group.day_id, block_code), False):
                conflicts.append(f"{block_group.day_name} {block_code} já alocado")
        return conflicts

    def _split_rules_by_priority(self, rules: List) -> tuple[List, List]:
        """Split discipline rules into hard and soft sets."""
        hard_rules = [rule for rule in rules if rule.prioridade == 0]
        soft_rules = [rule for rule in rules if rule.prioridade > 0]
        return hard_rules, soft_rules

    def _evaluate_hard_rules(
        self, room: Sala, demanda, hard_rules: List
    ) -> tuple[bool, int, List[str]]:
        """Return hard-rule compliance, awarded points, and matched rule labels."""
        if not hard_rules:
            return True, 0, []

        hard_point_total = 0
        hard_rules_satisfied_list = []

        for rule in hard_rules:
            compliance = self._check_rule_compliance(room, demanda, rule)

            logger.debug(
                f"Hard rule check: {rule.descricao} | "
                f"Room: {room.nome} (tipo_sala_id={room.tipo_sala_id}) | "
                f"Compliant: {compliance}"
            )

            if not compliance:
                return False, 0, []

            hard_point_total += SCORING_WEIGHTS.HARD_RULE_COMPLIANCE
            hard_rules_satisfied_list.append(self._get_rule_description(rule))

        return True, hard_point_total, hard_rules_satisfied_list

    def _evaluate_soft_rules(
        self, room: Sala, demanda, soft_rules: List
    ) -> tuple[int, List[str]]:
        """Return points and descriptions for satisfied soft rules."""
        soft_rule_points = 0
        soft_rule_matches = []

        for rule in soft_rules:
            if not self._check_rule_compliance(room, demanda, rule):
                continue

            soft_rule_points += rule.prioridade
            description = (
                rule.descricao.strip()
                if rule.descricao
                else self._get_rule_description(rule)
            )
            soft_rule_matches.append(f"Regra suave: {description}")

        return soft_rule_points, soft_rule_matches

    def score_room_candidates_for_demand(
        self,
        demanda_id: int,
        semester_id: int,
        professor_override: Optional[Professor] = None,
        continuity_context: Optional[ContinuityScoringContext] = None,
    ) -> List[RoomCandidate]:
        """
        Score all room candidates for a demand using advanced algorithm.

        Includes:
        - Historical frequency bonus (RF-006.6)
        - Hard rules compliance
        - Professor preferences
        - Conflict detection within specified semester

        Args:
            demanda_id: Demand to score rooms for
            semester_id: Semester to check conflicts within
            professor_override: Optional professor object (if known)

        Returns:
            List of RoomCandidate objects, sorted by score descending
        """
        # Get demand details
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return []

        # Lookup professor if not provided
        professor = professor_override
        if not professor:
            professor_map = self._lookup_professors_for_demands_from_objects([demanda])
            professor = professor_map.get(demanda_id)

        # Get professor preferences
        professor_prefs = self._get_professor_preferences_for_professor(professor)

        # Get rules for this demand
        all_rules = self._get_rules_for_disciplina(demanda.codigo_disciplina)
        hard_rules, _soft_rules = self._split_rules_by_priority(all_rules)

        atomic_blocks = self.parser.split_to_atomic_tuples(demanda.horario_sigaa_bruto)
        required_blocks = [block_code for block_code, _ in atomic_blocks]

        # Get only rooms enabled for the required blocks
        all_rooms = [
            room
            for room in self._get_available_rooms(required_blocks)
            if self.is_room_type_eligible_for_demand(
                room,
                demanda,
                all_rules,
                continuity_context,
            )
        ]
        conflict_map = self._build_conflict_lookup(
            [room.id for room in all_rooms],
            atomic_blocks,
            semester_id,
        )

        candidates = []
        for room in all_rooms:
            candidate = RoomCandidate(sala=room)

            # Parse atomic blocks for this demand
            candidate.atomic_blocks = atomic_blocks

            # Calculate detailed scoring breakdown
            scoring_breakdown = self._calculate_detailed_scoring_breakdown(
                room,
                demanda,
                all_rules,
                professor_prefs,
                semester_id,
                continuity_context,
            )

            if hard_rules and not scoring_breakdown.hard_rules_compliant:
                continue

            candidate.score = scoring_breakdown.total_score
            candidate.scoring_breakdown = scoring_breakdown

            # Extract rule violations for compatibility
            candidate.rule_violations = []
            if not scoring_breakdown.capacity_satisfied:
                candidate.rule_violations.append("Capacidade insuficiente")
            if hard_rules and not scoring_breakdown.hard_rules_compliant:
                candidate.rule_violations.append("Regras rígidas não atendidas")

            if not candidate.rule_violations:
                candidate.rule_violations = []

            # Check for conflicts within the specified semester
            conflicts = self._check_allocation_conflicts_semester_isolated(
                candidate,
                semester_id,
                conflict_map,
            )
            candidate.has_conflicts = len(conflicts) > 0

            candidates.append(candidate)

        # Sort by score (highest first), then by conflict status, then by room occupancy (highest first for optimization)
        occupancy_lookup = self._sort_room_candidates(candidates, semester_id)

        # Debug: Log when room occupancy optimization affects sorting
        if len(candidates) >= 2:
            top_score = candidates[0].score
            second_score = candidates[1].score
            if top_score == second_score:
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(
                    f"Room occupancy optimization applied for demand {candidates[0].sala.id}: "
                    f"Room {candidates[0].sala.nome} (occupancy: {occupancy_lookup.get(candidates[0].sala.id, 0)}) "
                    f"vs Room {candidates[1].sala.nome} (occupancy: {occupancy_lookup.get(candidates[1].sala.id, 0)})"
                )

        return candidates

    def score_room_candidates_for_full_continuity(
        self,
        demanda_id: int,
        pending_blocks: List[tuple[str, int]],
        semester_id: int,
        professor_override: Optional[Professor] = None,
        continuity_context: Optional[ContinuityScoringContext] = None,
    ) -> List[RoomCandidate]:
        """
        Score rooms for allocating all pending blocks of a demand to a single room.

        Unlike the legacy full-demand scorer, this method evaluates only the still-pending
        atomic blocks for availability and conflicts. This is required for resumable
        partial allocations and the discipline continuity phase.
        """
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda or not pending_blocks:
            return []

        professor = professor_override
        if not professor:
            professor_map = self._lookup_professors_for_demands_from_objects([demanda])
            professor = professor_map.get(demanda_id)

        professor_prefs = self._get_professor_preferences_for_professor(professor)
        all_rules = self._get_rules_for_disciplina(demanda.codigo_disciplina)
        hard_rules, _soft_rules = self._split_rules_by_priority(all_rules)

        required_blocks = sorted({block_code for block_code, _ in pending_blocks})
        all_rooms = [
            room
            for room in self._get_available_rooms(required_blocks)
            if self.is_room_type_eligible_for_demand(
                room,
                demanda,
                all_rules,
                continuity_context,
            )
        ]
        conflict_map = self._build_conflict_lookup(
            [room.id for room in all_rooms],
            pending_blocks,
            semester_id,
        )

        candidates = []
        for room in all_rooms:
            candidate = RoomCandidate(sala=room)
            candidate.atomic_blocks = pending_blocks

            scoring_breakdown = self._calculate_detailed_scoring_breakdown(
                room,
                demanda,
                all_rules,
                professor_prefs,
                semester_id,
                continuity_context,
            )

            if hard_rules and not scoring_breakdown.hard_rules_compliant:
                continue

            candidate.score = scoring_breakdown.total_score
            candidate.scoring_breakdown = scoring_breakdown
            candidate.rule_violations = []
            if not scoring_breakdown.capacity_satisfied:
                candidate.rule_violations.append("Capacidade insuficiente")
            if hard_rules and not scoring_breakdown.hard_rules_compliant:
                candidate.rule_violations.append("Regras rígidas não atendidas")

            conflicts = self._check_atomic_block_conflicts(
                room.id,
                pending_blocks,
                semester_id,
                conflict_map,
            )
            candidate.has_conflicts = len(conflicts) > 0
            candidates.append(candidate)

        self._sort_room_candidates(candidates, semester_id)
        return candidates

    # ========================================================================
    # BLOCK-GROUP LEVEL SCORING (For Partial/Split Allocation)
    # ========================================================================

    def group_blocks_by_day(self, horario_sigaa: str) -> List[BlockGroup]:
        """
        Group atomic blocks by day for per-day scoring.

        Same-day blocks must stay together; different-day blocks can be split.

        Args:
            horario_sigaa: SIGAA schedule string (e.g., "24M12 6T34")

        Returns:
            List of BlockGroup objects, one per distinct day
        """
        # Map SIGAA day codes to human-readable names
        day_names = {
            2: "SEG",
            3: "TER",
            4: "QUA",
            5: "QUI",
            6: "SEX",
            7: "SAB",
        }

        # Parse to atomic tuples: [(block_code, day_id), ...]
        atomic_tuples = self.parser.split_to_atomic_tuples(horario_sigaa)

        # Group by day
        day_blocks: Dict[int, List[str]] = {}
        for block_code, day_id in atomic_tuples:
            if day_id not in day_blocks:
                day_blocks[day_id] = []
            day_blocks[day_id].append(block_code)

        # Create BlockGroup objects
        block_groups = []
        for day_id in sorted(day_blocks.keys()):
            block_groups.append(
                BlockGroup(
                    day_id=day_id,
                    day_name=day_names.get(day_id, f"DIA{day_id}"),
                    blocks=sorted(day_blocks[day_id]),
                )
            )

        return block_groups

    def score_rooms_for_block_group(
        self,
        demanda_id: int,
        block_group: BlockGroup,
        semester_id: int,
        professor_override: Optional[Professor] = None,
        continuity_context: Optional[ContinuityScoringContext] = None,
    ) -> List[BlockGroupRoomScore]:
        """
        Score all rooms for a specific block group.

        This is the core of per-day scoring: each block group gets its own
        scoring with day-specific historical frequency bonus.

        Args:
            demanda_id: Demand ID
            block_group: The block group to score rooms for
            semester_id: Semester to check conflicts within
            professor_override: Optional professor object

        Returns:
            List of BlockGroupRoomScore objects, sorted by score descending
        """
        # Get demand details
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return []

        # Lookup professor if not provided
        professor = professor_override
        if not professor:
            professor_map = self._lookup_professors_for_demands_from_objects([demanda])
            professor = professor_map.get(demanda_id)

        # Get professor preferences
        professor_prefs = self._get_professor_preferences_for_professor(professor)

        # Get rules for this demand
        all_rules = self._get_rules_for_disciplina(demanda.codigo_disciplina)
        hard_rules, _soft_rules = self._split_rules_by_priority(all_rules)

        # Get only rooms enabled for this day's required blocks
        all_rooms = [
            room
            for room in self._get_available_rooms(block_group.blocks)
            if self.is_room_type_eligible_for_demand(
                room,
                demanda,
                all_rules,
                continuity_context,
            )
        ]
        conflict_map = self._build_conflict_lookup(
            [room.id for room in all_rooms],
            block_group.get_atomic_tuples(),
            semester_id,
        )

        scores = []
        for room in all_rooms:
            # Calculate per-block-group scoring breakdown
            breakdown = self._calculate_block_group_scoring_breakdown(
                room,
                demanda,
                block_group,
                all_rules,
                professor_prefs,
                semester_id,
                continuity_context,
            )

            if hard_rules and not breakdown.hard_rules_compliant:
                continue

            # Check for conflicts for this block group specifically
            conflicts = self._check_block_group_conflicts(
                room.id,
                block_group,
                semester_id,
                conflict_map,
            )

            # Get room metadata
            predio_name = (
                self._get_building_name(room.predio_id) if room.predio_id else "N/A"
            )
            tipo_sala_name = (
                self._get_room_type_name_by_id(room.tipo_sala_id)
                if room.tipo_sala_id
                else "N/A"
            )

            score = BlockGroupRoomScore(
                block_group=block_group,
                room_id=room.id,
                room_name=room.nome,
                room_capacity=room.capacidade or 0,
                room_type=tipo_sala_name,
                building_name=predio_name,
                score=breakdown.total_score,
                breakdown=breakdown,
                has_conflict=len(conflicts) > 0,
                conflict_details=conflicts,
            )
            scores.append(score)

        # Sort by score descending, then by conflict status
        scores.sort(key=lambda s: (s.score, not s.has_conflict), reverse=True)

        return scores

    def score_rooms_for_all_block_groups(
        self,
        demanda_id: int,
        semester_id: int,
        professor_override: Optional[Professor] = None,
    ) -> Dict[int, List[BlockGroupRoomScore]]:
        """
        Score all rooms for all block groups of a demand.

        Convenience method that groups blocks and scores each group independently.

        Args:
            demanda_id: Demand ID
            semester_id: Semester to check conflicts within
            professor_override: Optional professor object

        Returns:
            Dict mapping day_id to list of BlockGroupRoomScore objects
        """
        # Get demand to parse schedule
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return {}

        # Group blocks by day
        block_groups = self.group_blocks_by_day(demanda.horario_sigaa_bruto)

        # Score each group
        results = {}
        for block_group in block_groups:
            scores = self.score_rooms_for_block_group(
                demanda_id, block_group, semester_id, professor_override
            )
            results[block_group.day_id] = scores

        return results

    def _calculate_block_group_scoring_breakdown(
        self,
        room: Sala,
        demanda,
        block_group: BlockGroup,
        rules: List,
        professor_prefs: Dict,
        semester_id: int,
        continuity_context: Optional[ContinuityScoringContext] = None,
    ) -> BlockGroupScoringBreakdown:
        """
        Calculate detailed scoring breakdown for a specific block group.

        Similar to _calculate_detailed_scoring_breakdown but uses per-day
        historical frequency instead of overall frequency.
        """
        breakdown = BlockGroupScoringBreakdown()

        # 1. Capacity check (+3 points by default)
        if room.capacidade and room.capacidade >= demanda.vagas_disciplina:
            breakdown.capacity_points = SCORING_WEIGHTS.CAPACITY_ADEQUATE
            breakdown.capacity_satisfied = True
        else:
            breakdown.capacity_points = 0
            breakdown.capacity_satisfied = False

        hard_rules, soft_rules = self._split_rules_by_priority(rules)
        (
            hard_rules_compliant,
            hard_point_total,
            hard_rules_satisfied_list,
        ) = self._evaluate_hard_rules(room, demanda, hard_rules)
        breakdown.hard_rules_compliant = hard_rules_compliant
        breakdown.hard_rules_points = hard_point_total
        breakdown.hard_rules_satisfied = hard_rules_satisfied_list

        # 3. Soft rules and professor preferences.
        soft_point_total = 0
        soft_preferences_satisfied_list = []

        if hard_rules_compliant:
            soft_rule_points, soft_rule_matches = self._evaluate_soft_rules(
                room, demanda, soft_rules
            )
            soft_point_total += soft_rule_points
            soft_preferences_satisfied_list.extend(soft_rule_matches)

            # Room preferences
            prof_room_prefs = professor_prefs.get("preferred_rooms", [])
            if room.id in prof_room_prefs:
                soft_point_total += SCORING_WEIGHTS.PREFERRED_ROOM
                soft_preferences_satisfied_list.append("Sala preferida pelo professor")

            # Characteristic preferences
            prof_char_prefs = professor_prefs.get("preferred_characteristics", [])
            room_chars = self._get_room_characteristics(room.id)
            for char_id in prof_char_prefs:
                if char_id in room_chars:
                    char_name = self._get_characteristic_name(char_id)
                    soft_point_total += SCORING_WEIGHTS.PREFERRED_CHARACTERISTIC
                    soft_preferences_satisfied_list.append(
                        f"Característica preferida: {char_name}"
                    )
                    break  # Only one characteristic match needed

        breakdown.soft_preference_points = soft_point_total
        breakdown.soft_preferences_satisfied = soft_preferences_satisfied_list

        # 4. Historical frequency bonus - PER DAY (key difference!)
        # This is where hybrid disciplines naturally get different scores per day
        historical_freq = self._calculate_historical_frequency_bonus_per_day(
            demanda.codigo_disciplina,
            room.id,
            block_group.day_id,  # Day-specific!
            semester_id,
        )
        breakdown.historical_frequency_points = historical_freq
        breakdown.historical_allocations = (
            historical_freq // SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION
            if SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION > 0
            else 0
        )

        # 5. Hybrid discipline bonus - NEW!
        # Apply bonus when room type matches historical pattern for this day
        hybrid_bonus = self._calculate_hybrid_bonus(
            demanda.codigo_disciplina,
            room,
            block_group.day_id,
        )
        breakdown.hybrid_bonus_points = hybrid_bonus
        breakdown.hybrid_room_type_match = hybrid_bonus > 0

        breakdown.discipline_continuity_points = self._calculate_continuity_bonus(
            room, continuity_context
        )
        breakdown.professor_anchor_points = self._calculate_professor_anchor_bonus(
            room, continuity_context
        )
        breakdown.future_coverage_points = self._calculate_future_day_coverage_bonus(
            room, continuity_context
        )
        breakdown.fragmentation_penalty = self._calculate_fragmentation_penalty(
            room, continuity_context
        )

        # Calculate total
        breakdown.total_score = (
            breakdown.capacity_points
            + breakdown.hard_rules_points
            + breakdown.soft_preference_points
            + breakdown.historical_frequency_points
            + breakdown.hybrid_bonus_points
            + breakdown.discipline_continuity_points
            + breakdown.professor_anchor_points
            + breakdown.future_coverage_points
            - breakdown.fragmentation_penalty
        )

        return breakdown

    def _calculate_hybrid_bonus(
        self,
        codigo_disciplina: str,
        room: Sala,
        day_id: int,
    ) -> int:
        """
        Calculate hybrid discipline bonus for room type matching.

        For hybrid disciplines (detected in Phase 0), this applies bonus points when:
        - Room is a lab/specialized room AND day is a historical lab day
        - Room is a regular classroom AND day is a historical classroom-only day

        Args:
            codigo_disciplina: Discipline code
            room: Room to score
            day_id: Day ID (2=MON, 3=TUE, etc.)

        Returns:
            Bonus points if room type matches historical pattern, 0 otherwise
        """
        # Check if hybrid detection service is available
        if self._hybrid_detection_service is None:
            return 0

        # Check if this discipline is hybrid
        if not self._hybrid_detection_service.is_hybrid(codigo_disciplina):
            return 0

        # Get hybrid info
        hybrid_info = self._hybrid_detection_service.get_hybrid_info(codigo_disciplina)
        if not hybrid_info:
            return 0

        # Regular classroom type ID (Sala de Aula = 2)
        REGULAR_CLASSROOM_TYPE_ID = 2

        is_lab_room = room.tipo_sala_id != REGULAR_CLASSROOM_TYPE_ID
        is_lab_day = day_id in hybrid_info.lab_days
        is_classroom_day = day_id in hybrid_info.classroom_days

        # Apply bonus if room type matches the historical pattern for this day
        if is_lab_day and is_lab_room:
            # Lab room on a lab day - perfect match!
            logger.debug(
                f"Hybrid bonus for {codigo_disciplina}: lab room {room.nome} on lab day {day_id}"
            )
            return SCORING_WEIGHTS.HYBRID_ROOM_TYPE_MATCH

        if is_classroom_day and not is_lab_room:
            # Regular classroom on a classroom-only day - perfect match!
            logger.debug(
                f"Hybrid bonus for {codigo_disciplina}: classroom {room.nome} on classroom day {day_id}"
            )
            return SCORING_WEIGHTS.HYBRID_ROOM_TYPE_MATCH

        # No match - could be lab room on classroom day or vice versa
        return 0

    def _check_block_group_conflicts(
        self,
        sala_id: int,
        block_group: BlockGroup,
        semester_id: int,
        conflict_map: Optional[Dict[Tuple[int, int, str], bool]] = None,
    ) -> List[str]:
        """
        Check for conflicts for a specific block group.

        Args:
            sala_id: Room ID
            block_group: Block group to check
            semester_id: Semester to check conflicts within

        Returns:
            List of conflict descriptions (empty if no conflicts)
        """
        if conflict_map is None:
            conflict_map = self._build_conflict_lookup(
                [sala_id],
                block_group.get_atomic_tuples(),
                semester_id,
            )

        return self._collect_block_group_conflicts_from_lookup(
            sala_id,
            block_group,
            conflict_map,
        )

    def _get_building_name(self, predio_id: int) -> str:
        """Get building name by ID."""
        if not predio_id:
            return "N/A"
        stmt = text("SELECT nome FROM predios WHERE id = :pid")
        row = self.session.execute(stmt, {"pid": predio_id}).fetchone()
        return row[0] if row else "N/A"

    def _calculate_advanced_compatibility_score(
        self, room: Sala, demanda, hard_rules: List, professor_prefs: Dict
    ) -> CompatibilityScore:
        """
        Calculate advanced compatibility score (extracted from autonomous allocation).

        Includes capacity, hard rules, and professor preferences.
        """
        score = CompatibilityScore()
        violations = []

        # 1. Capacity check (basic requirement)
        if room.capacidade and room.capacidade >= demanda.vagas_disciplina:
            score.meets_capacity = True
            score.total_score += SCORING_WEIGHTS.CAPACITY_ADEQUATE

        # 2. Hard rules compliance (highest priority: 4 points each)
        hard_compliant = True
        for rule in hard_rules:
            if rule.prioridade == 0:  # Hard rule
                compliance = self._check_rule_compliance(room, demanda, rule)
                if not compliance:
                    hard_compliant = False
                    violations.append(f"Regra rígida violada: {rule.descricao}")
                else:
                    score.total_score += SCORING_WEIGHTS.HARD_RULE_COMPLIANCE

        score.hard_rules_compliant = hard_compliant

        # No need to check soft rules if hard rules fail
        if not hard_compliant:
            score.rule_violations = violations
            return score

        # 3. Professor preferences (2 points each category)
        soft_score = 0

        # Room preferences
        prof_room_prefs = professor_prefs.get("preferred_rooms", [])
        if room.id in prof_room_prefs:
            soft_score += SCORING_WEIGHTS.PREFERRED_ROOM
            score.soft_preferences_compliant = True

        # Characteristic preferences
        prof_char_prefs = professor_prefs.get("preferred_characteristics", [])
        room_chars = self._get_room_characteristics(room.id)
        for char_id in prof_char_prefs:
            if char_id in room_chars:
                soft_score += SCORING_WEIGHTS.PREFERRED_CHARACTERISTIC
                score.soft_preferences_compliant = True
                break

        score.total_score += soft_score
        score.rule_violations = violations

        return score

    def _calculate_detailed_scoring_breakdown(
        self,
        room: Sala,
        demanda,
        rules: List,
        professor_prefs: Dict,
        semester_id: int,
        continuity_context: Optional[ContinuityScoringContext] = None,
    ) -> ScoringBreakdown:
        """
        Calculate detailed scoring breakdown with full transparency.

        This provides a complete explanation of how each room scored,
        suitable for display in the UI.
        """
        breakdown = ScoringBreakdown()

        # 1. Capacity check (+1 point)
        if room.capacidade and room.capacidade >= demanda.vagas_disciplina:
            breakdown.capacity_points = SCORING_WEIGHTS.CAPACITY_ADEQUATE
            breakdown.capacity_satisfied = True
        else:
            breakdown.capacity_points = 0
            breakdown.capacity_satisfied = False

        hard_rules, soft_rules = self._split_rules_by_priority(rules)
        (
            hard_rules_compliant,
            hard_point_total,
            hard_rules_satisfied_list,
        ) = self._evaluate_hard_rules(room, demanda, hard_rules)
        breakdown.hard_rules_compliant = hard_rules_compliant
        breakdown.hard_rules_points = hard_point_total
        breakdown.hard_rules_satisfied = hard_rules_satisfied_list

        # 3. Soft rules and professor preferences.
        soft_point_total = 0
        soft_preferences_satisfied_list = []

        if hard_rules_compliant:
            soft_rule_points, soft_rule_matches = self._evaluate_soft_rules(
                room, demanda, soft_rules
            )
            soft_point_total += soft_rule_points
            soft_preferences_satisfied_list.extend(soft_rule_matches)

            # Room preferences
            prof_room_prefs = professor_prefs.get("preferred_rooms", [])
            if room.id in prof_room_prefs:
                soft_point_total += SCORING_WEIGHTS.PREFERRED_ROOM
                soft_preferences_satisfied_list.append("Sala preferida pelo professor")

            # Characteristic preferences
            prof_char_prefs = professor_prefs.get("preferred_characteristics", [])
            room_chars = self._get_room_characteristics(room.id)
            for char_id in prof_char_prefs:
                if char_id in room_chars:
                    char_name = self._get_characteristic_name(char_id)
                    soft_point_total += SCORING_WEIGHTS.PREFERRED_CHARACTERISTIC
                    soft_preferences_satisfied_list.append(
                        f"Característica preferida: {char_name}"
                    )
                    break  # Only one characteristic match needed

        breakdown.soft_preference_points = soft_point_total
        breakdown.soft_preferences_satisfied = soft_preferences_satisfied_list

        # 4. Historical frequency bonus (capped to prevent overwhelming other factors)
        historical_freq = self._calculate_historical_frequency_bonus(
            demanda.codigo_disciplina, room.id, semester_id
        )
        # Cap historical frequency points at maximum configured value
        # Note: historical_freq is already in POINTS (frequency × weight), not count
        breakdown.historical_frequency_points = min(
            historical_freq, SCORING_WEIGHTS.HISTORICAL_FREQUENCY_MAX_CAP
        )
        # Store actual frequency count for display (divide by weight to get count)
        breakdown.historical_allocations = (
            historical_freq // SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION
            if SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION > 0
            else 0
        )

        breakdown.discipline_continuity_points = self._calculate_continuity_bonus(
            room, continuity_context
        )
        breakdown.professor_anchor_points = self._calculate_professor_anchor_bonus(
            room, continuity_context
        )
        breakdown.future_coverage_points = self._calculate_future_day_coverage_bonus(
            room, continuity_context
        )
        breakdown.fragmentation_penalty = self._calculate_fragmentation_penalty(
            room, continuity_context
        )

        # Calculate total
        breakdown.total_score = (
            breakdown.capacity_points
            + breakdown.hard_rules_points
            + breakdown.soft_preference_points
            + breakdown.historical_frequency_points
            + breakdown.discipline_continuity_points
            + breakdown.professor_anchor_points
            + breakdown.future_coverage_points
            - breakdown.fragmentation_penalty
        )

        return breakdown

    def _calculate_continuity_bonus(
        self,
        room: Sala,
        continuity_context: Optional[ContinuityScoringContext],
    ) -> int:
        """Reward reusing a room already associated with the same discipline."""
        if continuity_context is None:
            return 0
        return (
            SCORING_WEIGHTS.DISCIPLINE_EXISTING_ROOM_BONUS
            if room.id in continuity_context.discipline_existing_room_ids
            else 0
        )

    def _calculate_professor_anchor_bonus(
        self,
        room: Sala,
        continuity_context: Optional[ContinuityScoringContext],
    ) -> int:
        """Reward matching the current professor anchor context."""
        if continuity_context is None:
            return 0

        bonus = 0
        if continuity_context.professor_anchor_room_id == room.id:
            bonus += SCORING_WEIGHTS.PROFESSOR_ANCHOR_ROOM_BONUS
        if (
            continuity_context.professor_anchor_building_id is not None
            and continuity_context.professor_anchor_building_id == room.predio_id
        ):
            bonus += SCORING_WEIGHTS.PROFESSOR_ANCHOR_BUILDING_BONUS
        if (
            continuity_context.professor_anchor_room_type_id is not None
            and continuity_context.professor_anchor_room_type_id == room.tipo_sala_id
        ):
            bonus += SCORING_WEIGHTS.PROFESSOR_ANCHOR_ROOM_TYPE_BONUS
        return bonus

    def _calculate_future_day_coverage_bonus(
        self,
        room: Sala,
        continuity_context: Optional[ContinuityScoringContext],
    ) -> int:
        """Reward rooms that can likely absorb more pending day-groups later."""
        if continuity_context is None:
            return 0

        coverage_count = continuity_context.future_day_coverage_by_room_id.get(
            room.id,
            continuity_context.future_day_coverage_count,
        )
        return max(coverage_count, 0) * SCORING_WEIGHTS.FUTURE_DAY_COVERAGE_PER_DAY

    def _calculate_fragmentation_penalty(
        self,
        room: Sala,
        continuity_context: Optional[ContinuityScoringContext],
    ) -> int:
        """Penalize opening a new room for a non-hybrid discipline already in progress."""
        if continuity_context is None:
            return 0
        if continuity_context.is_hybrid:
            return 0
        if not continuity_context.discipline_existing_room_ids:
            return 0
        if room.id in continuity_context.discipline_existing_room_ids:
            return 0
        return SCORING_WEIGHTS.NON_HYBRID_FRAGMENTATION_PENALTY

    def _check_atomic_block_conflicts(
        self,
        sala_id: int,
        atomic_blocks: List[tuple[str, int]],
        semester_id: int,
        conflict_map: Optional[Dict[Tuple[int, int, str], bool]] = None,
    ) -> List[Dict]:
        """Check conflicts for an arbitrary list of atomic blocks."""
        if conflict_map is None:
            conflict_map = self._build_conflict_lookup(
                [sala_id],
                atomic_blocks,
                semester_id,
            )
        return self._collect_atomic_conflicts_from_lookup(
            sala_id,
            atomic_blocks,
            conflict_map,
        )

    def _check_rule_compliance(self, room, demanda, rule) -> bool:
        """Check if room complies with a specific rule."""
        import json

        try:
            config = json.loads(rule.config_json)

            if rule.tipo_regra == "DISCIPLINA_TIPO_SALA":
                required_type_id = config.get("tipo_sala_id")
                result = room.tipo_sala_id == required_type_id
                logger.debug(
                    f"Rule check DISCIPLINA_TIPO_SALA: {rule.descricao} | "
                    f"Room {room.nome} tipo_sala_id={room.tipo_sala_id} | "
                    f"Required tipo_sala_id={required_type_id} | "
                    f"Match: {result}"
                )
                return result

            elif rule.tipo_regra == "DISCIPLINA_SALA":
                required_room_id = config.get("sala_id")
                result = room.id == required_room_id
                logger.debug(
                    f"Rule check DISCIPLINA_SALA: {rule.descricao} | "
                    f"Room id={room.id} | Required room_id={required_room_id} | "
                    f"Match: {result}"
                )
                return result

            elif rule.tipo_regra == "DISCIPLINA_CARACTERISTICA":
                required_char = config.get("caracteristica_nome")
                room_chars = self._get_room_characteristics(room.id)
                char_names = [self._get_characteristic_name(cid) for cid in room_chars]
                result = required_char in char_names
                logger.debug(
                    f"Rule check DISCIPLINA_CARACTERISTICA: {rule.descricao} | "
                    f"Room {room.nome} chars={char_names} | "
                    f"Required char={required_char} | "
                    f"Match: {result}"
                )
                return result

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(
                f"Rule compliance check failed for {rule.descricao}: {e} | "
                f"config_json={rule.config_json}"
            )
            return False

        logger.warning(
            f"Unknown rule type: {rule.tipo_regra} for rule {rule.descricao}"
        )
        return False

    def _check_allocation_conflicts_semester_isolated(
        self,
        candidate: RoomCandidate,
        semester_id: int,
        conflict_map: Optional[Dict[Tuple[int, int, str], bool]] = None,
    ) -> List[Dict]:
        """
        Check for conflicts within a specific semester only (not cross-semester).
        """
        if conflict_map is None:
            conflict_map = self._build_conflict_lookup(
                [candidate.sala.id],
                candidate.atomic_blocks,
                semester_id,
            )

        return self._collect_atomic_conflicts_from_lookup(
            candidate.sala.id,
            candidate.atomic_blocks,
            conflict_map,
        )

    def _get_professor_preferences_for_professor(
        self, professor: Optional[Professor]
    ) -> Dict:
        """Get professor preferences dict from Professor object."""
        prefs = {"preferred_rooms": [], "preferred_characteristics": []}

        if not professor:
            return prefs

        cached = self._professor_preferences_cache.get(professor.id)
        if cached is not None:
            return cached

        # Get room preferences
        stmt = text(
            "SELECT sala_id FROM professor_prefere_sala WHERE professor_id = :prof_id"
        )
        room_prefs = [
            row[0]
            for row in self.session.execute(stmt, {"prof_id": professor.id}).fetchall()
        ]
        prefs["preferred_rooms"].extend(room_prefs)

        # Get characteristic preferences
        stmt = text(
            "SELECT caracteristica_id FROM professor_prefere_caracteristica WHERE professor_id = :prof_id"
        )
        char_prefs = [
            row[0]
            for row in self.session.execute(stmt, {"prof_id": professor.id}).fetchall()
        ]
        prefs["preferred_characteristics"].extend(char_prefs)

        self._professor_preferences_cache[professor.id] = prefs
        return prefs

    def _calculate_historical_frequency_bonus(
        self, disciplina_codigo: str, sala_id: int, exclude_semester_id: int
    ) -> int:
        """
        Calculate historical frequency bonus (RF-006.6) - LEGACY METHOD.

        Returns bonus points based on how many times this discipline has been
        allocated to this room in previous semesters (any day).

        The result is capped at HISTORICAL_FREQUENCY_MAX_CAP points (not allocations).

        Note: This method is kept for backward compatibility. For per-day scoring,
        use _calculate_historical_frequency_bonus_per_day() instead.

        Returns:
            Historical frequency points (already capped at MAX_CAP value)
        """
        cache_key = (disciplina_codigo, sala_id, exclude_semester_id)
        cached = self._historical_frequency_cache.get(cache_key)
        if cached is not None:
            return cached

        # Use existing repository method to get frequency count
        frequency = self.alocacao_repo.get_discipline_room_frequency(
            disciplina_codigo, sala_id, exclude_semester_id
        )

        # Calculate points: frequency (count) × weight (points per allocation)
        historical_points = (
            frequency * SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION
        )

        # Cap at maximum POINTS (not maximum allocations)
        result = min(historical_points, SCORING_WEIGHTS.HISTORICAL_FREQUENCY_MAX_CAP)
        self._historical_frequency_cache[cache_key] = result
        return result

    def _calculate_historical_frequency_bonus_per_day(
        self,
        disciplina_codigo: str,
        sala_id: int,
        dia_semana_id: int,
        exclude_semester_id: int,
    ) -> int:
        """
        Calculate historical frequency bonus per day (Enhanced RF-006.6).

        Returns bonus points based on how many times this discipline has been
        allocated to this room ON THIS SPECIFIC DAY in previous semesters.

        This enables hybrid disciplines to get different scores for different days,
        naturally leading to split allocation when historical data shows different
        rooms were used on different days.

        Args:
            disciplina_codigo: Discipline code
            sala_id: Room ID
            dia_semana_id: Day of week ID (2=MON, 3=TUE, ..., 7=SAT)
            exclude_semester_id: Semester ID to exclude (current semester)

        Returns:
            Historical frequency points for this day (capped at MAX_CAP value)
        """
        cache_key = (disciplina_codigo, sala_id, dia_semana_id, exclude_semester_id)
        cached = self._historical_frequency_day_cache.get(cache_key)
        if cached is not None:
            return cached

        # Use new repository method to get day-specific frequency count
        frequency = self.alocacao_repo.get_discipline_room_day_frequency(
            disciplina_codigo, sala_id, dia_semana_id, exclude_semester_id
        )

        # Calculate points: frequency (count) × weight (points per allocation)
        historical_points = (
            frequency * SCORING_WEIGHTS.HISTORICAL_FREQUENCY_PER_ALLOCATION
        )

        # Cap at maximum POINTS (not maximum allocations)
        result = min(historical_points, SCORING_WEIGHTS.HISTORICAL_FREQUENCY_MAX_CAP)
        self._historical_frequency_day_cache[cache_key] = result
        return result

    def _lookup_professors_for_demands_from_objects(
        self, demands
    ) -> Dict[int, Optional[Professor]]:
        """Lookup professors for demand objects."""
        professor_map = {}

        for demanda in demands:
            demanda_id = demanda.id
            prof_text = demanda.professores_disciplina.strip()

            if prof_text:
                # Support multiple professors (take first match)
                prof_names = [name.strip() for name in prof_text.split(",")]
                professor = None

                for prof_name in prof_names:
                    if prof_name not in self._professor_lookup_cache:
                        self._professor_lookup_cache[prof_name] = (
                            self.prof_repo.get_by_nome_completo(prof_name)
                        )
                    professor = self._professor_lookup_cache[prof_name]
                    if professor:
                        break

                professor_map[demanda_id] = professor

        return professor_map

    def _get_room_characteristics(self, sala_id: int):
        """Get characteristic IDs for a room."""
        cached = self._room_characteristics_cache.get(sala_id)
        if cached is not None:
            return cached

        stmt = text(
            "SELECT caracteristica_id FROM sala_caracteristicas WHERE sala_id = :sala_id"
        )
        rows = self.session.execute(stmt, {"sala_id": sala_id}).fetchall()
        characteristics = {row[0] for row in rows}
        self._room_characteristics_cache[sala_id] = characteristics
        return characteristics

    def _get_characteristic_name(self, caracteristica_id: int) -> str:
        """Get characteristic name by ID."""
        cached = self._characteristic_name_cache.get(caracteristica_id)
        if cached is not None:
            return cached

        stmt = text("SELECT nome FROM caracteristicas WHERE id = :cid")
        row = self.session.execute(stmt, {"cid": caracteristica_id}).fetchone()
        name = row[0] if row else ""
        self._characteristic_name_cache[caracteristica_id] = name
        return name

    def _get_rule_description(self, rule) -> str:
        """Get human-readable description of a rule for UI display."""
        import json

        try:
            config = json.loads(rule.config_json)

            if rule.tipo_regra == "DISCIPLINA_TIPO_SALA":
                tipo_sala_name = self._get_room_type_name_by_id(
                    config.get("tipo_sala_id")
                )
                return f"Tipo de sala: {tipo_sala_name}"

            elif rule.tipo_regra == "DISCIPLINA_SALA":
                sala_id = config.get("sala_id")
                sala_name = self._get_room_name_by_id(sala_id)
                return f"Sala específica: {sala_name}"

            elif rule.tipo_regra == "DISCIPLINA_CARACTERISTICA":
                char_name = config.get("caracteristica_nome")
                return f"Característica: {char_name}"

            else:
                return f"Regra: {rule.descricao}"

        except (json.JSONDecodeError, KeyError):
            return f"Regra: {rule.descricao}"

    def _get_room_type_name_by_id(self, tipo_sala_id: int) -> str:
        """Get room type name by ID."""
        if not tipo_sala_id:
            return "N/A"
        stmt = text("SELECT nome FROM tipos_sala WHERE id = :tid")
        row = self.session.execute(stmt, {"tid": tipo_sala_id}).fetchone()
        return row[0] if row else "N/A"

    def _get_room_name_by_id(self, sala_id: int) -> str:
        """Get room name by ID."""
        if not sala_id:
            return "N/A"
        stmt = text("SELECT nome FROM salas WHERE id = :sid")
        row = self.session.execute(stmt, {"sid": sala_id}).fetchone()
        return row[0] if row else "N/A"
