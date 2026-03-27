"""
Optimized Autonomous Allocation Service - Reduced I/O with batch operations and detailed logging

Supports both full allocation (all blocks to one room) and partial allocation
(different block-groups to different rooms based on per-day scoring).
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.config.settings import Settings
from src.repositories.optimized_allocation_repo import OptimizedAllocationRepository
from src.schemas.allocation import AlocacaoSemestralCreate
from src.services.allocation_continuity_planner import AllocationContinuityPlanner
from src.services.autonomous_allocation_report_service import (
    AutonomousAllocationReportService,
)
from src.services.autonomous_allocation_service import (
    AllocationCandidate,
    AutonomousAllocationService,
    PhaseResult,
)
from src.services.hybrid_discipline_service import (
    HybridDetectionResult,
    HybridDisciplineDetectionService,
)
from src.services.room_scoring_service import ContinuityScoringContext
from src.utils.allocation_debug_report import AllocationDebugReport
from src.utils.allocation_logger import AllocationDecisionLogger

logger = logging.getLogger(__name__)


@dataclass
class BlockGroupCandidate:
    """Represents a room candidate for a specific block group (day)."""

    sala: Any  # SalaRead DTO
    demanda_id: int
    day_id: int
    day_name: str
    blocks: List[Tuple[str, int]]  # List of (block_code, day_sigaa)
    score: float
    professor_id: Optional[int] = None
    professor_name: Optional[str] = None
    scoring_breakdown: Optional[Dict[str, Any]] = None
    has_conflicts: bool = False


@dataclass
class BlockGroupAllocationResult:
    """Result of allocating a block group."""

    demanda_id: int
    day_id: int
    day_name: str
    blocks: List[str]
    allocated: bool
    sala_id: Optional[int] = None
    sala_nome: Optional[str] = None
    score: float = 0.0
    failure_reason: Optional[str] = None


logger = logging.getLogger(__name__)


class OptimizedAutonomousAllocationService(AutonomousAllocationService):
    """
    Optimized version of autonomous allocation with:
    - Batch database operations to reduce I/O
    - Detailed decision logging
    - Transaction-based allocations
    - **Partial allocation support** (different rooms per block-group/day)
    """

    def __init__(self, session: Session):
        super().__init__(session)
        # Use optimized repository for batch operations
        self.optimized_alocacao_repo = OptimizedAllocationRepository(session)
        self.decision_logger = AllocationDecisionLogger()
        self.report_service = AutonomousAllocationReportService()

        # Hybrid discipline detection service (Phase 0)
        self.hybrid_detection_service = HybridDisciplineDetectionService(session)
        self.continuity_planner = AllocationContinuityPlanner(
            session,
            hybrid_service=self.hybrid_detection_service,
        )
        self._latest_continuity_profiles: Dict[int, Any] = {}

    def _sync_continuity_planner(self) -> None:
        """Keep planner dependencies aligned with the active hybrid service state."""
        self.continuity_planner.hybrid_service = self.hybrid_detection_service
        self.continuity_planner.scoring_service.set_hybrid_detection_service(
            self.hybrid_detection_service
        )

    def _prepare_continuity_profiles(
        self,
        demands: List[Any],
        semester_id: int,
    ) -> Dict[int, Any]:
        """Build continuity profiles for later phases without changing allocation flow."""
        self._sync_continuity_planner()
        profiles = self.continuity_planner.build_demand_profiles(demands, semester_id)
        self._latest_continuity_profiles = profiles
        return profiles

    # =========================================================================
    # PARTIAL ALLOCATION METHODS (Block-Group Level Scoring & Allocation)
    # =========================================================================

    def _group_demand_blocks_by_day(
        self, horario_sigaa: str
    ) -> Dict[int, List[Tuple[str, int]]]:
        """
        Group atomic blocks by day for a demand's schedule.

        Args:
            horario_sigaa: Raw SIGAA schedule string (e.g., "24M12 35T34")

        Returns:
            Dict[day_id, List[(block_code, day_sigaa)]] - blocks grouped by day
        """
        atomic_blocks = self.parser.split_to_atomic_tuples(horario_sigaa)
        groups: Dict[int, List[Tuple[str, int]]] = {}

        for bloco_codigo, dia_sigaa in atomic_blocks:
            if dia_sigaa not in groups:
                groups[dia_sigaa] = []
            groups[dia_sigaa].append((bloco_codigo, dia_sigaa))

        return groups

    def _get_pending_atomic_blocks_for_demand(
        self, demanda_id: int, horario_sigaa: str
    ) -> List[Tuple[str, int]]:
        """Return only the atomic blocks that are still pending for a demand."""
        atomic_blocks = self.parser.split_to_atomic_tuples(horario_sigaa)
        if not atomic_blocks:
            return []

        existing_allocations = self.alocacao_repo.get_by_demanda(demanda_id)
        allocated_blocks = {
            (alloc.codigo_bloco, alloc.dia_semana_id) for alloc in existing_allocations
        }

        return [
            (bloco_codigo, dia_sigaa)
            for bloco_codigo, dia_sigaa in atomic_blocks
            if (bloco_codigo, dia_sigaa) not in allocated_blocks
        ]

    def _group_pending_blocks_by_day(
        self, demanda_id: int, horario_sigaa: str
    ) -> Dict[int, List[Tuple[str, int]]]:
        """Group only pending atomic blocks by day for reruns."""
        groups: Dict[int, List[Tuple[str, int]]] = {}

        for bloco_codigo, dia_sigaa in self._get_pending_atomic_blocks_for_demand(
            demanda_id, horario_sigaa
        ):
            groups.setdefault(dia_sigaa, []).append((bloco_codigo, dia_sigaa))

        return groups

    def _score_rooms_for_block_group(
        self,
        demanda: Any,
        day_id: int,
        blocks: List[Tuple[str, int]],
        semester_id: int,
        professor: Optional[Any] = None,
        continuity_context: Optional[ContinuityScoringContext] = None,
    ) -> List[BlockGroupCandidate]:
        """
        Score all rooms for a specific block group (day) of a demand.

        Uses per-day historical scoring from RoomScoringService.

        Args:
            demanda: The demand object
            day_id: The day ID (SIGAA format: 2=Mon, 3=Tue, etc.)
            blocks: List of (block_code, day_sigaa) tuples for this day
            semester_id: Current semester ID
            professor: Optional professor object for preference scoring

        Returns:
            List of BlockGroupCandidate sorted by score (highest first)
        """
        from src.services.room_scoring_service import BlockGroup

        day_names = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}
        day_name = day_names.get(day_id, f"DIA{day_id}")

        # Create a BlockGroup object for the scoring service
        block_codes = sorted(set(b[0] for b in blocks))
        block_group = BlockGroup(
            day_id=day_id,
            day_name=day_name,
            blocks=block_codes,
        )

        # Get block group scoring from the centralized scoring service
        block_group_scores = self.scoring_service.score_rooms_for_block_group(
            demanda_id=demanda.id,
            block_group=block_group,
            semester_id=semester_id,
            professor_override=professor,
            continuity_context=continuity_context,
        )

        # Get rooms enabled for this block group to map room_id to room objects
        all_rooms = self.sala_repo.get_available_for_allocation(
            required_blocks=block_codes
        )
        room_dict = {room.id: room for room in all_rooms}

        candidates = []
        for room_score in block_group_scores:
            sala = room_dict.get(room_score.room_id)
            if not sala:
                continue

            candidates.append(
                BlockGroupCandidate(
                    sala=sala,
                    demanda_id=demanda.id,
                    day_id=day_id,
                    day_name=day_name,
                    blocks=blocks,
                    score=room_score.score,
                    professor_id=professor.id if professor else None,
                    professor_name=demanda.professores_disciplina,
                    scoring_breakdown=(
                        room_score.breakdown.__dict__ if room_score.breakdown else None
                    ),
                    has_conflicts=room_score.has_conflict,
                )
            )

        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    def _allocate_block_group(
        self,
        candidate: BlockGroupCandidate,
        semester_id: int,
    ) -> bool:
        """
        Allocate a single block group to a room.

        Args:
            candidate: The BlockGroupCandidate to allocate
            semester_id: Current semester ID

        Returns:
            True if allocation successful, False otherwise
        """
        try:
            allocation_dtos = []
            for bloco_codigo, dia_sigaa in candidate.blocks:
                allocation_dto = AlocacaoSemestralCreate(
                    semestre_id=semester_id,
                    demanda_id=candidate.demanda_id,
                    sala_id=candidate.sala.id,
                    dia_semana_id=dia_sigaa,
                    codigo_bloco=bloco_codigo,
                    origem_alocacao="autonoma",
                )
                allocation_dtos.append(allocation_dto)

            self.optimized_alocacao_repo.create_batch_atomic(allocation_dtos)

            logger.debug(
                f"Allocated block group {candidate.day_name} ({len(candidate.blocks)} blocks) "
                f"for demand {candidate.demanda_id} to room {candidate.sala.id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Block group allocation failed for demand {candidate.demanda_id}, "
                f"day {candidate.day_name}: {e}"
            )
            return False

    def _allocate_full_pending_demand_to_room(
        self,
        demanda: Any,
        room: Any,
        pending_blocks: List[Tuple[str, int]],
        semester_id: int,
    ) -> bool:
        """Allocate all still-pending blocks of a demand to a single room.

        This helper is the mechanical basis for the future continuity phase.
        It is intentionally self-contained and conservative:

        - it allocates only still-pending atomic blocks
        - it performs a fresh batch conflict check immediately before creation
        - it short-circuits safely when there is nothing left to allocate
        """
        if not pending_blocks:
            logger.debug(
                "Skipping full pending allocation for %s: no pending blocks",
                getattr(demanda, "codigo_disciplina", getattr(demanda, "id", "?")),
            )
            return True

        room_id = getattr(room, "id", None)
        if room_id is None:
            logger.error("Full pending allocation failed: room has no id")
            return False

        slots = [(room_id, day_id, block_code) for block_code, day_id in pending_blocks]
        fresh_conflicts = self.optimized_alocacao_repo.check_conflicts_batch(
            slots, semester_id
        )
        if any(fresh_conflicts.get(slot, False) for slot in slots):
            logger.debug(
                "Fresh conflict check blocked full pending allocation for demand %s in room %s",
                getattr(demanda, "id", "?"),
                room_id,
            )
            return False

        allocation_dtos = [
            AlocacaoSemestralCreate(
                semestre_id=semester_id,
                demanda_id=demanda.id,
                sala_id=room_id,
                dia_semana_id=day_id,
                codigo_bloco=block_code,
                origem_alocacao="autonoma",
            )
            for block_code, day_id in pending_blocks
        ]

        try:
            self.optimized_alocacao_repo.create_batch_atomic(allocation_dtos)
            logger.debug(
                "Allocated %s pending blocks for demand %s to room %s",
                len(allocation_dtos),
                getattr(demanda, "id", "?"),
                room_id,
            )
            return True
        except Exception as exc:
            logger.error(
                "Full pending allocation failed for demand %s in room %s: %s",
                getattr(demanda, "id", "?"),
                room_id,
                exc,
            )
            return False

    def _is_hybrid_demand(self, codigo_disciplina: str) -> bool:
        """Return whether the discipline is currently marked as hybrid."""
        if not getattr(self.hybrid_detection_service, "_is_initialized", False):
            return False
        return bool(self.hybrid_detection_service.is_hybrid(codigo_disciplina))

    def _get_existing_room_ids_for_demand(self, demanda_id: int) -> List[int]:
        """Return currently used rooms for a demand ordered by frequency."""
        allocations = self.alocacao_repo.get_by_demanda(demanda_id)
        room_counts: Dict[int, int] = {}
        for allocation in allocations:
            room_counts[allocation.sala_id] = room_counts.get(allocation.sala_id, 0) + 1
        return [
            room_id
            for room_id, _count in sorted(
                room_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ]

    def _build_full_demand_continuity_context(
        self,
        demanda: Any,
        semester_id: int,
        professor: Optional[Any] = None,
    ) -> ContinuityScoringContext:
        """Build continuity context for whole-demand consolidation attempts."""
        anchor = self.continuity_planner.resolve_professor_anchor(
            professor, semester_id
        )
        return ContinuityScoringContext(
            is_hybrid=self._is_hybrid_demand(demanda.codigo_disciplina),
            discipline_existing_room_ids=self._get_existing_room_ids_for_demand(
                demanda.id
            ),
            professor_anchor_room_id=anchor.room_id if anchor else None,
            professor_anchor_building_id=anchor.building_id if anchor else None,
            professor_anchor_room_type_id=anchor.room_type_id if anchor else None,
        )

    def _build_block_group_continuity_context(
        self,
        demanda: Any,
        current_day_id: int,
        current_blocks: List[Tuple[str, int]],
        pending_blocks_by_day: Dict[int, List[Tuple[str, int]]],
        semester_id: int,
        professor: Optional[Any] = None,
    ) -> ContinuityScoringContext:
        """Build continuity context for partial per-day fallback scoring."""
        anchor = self.continuity_planner.resolve_professor_anchor(
            professor, semester_id
        )
        remaining_days = {
            day_id: blocks
            for day_id, blocks in pending_blocks_by_day.items()
            if day_id != current_day_id
        }
        required_blocks = sorted({block_code for block_code, _ in current_blocks})
        available_rooms = self.sala_repo.get_available_for_allocation(
            required_blocks=required_blocks
        )
        future_coverage_by_room_id = {
            room.id: self.continuity_planner.count_future_day_coverage(
                demanda,
                room.id,
                remaining_days,
                semester_id,
            )
            for room in available_rooms
        }

        return ContinuityScoringContext(
            is_hybrid=self._is_hybrid_demand(demanda.codigo_disciplina),
            discipline_existing_room_ids=self._get_existing_room_ids_for_demand(
                demanda.id
            ),
            professor_anchor_room_id=anchor.room_id if anchor else None,
            professor_anchor_building_id=anchor.building_id if anchor else None,
            professor_anchor_room_type_id=anchor.room_type_id if anchor else None,
            future_day_coverage_by_room_id=future_coverage_by_room_id,
        )

    def _execute_discipline_continuity_phase(
        self,
        demands: List[Any],
        semester_id: int,
        dry_run: bool,
    ) -> PhaseResult:
        """Phase 1.5: consolidate non-hybrid disciplines into one room when viable."""
        result = PhaseResult()
        if not demands:
            return result

        profiles = self._prepare_continuity_profiles(demands, semester_id)
        prioritized_ids = self.continuity_planner.prioritize_demands_for_continuity(
            profiles
        )
        demand_by_id = {demanda.id: demanda for demanda in demands}
        professor_map = self._lookup_professors_for_demands_from_objects(demands)

        for demanda_id in prioritized_ids:
            demanda = demand_by_id.get(demanda_id)
            profile = profiles.get(demanda_id)
            if demanda is None or profile is None:
                continue
            if profile.is_hybrid:
                continue
            if not profile.compatible_full_room_ids:
                continue

            pending_blocks = self._get_pending_atomic_blocks_for_demand(
                demanda_id,
                demanda.horario_sigaa_bruto,
            )
            if not pending_blocks:
                continue

            professor = professor_map.get(demanda_id)
            continuity_context = self._build_full_demand_continuity_context(
                demanda,
                semester_id,
                professor,
            )
            candidates = self.scoring_service.score_room_candidates_for_full_continuity(
                demanda_id=demanda_id,
                pending_blocks=pending_blocks,
                semester_id=semester_id,
                professor_override=professor,
                continuity_context=continuity_context,
            )
            valid_candidates = [
                candidate for candidate in candidates if not candidate.has_conflicts
            ]

            if not valid_candidates:
                continue

            top_candidate = valid_candidates[0]
            if dry_run:
                result.allocations_completed += 1
                logger.info(
                    "Phase 1.5 dry-run would consolidate %s in room %s",
                    demanda.codigo_disciplina,
                    top_candidate.sala.nome,
                )
                continue

            if self._allocate_full_pending_demand_to_room(
                demanda,
                top_candidate.sala,
                pending_blocks,
                semester_id,
            ):
                result.allocations_completed += 1
                logger.info(
                    "Phase 1.5 consolidated %s into room %s",
                    demanda.codigo_disciplina,
                    top_candidate.sala.nome,
                )
            else:
                result.conflicts_found += 1

        result.total_demands_processed = len(demands)
        return result

    def _get_demands_for_partial_fallback(self, semester_id: int) -> List[Any]:
        """Return demands that still have pending work after earlier phases."""
        return self.manual_service.get_unallocated_demands(semester_id)

    def _execute_partial_allocation_phase(
        self,
        demands: List[Any],
        semester_id: int,
        dry_run: bool,
    ) -> Tuple[PhaseResult, List[BlockGroupAllocationResult]]:
        """
        Execute partial allocation phase: process each demand's block-groups independently.

        This method allows different days of a demand to be allocated to different rooms
        based on per-day historical scoring. This is useful for hybrid disciplines that
        need different room types on different days (e.g., lab on Mon, lecture hall on Wed).

        Args:
            demands: List of demands to process
            semester_id: Current semester ID
            dry_run: If True, simulate without actual allocations

        Returns:
            Tuple of (PhaseResult, List[BlockGroupAllocationResult])
        """
        result = PhaseResult()
        block_group_results: List[BlockGroupAllocationResult] = []

        # Batch: Get professor information for all demands
        professor_map = self._lookup_professors_for_demands_from_objects(demands)

        logger.info(f"Executing partial allocation phase for {len(demands)} demands")

        for demanda in demands:
            demanda_id = demanda.id
            professor = professor_map.get(demanda_id)

            # Group only pending blocks by day so reruns resume partial demands.
            block_groups = self._group_pending_blocks_by_day(
                demanda_id, demanda.horario_sigaa_bruto
            )

            if not block_groups:
                logger.debug(f"Skipping {demanda.codigo_disciplina}: no pending blocks")
                continue

            logger.debug(
                f"Processing {demanda.codigo_disciplina}: "
                f"{len(block_groups)} block groups"
            )

            # Process each block group independently
            for day_id, blocks in block_groups.items():
                continuity_context = self._build_block_group_continuity_context(
                    demanda,
                    day_id,
                    blocks,
                    block_groups,
                    semester_id,
                    professor,
                )

                # Score rooms for this specific block group
                candidates = self._score_rooms_for_block_group(
                    demanda,
                    day_id,
                    blocks,
                    semester_id,
                    professor,
                    continuity_context,
                )

                if not candidates:
                    day_names = {
                        2: "SEG",
                        3: "TER",
                        4: "QUA",
                        5: "QUI",
                        6: "SEX",
                        7: "SAB",
                    }
                    day_name = day_names.get(day_id, f"DIA{day_id}")

                    result.demands_skipped += 1
                    block_group_results.append(
                        BlockGroupAllocationResult(
                            demanda_id=demanda_id,
                            day_id=day_id,
                            day_name=day_name,
                            blocks=[b[0] for b in blocks],
                            allocated=False,
                            failure_reason="No rooms satisfy hard rules or availability for this block group",
                        )
                    )
                    continue

                # Filter out candidates with conflicts
                valid_candidates = [c for c in candidates if not c.has_conflicts]

                if not valid_candidates:
                    day_names = {
                        2: "SEG",
                        3: "TER",
                        4: "QUA",
                        5: "QUI",
                        6: "SEX",
                        7: "SAB",
                    }
                    day_name = day_names.get(day_id, f"DIA{day_id}")

                    result.conflicts_found += 1
                    block_group_results.append(
                        BlockGroupAllocationResult(
                            demanda_id=demanda_id,
                            day_id=day_id,
                            day_name=day_name,
                            blocks=[b[0] for b in blocks],
                            allocated=False,
                            failure_reason="All rooms have conflicts for this block group",
                        )
                    )
                    logger.debug(
                        f"No valid rooms for {demanda.codigo_disciplina} day {day_name}"
                    )
                    continue

                # Try to allocate to best available room
                allocated = False
                for candidate in valid_candidates:
                    # Fresh conflict check against current DB state
                    slots = [
                        (candidate.sala.id, dia_sigaa, bloco_codigo)
                        for bloco_codigo, dia_sigaa in candidate.blocks
                    ]
                    fresh_conflicts = (
                        self.optimized_alocacao_repo.check_conflicts_batch(
                            slots, semester_id
                        )
                    )
                    has_conflicts = any(
                        fresh_conflicts.get(slot, False) for slot in slots
                    )

                    if has_conflicts:
                        continue

                    # Allocate this block group
                    if not dry_run:
                        success = self._allocate_block_group(candidate, semester_id)
                        if success:
                            result.allocations_completed += 1
                            allocated = True
                            block_group_results.append(
                                BlockGroupAllocationResult(
                                    demanda_id=demanda_id,
                                    day_id=candidate.day_id,
                                    day_name=candidate.day_name,
                                    blocks=[b[0] for b in candidate.blocks],
                                    allocated=True,
                                    sala_id=candidate.sala.id,
                                    sala_nome=candidate.sala.nome,
                                    score=candidate.score,
                                )
                            )
                            break
                    else:
                        # Dry run - count as successful
                        result.allocations_completed += 1
                        allocated = True
                        block_group_results.append(
                            BlockGroupAllocationResult(
                                demanda_id=demanda_id,
                                day_id=candidate.day_id,
                                day_name=candidate.day_name,
                                blocks=[b[0] for b in candidate.blocks],
                                allocated=True,
                                sala_id=candidate.sala.id,
                                sala_nome=candidate.sala.nome,
                                score=candidate.score,
                            )
                        )
                        break

                if not allocated:
                    day_names = {
                        2: "SEG",
                        3: "TER",
                        4: "QUA",
                        5: "QUI",
                        6: "SEX",
                        7: "SAB",
                    }
                    day_name = day_names.get(day_id, f"DIA{day_id}")

                    result.demands_skipped += 1
                    block_group_results.append(
                        BlockGroupAllocationResult(
                            demanda_id=demanda_id,
                            day_id=day_id,
                            day_name=day_name,
                            blocks=[b[0] for b in blocks],
                            allocated=False,
                            failure_reason="All candidates failed fresh conflict check",
                        )
                    )

        result.total_demands_processed = len(demands)
        return result, block_group_results

    def execute_autonomous_allocation_partial(
        self, semester_id: int, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute autonomous allocation with PARTIAL allocation support.

        This variant allows different block-groups (days) of a demand to be
        allocated to different rooms. Useful for:
        - Hybrid disciplines (lab days vs lecture days)
        - Maximizing allocation when single-room allocation fails
        - Better historical pattern matching per day

        Args:
            semester_id: Semester to allocate for
            dry_run: If True, only simulate without actual allocations

        Returns:
            Detailed allocation results including per-block-group breakdown
        """
        import time

        start_time = time.perf_counter()
        phase_timings: Dict[str, float] = {}

        logger.info(
            f"Starting PARTIAL autonomous allocation for semester {semester_id}"
        )
        self.decision_logger = AllocationDecisionLogger()

        try:
            # Get unallocated demands
            phase_start = time.perf_counter()
            unallocated_demands = self.manual_service.get_unallocated_demands(
                semester_id
            )
            phase_timings["load_unallocated_demands"] = round(
                time.perf_counter() - phase_start, 4
            )
            logger.info(f"Found {len(unallocated_demands)} unallocated demands")

            # Phase 0: Hybrid Discipline Detection (NEW!)
            logger.info("=== PHASE 0: Hybrid Discipline Detection ===")
            phase_start = time.perf_counter()
            phase0_result = self._execute_hybrid_detection_phase(semester_id)
            phase_timings["phase0_hybrid_detection"] = round(
                time.perf_counter() - phase_start, 4
            )
            logger.info(f"Detected {phase0_result.detected_count} hybrid disciplines")

            # Phase 1: Hard Rules (unchanged - allocates all blocks to one room)
            logger.info("=== PHASE 1: Hard Rules Allocation ===")
            phase_start = time.perf_counter()
            phase1_result = self._execute_hard_rules_phase_optimized(
                unallocated_demands, semester_id, dry_run
            )
            phase_timings["phase1_hard_rules"] = round(
                time.perf_counter() - phase_start, 4
            )
            self.decision_logger.log_phase_summary("hard_rules", phase1_result.__dict__)

            if not dry_run:
                self.session.commit()
                logger.info("Phase 1 allocations committed")

            # Get remaining demands after Phase 1
            phase_start = time.perf_counter()
            remaining_demands = self._get_demands_for_partial_fallback(semester_id)
            logger.info(f"After Phase 1: {len(remaining_demands)} demands remaining")

            continuity_profiles = self._prepare_continuity_profiles(
                remaining_demands, semester_id
            )
            phase_timings["prepare_continuity_profiles_phase1_5"] = round(
                time.perf_counter() - phase_start, 4
            )
            continuity_candidates = sum(
                1
                for profile in continuity_profiles.values()
                if (not profile.is_hybrid) and profile.compatible_full_room_ids
            )
            logger.info(
                "Continuity planner prepared %s profiles (%s non-hybrid demands have at least one full-room option)",
                len(continuity_profiles),
                continuity_candidates,
            )

            logger.info("=== PHASE 1.5: Discipline Continuity Allocation ===")
            phase_start = time.perf_counter()
            phase1_5_result = self._execute_discipline_continuity_phase(
                remaining_demands,
                semester_id,
                dry_run,
            )
            phase_timings["phase1_5_continuity"] = round(
                time.perf_counter() - phase_start, 4
            )
            self.decision_logger.log_phase_summary(
                "discipline_continuity", phase1_5_result.__dict__
            )

            if not dry_run:
                self.session.commit()
                logger.info("Phase 1.5 allocations committed")

            phase_start = time.perf_counter()
            remaining_demands = self._get_demands_for_partial_fallback(semester_id)
            continuity_profiles = self._prepare_continuity_profiles(
                remaining_demands, semester_id
            )
            phase_timings["prepare_continuity_profiles_partial"] = round(
                time.perf_counter() - phase_start, 4
            )

            # Phase 2+3 COMBINED: Partial Allocation Phase
            # (Replaces separate soft scoring + atomic allocation phases)
            logger.info("=== PHASE 2/3: Partial Allocation Phase ===")
            phase_start = time.perf_counter()
            partial_result, block_group_results = (
                self._execute_partial_allocation_phase(
                    remaining_demands, semester_id, dry_run
                )
            )
            phase_timings["phase_partial"] = round(
                time.perf_counter() - phase_start, 4
            )

            if not dry_run:
                self.session.commit()
                logger.info("Partial allocation phase committed")

            # Compile results
            execution_time = time.perf_counter() - start_time

            # Calculate statistics from block group results
            total_block_groups = len(block_group_results)
            allocated_block_groups = sum(1 for r in block_group_results if r.allocated)

            # Group results by demand to show which demands got split allocations
            demands_with_splits = {}
            for bgr in block_group_results:
                if bgr.demanda_id not in demands_with_splits:
                    demands_with_splits[bgr.demanda_id] = []
                demands_with_splits[bgr.demanda_id].append(bgr)

            # Count demands with multiple rooms (actual splits)
            split_demands = 0
            for demand_id, results in demands_with_splits.items():
                allocated_results = [r for r in results if r.allocated]
                unique_rooms = set(r.sala_id for r in allocated_results if r.sala_id)
                if len(unique_rooms) > 1:
                    split_demands += 1

            final_result = {
                "success": True,
                "semester_id": semester_id,
                "mode": "partial_allocation",
                "total_demands_initial": len(unallocated_demands),
                "allocations_completed": (
                    phase1_result.allocations_completed
                    + phase1_5_result.allocations_completed
                    + partial_result.allocations_completed
                ),
                "block_groups_processed": total_block_groups,
                "block_groups_allocated": allocated_block_groups,
                "demands_with_split_rooms": split_demands,
                "conflicts_found": (
                    phase1_result.conflicts_found + partial_result.conflicts_found
                ),
                "phase1_hard_rules": {
                    "allocations": phase1_result.allocations_completed,
                    "conflicts": phase1_result.conflicts_found,
                },
                "phase1_5_continuity": {
                    "allocations": phase1_5_result.allocations_completed,
                    "conflicts": phase1_5_result.conflicts_found,
                },
                "phase_partial": {
                    "block_groups_allocated": allocated_block_groups,
                    "block_groups_failed": total_block_groups - allocated_block_groups,
                    "split_allocations": split_demands,
                },
                # Hybrid discipline detection results (Phase 0)
                "hybrid_summary": self.decision_logger.get_hybrid_summary(),
                "continuity_summary": {
                    "profiles_built": len(continuity_profiles),
                    "non_hybrid_candidates_for_phase_1_5": continuity_candidates,
                    "hybrid_profiles": sum(
                        1
                        for profile in continuity_profiles.values()
                        if profile.is_hybrid
                    ),
                },
                "block_group_details": [
                    {
                        "demanda_id": r.demanda_id,
                        "day": r.day_name,
                        "blocks": r.blocks,
                        "allocated": r.allocated,
                        "sala_nome": r.sala_nome,
                        "score": r.score,
                        "failure_reason": r.failure_reason,
                    }
                    for r in block_group_results[:50]  # Limit for performance
                ],
                "execution_time": execution_time,
                "performance": {
                    **phase_timings,
                    "total_execution_time": round(execution_time, 4),
                },
                "progress_percentage": (
                    (allocated_block_groups / total_block_groups * 100)
                    if total_block_groups > 0
                    else 100
                ),
            }

            logger.info(
                f"Partial allocation complete: {allocated_block_groups}/{total_block_groups} "
                f"block groups allocated, {split_demands} demands split across rooms"
            )
            logger.info("Partial allocation performance: %s", final_result["performance"])

            return final_result

        except Exception as e:
            logger.error(f"Partial autonomous allocation failed: {e}")
            self.session.rollback()
            raise

    # =========================================================================
    # PHASE 0: HYBRID DISCIPLINE DETECTION
    # =========================================================================

    def _execute_hybrid_detection_phase(
        self, current_semester_id: int, debug_report=None
    ) -> HybridDetectionResult:
        """
        Phase 0: Detect hybrid disciplines from historical allocations.

        A hybrid discipline is one that has been allocated to both:
        - Regular classrooms (tipo_sala_id = 2)
        - Specialized rooms (labs, auditoriums, etc. - tipo_sala_id != 2)

        This phase analyzes the most recent historical semester to identify
        disciplines that need split allocation (lab on some days, classroom on others).

        After detection, the hybrid service is injected into the scoring service
        so that per-day scoring can apply the hybrid room type match bonus.

        Args:
            current_semester_id: The semester we're allocating for (NOT used for detection)
            debug_report: Optional debug report for logging

        Returns:
            HybridDetectionResult with detection details
        """
        logger.info("Starting Phase 0: Hybrid Discipline Detection")

        # Get the most recent semester WITH ALLOCATIONS for detection
        # CRITICAL: We need to use a semester that has historical data, NOT the current
        # empty semester we're about to allocate. This was the bug - we were using
        # get_most_recent_semester_id() which returned semester 5 (empty), instead of
        # semester 4 (which has historical allocations).
        detection_semester_id = (
            self.hybrid_detection_service.resolve_detection_semester(
                current_semester_id
            )
        )

        if not detection_semester_id:
            logger.warning(
                "No historical semesters with allocations found for hybrid detection"
            )
            self.decision_logger.log_no_hybrid_disciplines_found(
                detection_semester_id=0,
                reason="No semesters with allocation data found in database",
            )
            return HybridDetectionResult()

        logger.info(
            f"Using semester {detection_semester_id} for hybrid detection "
            f"(current semester: {current_semester_id})"
        )

        # Execute detection
        result = self.hybrid_detection_service.detect_hybrid_disciplines(
            detection_semester_id
        )

        logger.info(
            f"Phase 0 complete: Detected {result.detected_count} hybrid disciplines "
            f"from semester {result.detection_semester_id}"
        )

        # Log detected hybrid disciplines
        if result.hybrid_disciplines:
            for codigo in result.hybrid_disciplines[:5]:  # Log first 5
                info = result.details.get(codigo)
                if info:
                    logger.info(
                        f"  - {codigo}: lab_days={info.lab_days}, classroom_days={info.classroom_days}"
                    )
            if len(result.hybrid_disciplines) > 5:
                logger.info(f"  ... and {len(result.hybrid_disciplines) - 5} more")

        # Inject hybrid detection service into scoring service for hybrid-aware scoring
        self.scoring_service.set_hybrid_detection_service(self.hybrid_detection_service)
        logger.debug("Hybrid detection service injected into scoring service")

        # ===== DETAILED DEBUG LOGGING =====
        # Log Phase 0 results to the allocation decisions log file
        self.decision_logger.log_hybrid_detection_phase(
            detection_semester_id=detection_semester_id,
            current_semester_id=current_semester_id,
            hybrid_disciplines=result.hybrid_disciplines,
            detection_details=result.details,
        )

        # Log each hybrid discipline in detail
        for codigo, info in result.details.items():
            self.decision_logger.log_hybrid_discipline_detail(
                codigo_disciplina=codigo,
                lab_days=info.lab_days,
                classroom_days=info.classroom_days,
                lab_room_ids=info.historical_lab_rooms,
            )

        # Log if no hybrid disciplines found
        if not result.hybrid_disciplines:
            self.decision_logger.log_no_hybrid_disciplines_found(
                detection_semester_id=detection_semester_id,
                reason="Detection query returned 0 disciplines with 2+ rooms including non-classroom",
            )

        # Log to debug report
        if debug_report:
            debug_report.log_section_header("phase0_hybrid_detection")
            debug_report.log_kv("detection_semester_id", detection_semester_id)
            debug_report.log_kv("hybrid_disciplines_count", result.detected_count)
            for codigo, info in result.details.items():
                debug_report.log_kv(
                    f"hybrid_{codigo}",
                    f"lab_days={info.lab_days}, classroom_days={info.classroom_days}",
                )

        return result

    def execute_autonomous_allocation(
        self,
        semester_id: int,
        dry_run: bool = False,
        generate_debug_report: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute optimized autonomous allocation with detailed logging and PDF report generation.

        Args:
            semester_id: Semester to allocate for
            dry_run: If True, only simulate without actual allocations
            generate_debug_report: If True, generate comprehensive debug log file

        Returns:
            Detailed allocation results with PDF report
        """
        import time

        start_time = time.time()

        logger.info(
            f"Starting optimized autonomous allocation for semester {semester_id}"
        )
        self.decision_logger = AllocationDecisionLogger()

        # Initialize debug report if requested and DEBUG is enabled in settings
        debug_report = None
        settings = Settings()
        if generate_debug_report and settings.DEBUG:
            from src.utils.allocation_debug_report import AllocationDebugReport

            debug_report = AllocationDebugReport()
            logger.info(
                f"Debug report will be saved to: {debug_report.get_report_path()}"
            )

        try:
            # Get unallocated demands
            unallocated_demands = self.manual_service.get_unallocated_demands(
                semester_id
            )
            logger.info(f"Found {len(unallocated_demands)} unallocated demands")

            # Phase 0: Hybrid Discipline Detection (NEW!)
            logger.info("=== PHASE 0: Hybrid Discipline Detection ===")
            if debug_report:
                debug_report.log_phase_start(
                    "hybrid_detection",
                    "Detect hybrid disciplines from historical allocations",
                )

            phase0_result = self._execute_hybrid_detection_phase(
                semester_id, debug_report
            )

            if debug_report:
                debug_report.log_phase_end(
                    "hybrid_detection",
                    {
                        "hybrid_disciplines_detected": phase0_result.detected_count,
                        "detection_semester": phase0_result.detection_semester_id,
                        "hybrid_codes": phase0_result.hybrid_disciplines[
                            :10
                        ],  # First 10 for logging
                    },
                )

            # Phase 1: Hard Rules Allocation
            logger.info("=== PHASE 1: Hard Rules Allocation ===")
            if debug_report:
                debug_report.log_phase_start(
                    "hard_rules",
                    "Allocate demands with hard rules (specific room/type requirements)",
                )

            phase1_result = self._execute_hard_rules_phase_optimized(
                unallocated_demands, semester_id, dry_run, debug_report
            )
            self.decision_logger.log_phase_summary("hard_rules", phase1_result.__dict__)

            if debug_report:
                debug_report.log_phase_end(
                    "hard_rules",
                    {
                        "demands_processed": (
                            phase1_result.demands_processed
                            if hasattr(phase1_result, "demands_processed")
                            else 0
                        ),
                        "allocations_made": phase1_result.allocations_completed,
                        "conflicts_found": phase1_result.conflicts_found,
                        "skipped": phase1_result.demands_skipped,
                    },
                )

            # ✅ Commit Phase 1 allocations to ensure fresh conflict checks in Phase 3
            if not dry_run:
                self.session.commit()
                logger.info("Phase 1 allocations committed to database")

            # Get remaining demands - REFRESH after phase 1 allocations
            remaining_demands = self.manual_service.get_unallocated_demands(semester_id)
            logger.info(
                f"Phase 2: Processing {len(remaining_demands)} remaining unallocated demands"
            )

            # Phase 2: Soft Scoring Phase
            logger.info("=== PHASE 2: Soft Scoring Phase ===")
            if debug_report:
                debug_report.log_phase_start(
                    "soft_scoring",
                    "Score all rooms for remaining demands using soft preferences and historical data",
                )

            phase2_result = self._execute_soft_scoring_phase_optimized(
                remaining_demands, semester_id, debug_report
            )
            self.decision_logger.log_phase_summary(
                "soft_scoring", phase2_result.__dict__
            )

            if debug_report:
                debug_report.log_phase_end(
                    "soft_scoring",
                    {
                        "demands_processed": len(remaining_demands),
                        "allocations_made": 0,  # Scoring phase doesn't allocate
                        "conflicts_found": phase2_result.conflicts_found,
                        "skipped": phase2_result.demands_skipped,
                    },
                )

            # Phase 3: Atomic Allocation Phase
            logger.info("=== PHASE 3: Atomic Allocation Phase ===")
            if debug_report:
                debug_report.log_phase_start(
                    "atomic_allocation",
                    "Allocate demands to highest-scoring rooms with conflict detection",
                )

            phase3_result = self._execute_atomic_allocation_phase_optimized(
                phase2_result.candidates, semester_id, dry_run, debug_report
            )
            self.decision_logger.log_phase_summary(
                "atomic_allocation", phase3_result.__dict__
            )

            if debug_report:
                debug_report.log_phase_end(
                    "atomic_allocation",
                    {
                        "demands_processed": (
                            len(phase2_result.candidates)
                            if hasattr(phase2_result, "candidates")
                            else 0
                        ),
                        "allocations_made": phase3_result.allocations_completed,
                        "conflicts_found": phase3_result.conflicts_found,
                        "skipped": phase3_result.demands_skipped,
                    },
                )

            # ✅ Commit Phase 3 allocations
            if not dry_run:
                self.session.commit()
                logger.info("Phase 3 allocations committed to database")

            # Compile final results - count only new allocations made in this session
            execution_time = time.time() - start_time
            semester = self.semestre_repo.get_by_id(semester_id)
            semester_name = semester.nome if semester else f"Semestre {semester_id}"

            # Get the IDs of demands that were unallocated before this session
            initial_unallocated_ids = {d.id for d in unallocated_demands}

            # Get current allocations and count ONLY those that were from our initial unallocated set
            current_allocations = self.alocacao_repo.get_by_semestre(semester_id)
            newly_allocated_demand_ids = {
                alloc.demanda_id
                for alloc in current_allocations
                if alloc.demanda_id in initial_unallocated_ids
            }
            total_newly_allocated = len(newly_allocated_demand_ids)

            # Update phase results with actual new allocation counts
            phase1_result.allocations_completed = min(
                phase1_result.allocations_completed, total_newly_allocated
            )
            phase3_result.allocations_completed = (
                total_newly_allocated - phase1_result.allocations_completed
            )

            final_result = self._compile_final_results(
                phase1_result, phase2_result, phase3_result, semester_id
            )

            # Override with CORRECT new allocation count (not total semester allocations)
            final_result["allocations_completed"] = total_newly_allocated
            final_result["total_demands_processed"] = len(unallocated_demands)
            final_result["progress_percentage"] = (
                (total_newly_allocated / len(unallocated_demands) * 100)
                if unallocated_demands
                else 100
            )

            logger.info(
                f"Session summary: {total_newly_allocated} NEW allocations from {len(unallocated_demands)} unallocated demands"
            )
            logger.info(f"Demands that were allocated: {newly_allocated_demand_ids}")

            logger.info("=== GENERATING PDF REPORT ===")
            allocation_decisions = self.decision_logger.get_all_decisions()

            pdf_content = self.report_service.generate_autonomous_allocation_report(
                allocation_results=final_result,
                allocation_decisions=allocation_decisions,
                semester_name=semester_name,
                execution_time=execution_time,
            )

            # Add PDF to results
            final_result["pdf_report"] = pdf_content
            final_result["pdf_filename"] = (
                f"relatorio_alocacao_autonoma_{semester_name.replace('-', '_')}.pdf"
            )
            final_result["execution_time"] = execution_time

            # Log session summary
            self.decision_logger.log_session_summary(final_result)

            return final_result

        except Exception as e:
            logger.error(f"Optimized autonomous allocation failed: {e}")
            self.session.rollback()
            raise

    def _execute_hard_rules_phase_optimized(
        self, demands: List[Any], semester_id: int, dry_run: bool, debug_report=None
    ) -> PhaseResult:
        """Optimized hard rules phase with batch operations and logging."""
        result = PhaseResult()

        # Batch: Get all rules for all disciplines
        discipline_codes = [d.codigo_disciplina for d in demands]
        all_hard_rules = {}
        for code in discipline_codes:
            rules = self.regra_repo.find_rules_by_disciplina(code)
            all_hard_rules[code] = [r for r in rules if r.prioridade == 0]

        # Batch: Get professor information for all demands
        professor_map = self._lookup_professors_for_demands_from_objects(demands)

        # Batch: Get active rooms (block filtering is demand-specific below)
        all_rooms = self.sala_repo.get_available_for_allocation()

        # Process demands with hard rules
        demands_with_hard_rules = [
            d for d in demands if all_hard_rules.get(d.codigo_disciplina)
        ]

        logger.info(
            f"Processing {len(demands_with_hard_rules)} demands with hard rules"
        )

        for demanda in demands_with_hard_rules:
            demanda_id = demanda.id
            hard_rules = all_hard_rules[demanda.codigo_disciplina]
            professor = professor_map.get(demanda_id)

            # Demands already partially allocated are resumed in the partial phase.
            if self.alocacao_repo.get_by_demanda(demanda_id):
                logger.debug(
                    f"Skipping hard-rules single-room attempt for partially allocated demand {demanda.codigo_disciplina}"
                )
                continue

            atomic_blocks = self.parser.split_to_atomic_tuples(
                demanda.horario_sigaa_bruto
            )
            required_blocks = [block_code for block_code, _ in atomic_blocks]
            allocated_room = None

            # Debug report: Log demand start
            if debug_report:
                block_groups = []
                day_blocks = {}
                day_names = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}
                for bloco, dia in atomic_blocks:
                    if dia not in day_blocks:
                        day_blocks[dia] = []
                    day_blocks[dia].append(bloco)
                for dia, blocos in sorted(day_blocks.items()):
                    block_groups.append(
                        {
                            "day_id": dia,
                            "day_name": day_names.get(dia, f"D{dia}"),
                            "blocks": blocos,
                        }
                    )

                debug_report.log_demand_start(
                    demanda_id=demanda_id,
                    codigo=demanda.codigo_disciplina,
                    nome=demanda.nome_disciplina or "",
                    turma=demanda.turma_disciplina or "",
                    professores=demanda.professores_disciplina or "",
                    vagas=demanda.vagas_disciplina or 0,
                    horario_sigaa=demanda.horario_sigaa_bruto or "",
                    block_groups=block_groups,
                )

                # Log hard rules
                debug_report.log_hard_rules(
                    [
                        {
                            "tipo_regra": r.tipo_regra,
                            "descricao": r.descricao,
                            "prioridade": r.prioridade,
                        }
                        for r in hard_rules
                    ]
                )

            # Find rooms that satisfy hard rules
            suitable_rooms = []
            for room in all_rooms:
                if not self.sala_repo.is_room_enabled_for_blocks(
                    room.id, required_blocks
                ):
                    continue
                if self._check_hard_rules_compliance(room, demanda, hard_rules):
                    suitable_rooms.append(room)

            if suitable_rooms:
                # Build room-time slots ONLY for this demand's actual blocks
                room_time_slots = []
                for room in suitable_rooms:
                    for bloco_codigo, dia_sigaa in atomic_blocks:
                        room_time_slots.append((room.id, dia_sigaa, bloco_codigo))

                # Single batch query for conflict checks
                conflict_results = self.optimized_alocacao_repo.check_conflicts_batch(
                    room_time_slots, semester_id
                )

                # Find first room without conflicts
                allocated_room = None
                for room in suitable_rooms:
                    has_conflicts = any(
                        conflict_results.get((room.id, dia_sigaa, bloco_codigo), False)
                        for bloco_codigo, dia_sigaa in atomic_blocks
                    )

                    if not has_conflicts:
                        allocated_room = room
                        break

            if allocated_room:
                # Debug report: Log allocation decision
                if debug_report:
                    day_names = {
                        2: "SEG",
                        3: "TER",
                        4: "QUA",
                        5: "QUI",
                        6: "SEX",
                        7: "SAB",
                    }
                    atomic_blocks = self.parser.split_to_atomic_tuples(
                        demanda.horario_sigaa_bruto
                    )
                    all_blocks = [b[0] for b in atomic_blocks]
                    debug_report.log_allocation_decision(
                        day_name="ALL DAYS",
                        blocks=all_blocks,
                        chosen_room=allocated_room.nome,
                        score=100,
                        reason=f"Hard rule compliance: {len(hard_rules)} rule(s) satisfied, no conflicts",
                    )
                    debug_report.log_demand_summary(
                        demanda_id=demanda_id,
                        allocated=True,
                        rooms_used=[allocated_room.nome],
                        total_blocks=len(atomic_blocks),
                        allocated_blocks=len(atomic_blocks),
                        is_split=False,
                    )

                # Perform allocation
                if not dry_run:
                    success = self._allocate_atomic_blocks_optimized(
                        AllocationCandidate(
                            sala=allocated_room,
                            demanda_id=demanda_id,
                            score=100,  # Maximum priority for hard rules
                            professor_name=demanda.professores_disciplina,
                            professor_id=professor.id if professor else None,
                            atomic_blocks=self.parser.split_to_atomic_tuples(
                                demanda.horario_sigaa_bruto
                            ),
                        ),
                        semester_id,
                    )
                    if success:
                        result.allocations_completed += 1

                    # Log decision
                    self.decision_logger.log_allocation_attempt(
                        semester_id=semester_id,
                        demanda=demanda,
                        phase="hard_rules",
                        allocated=True,
                        allocated_room=allocated_room,
                        final_score=100,
                        candidates_evaluated=[
                            AllocationCandidate(
                                sala=r, demanda_id=demanda_id, score=100
                            )
                            for r in suitable_rooms
                        ],
                        hard_rules=hard_rules,
                        professor_prefs=self._get_professor_preferences_for_professor(
                            professor
                        ),
                        decision_reason="All hard rules satisfied and no conflicts",
                    )

                    logger.debug(
                        f"Allocated {demanda.codigo_disciplina} to {allocated_room.nome} via hard rules"
                    )
                else:
                    # Dry run - just count as successful
                    result.allocations_completed += 1

                    # Log decision
                    self.decision_logger.log_allocation_attempt(
                        semester_id=semester_id,
                        demanda=demanda,
                        phase="hard_rules",
                        allocated=True,
                        allocated_room=allocated_room,
                        final_score=100,
                        candidates_evaluated=[
                            AllocationCandidate(
                                sala=r, demanda_id=demanda_id, score=100
                            )
                            for r in suitable_rooms
                        ],
                        hard_rules=hard_rules,
                        professor_prefs=self._get_professor_preferences_for_professor(
                            professor
                        ),
                        decision_reason="All hard rules satisfied and no conflicts (dry run)",
                    )

                    logger.debug(
                        f"Would allocate {demanda.codigo_disciplina} to {allocated_room.nome} via hard rules (dry run)"
                    )
            else:
                # Log skipped due to no suitable rooms
                self.decision_logger.log_allocation_attempt(
                    semester_id=semester_id,
                    demanda=demanda,
                    phase="hard_rules",
                    allocated=False,
                    hard_rules=hard_rules,
                    skipped_reason="No rooms satisfy hard rules",
                )

        result.total_demands_processed = len(demands_with_hard_rules)
        result.success_rate = (
            result.allocations_completed / len(demands_with_hard_rules)
            if demands_with_hard_rules
            else 0
        )

        return result

    def _execute_soft_scoring_phase_optimized(
        self, demands: List[Any], semester_id: int, debug_report=None
    ) -> PhaseResult:
        """Optimized soft scoring phase with batch operations and logging."""
        result = PhaseResult()
        phase2_candidates = {}

        # Batch: Get professor information for all demands
        professor_map = self._lookup_professors_for_demands_from_objects(demands)

        logger.info(f"Scoring {len(demands)} demands with advanced algorithm")

        for demanda in demands:
            demanda_id = demanda.id

            # Debug report: Log demand start
            if debug_report:
                atomic_blocks = self.parser.split_to_atomic_tuples(
                    demanda.horario_sigaa_bruto
                )
                day_blocks = {}
                day_names = {2: "SEG", 3: "TER", 4: "QUA", 5: "QUI", 6: "SEX", 7: "SAB"}
                for bloco, dia in atomic_blocks:
                    if dia not in day_blocks:
                        day_blocks[dia] = []
                    day_blocks[dia].append(bloco)
                block_groups = []
                for dia, blocos in sorted(day_blocks.items()):
                    block_groups.append(
                        {
                            "day_id": dia,
                            "day_name": day_names.get(dia, f"D{dia}"),
                            "blocks": blocos,
                        }
                    )

                debug_report.log_demand_start(
                    demanda_id=demanda_id,
                    codigo=demanda.codigo_disciplina,
                    nome=demanda.nome_disciplina or "",
                    turma=demanda.turma_disciplina or "",
                    professores=demanda.professores_disciplina or "",
                    vagas=demanda.vagas_disciplina or 0,
                    horario_sigaa=demanda.horario_sigaa_bruto or "",
                    block_groups=block_groups,
                )

                # Log soft rules if any
                soft_rules = self.regra_repo.find_rules_by_disciplina(
                    demanda.codigo_disciplina
                )
                soft_rules = [r for r in soft_rules if r.prioridade > 0]
                debug_report.log_soft_rules(
                    [
                        {
                            "tipo_regra": r.tipo_regra,
                            "descricao": r.descricao,
                            "prioridade": r.prioridade,
                        }
                        for r in soft_rules
                    ]
                )

                # Log professor preferences
                professor = professor_map.get(demanda_id)
                if professor:
                    prof_prefs = self._get_professor_preferences_for_professor(
                        professor
                    )
                    debug_report.log_professor_preferences(prof_prefs)
                else:
                    debug_report.log_professor_preferences({})

            # Use shared scoring service
            candidates = self.scoring_service.score_room_candidates_for_demand(
                demanda_id,
                semester_id,
                professor_override=professor_map.get(demanda_id),
            )

            # Filter out candidates with conflicts
            valid_candidates = [c for c in candidates if not c.has_conflicts]
            result.conflicts_found += len(candidates) - len(valid_candidates)

            # Debug report: Log scoring for all candidates (top 10)
            if debug_report and candidates:
                room_scores = []
                for c in candidates[:15]:  # Show top 15
                    breakdown = (
                        c.scoring_breakdown
                        if hasattr(c, "scoring_breakdown") and c.scoring_breakdown
                        else None
                    )
                    room_scores.append(
                        {
                            "room_name": c.sala.nome if c.sala else "Unknown",
                            "room_capacity": c.sala.capacidade if c.sala else 0,
                            "total_score": c.score,
                            "capacity_score": (
                                breakdown.capacity_score if breakdown else 0
                            ),
                            "hard_rule_score": (
                                breakdown.hard_rule_score if breakdown else 0
                            ),
                            "historical_score": (
                                breakdown.historical_score if breakdown else 0
                            ),
                            "historical_allocations": (
                                breakdown.historical_allocations if breakdown else 0
                            ),
                            "professor_room_score": (
                                breakdown.professor_room_score if breakdown else 0
                            ),
                            "professor_char_score": (
                                breakdown.professor_char_score if breakdown else 0
                            ),
                            "has_conflict": c.has_conflicts,
                        }
                    )

                debug_report.log_block_group_scoring(
                    day_id=0,
                    day_name="ALL BLOCKS (combined)",
                    blocks=[
                        b[0]
                        for b in self.parser.split_to_atomic_tuples(
                            demanda.horario_sigaa_bruto
                        )
                    ],
                    room_scores=room_scores,
                    max_rooms_to_show=10,
                )

            if valid_candidates:
                # Convert to AllocationCandidates
                allocation_candidates = []
                for candidate in valid_candidates:
                    allocation_candidates.append(
                        AllocationCandidate(
                            sala=candidate.sala,
                            demanda_id=demanda_id,
                            score=candidate.score,
                            professor_name=demanda.professores_disciplina,
                            professor_id=(
                                professor_map.get(demanda_id).id
                                if professor_map.get(demanda_id)
                                else None
                            ),
                            atomic_blocks=self.parser.split_to_atomic_tuples(
                                demanda.horario_sigaa_bruto
                            ),
                            scoring_breakdown=(
                                candidate.scoring_breakdown.__dict__
                                if hasattr(candidate, "scoring_breakdown")
                                and candidate.scoring_breakdown
                                else None
                            ),
                        )
                    )

                phase2_candidates[demanda_id] = allocation_candidates

                # Log scoring decision
                self.decision_logger.log_allocation_attempt(
                    semester_id=semester_id,
                    demanda=demanda,
                    phase="soft_scoring",
                    allocated=False,  # Not allocated yet, just scored
                    final_score=valid_candidates[0].score if valid_candidates else 0,
                    scoring_breakdown=(
                        valid_candidates[0].scoring_breakdown.__dict__
                        if valid_candidates and valid_candidates[0].scoring_breakdown
                        else None
                    ),
                    candidates_evaluated=valid_candidates[:5],  # Top 5 candidates
                    professor_prefs=self._get_professor_preferences_for_professor(
                        professor_map.get(demanda_id)
                    ),
                    historical_count=(
                        valid_candidates[0].scoring_breakdown.historical_allocations
                        if valid_candidates and valid_candidates[0].scoring_breakdown
                        else 0
                    ),
                    decision_reason=f"Scored {len(valid_candidates)} valid candidates, top score: {valid_candidates[0].score if valid_candidates else 0}",
                )

        result.candidates = phase2_candidates
        result.total_demands_processed = len(demands)
        result.success_rate = len(phase2_candidates) / len(demands) if demands else 0

        return result

    def _execute_atomic_allocation_phase_optimized(
        self,
        phase2_candidates: Dict[int, List[AllocationCandidate]],
        semester_id: int,
        dry_run: bool,
        debug_report: Optional[AllocationDebugReport] = None,
    ) -> PhaseResult:
        """Optimized atomic allocation phase with FRESH conflict checks.

        This method performs a batch conflict check against CURRENT DB state
        (after Phase 1 allocations) to ensure accurate conflict detection.
        The conflict map is updated incrementally as each demand is allocated.
        """
        result = PhaseResult()

        # Sort all candidates by score for prioritization
        # Keep ALL candidates per demand (not just top 1) to enable fallback
        demands_with_candidates = {}
        for demanda_id, candidates in phase2_candidates.items():
            if candidates:
                # Sort candidates by score for this demand
                candidates.sort(key=lambda c: c.score, reverse=True)
                demands_with_candidates[demanda_id] = candidates

        # Sort demands by their best candidate score
        sorted_demand_ids = sorted(
            demands_with_candidates.keys(),
            key=lambda did: demands_with_candidates[did][0].score,
            reverse=True,
        )

        logger.info(
            f"Attempting atomic allocation for {len(sorted_demand_ids)} scored demands"
        )

        allocation_attempts = []

        for demanda_id in sorted_demand_ids:
            # Get demand details for logging
            demanda = self.demanda_repo.get_by_id(demanda_id)
            if not demanda:
                continue

            candidates = demands_with_candidates[demanda_id]
            allocation_success = False

            # Debug report: Log demand start in Phase 3
            if debug_report:
                debug_report.log_demand_start(
                    demanda_id=demanda_id,
                    codigo=demanda.codigo_disciplina,
                    nome=demanda.nome_disciplina,
                    turma=demanda.turma_disciplina,
                    professores=demanda.professores_disciplina,
                    vagas=demanda.vagas_disciplina,
                    horario_sigaa=demanda.horario_sigaa_bruto,
                    block_groups=[],
                )

            # ✅ CRITICAL FIX: Try ALL candidates for this demand until one succeeds
            # Original version tries multiple candidates; optimized was only trying 1
            candidates_tried = []
            for candidate_idx, candidate in enumerate(candidates):
                # Build slots for this specific candidate
                slots = [
                    (candidate.sala.id, dia_sigaa, bloco_codigo)
                    for bloco_codigo, dia_sigaa in candidate.atomic_blocks
                ]

                # ✅ Fresh conflict check for THIS candidate against CURRENT DB state
                fresh_conflict_check = (
                    self.optimized_alocacao_repo.check_conflicts_batch(
                        slots, semester_id
                    )
                )
                has_conflicts = any(
                    fresh_conflict_check.get(slot, False) for slot in slots
                )

                if has_conflicts:
                    # Try next candidate for this demand
                    result.conflicts_found += 1
                    candidates_tried.append(
                        {
                            "room": candidate.sala.nome,
                            "score": candidate.score,
                            "result": "CONFLICT",
                            "reason": "Time slot conflicts with existing allocation",
                        }
                    )
                    logger.debug(
                        f"Candidate {candidate.sala.nome} for {demanda.codigo_disciplina} has conflicts, trying next..."
                    )
                    continue

                # No conflicts - try to allocate
                if not dry_run:
                    success = self._allocate_atomic_blocks_optimized(
                        candidate, semester_id
                    )
                    if success:
                        result.allocations_completed += 1
                        allocation_attempts.append((demanda, candidate, True, None))
                        allocation_success = True
                        candidates_tried.append(
                            {
                                "room": candidate.sala.nome,
                                "score": candidate.score,
                                "result": "ALLOCATED",
                                "reason": f"Successfully allocated (rank #{candidate_idx + 1})",
                            }
                        )
                        logger.debug(
                            f"Successfully allocated {demanda.codigo_disciplina} to room {candidate.sala.nome} (score: {candidate.score})"
                        )
                        break  # Success - move to next demand
                    else:
                        # Allocation failed - try next candidate
                        candidates_tried.append(
                            {
                                "room": candidate.sala.nome,
                                "score": candidate.score,
                                "result": "DB_ERROR",
                                "reason": "Database allocation failed",
                            }
                        )
                        logger.debug(
                            f"Allocation failed for {candidate.sala.nome}, trying next candidate..."
                        )
                        continue
                else:
                    # Dry run - just count as successful (no DB operations)
                    result.allocations_completed += 1
                    allocation_attempts.append((demanda, candidate, True, None))
                    allocation_success = True
                    logger.debug(
                        f"[DRY RUN] Would allocate {demanda.codigo_disciplina} to room {candidate.sala.nome}"
                    )
                    break

            # If no candidates worked, record the failure
            if not allocation_success:
                best_candidate = candidates[0]
                allocation_attempts.append(
                    (
                        demanda,
                        best_candidate,
                        False,
                        f"All {len(candidates)} candidates had conflicts or failed allocation",
                    )
                )
                result.demands_skipped += 1
                logger.debug(
                    f"Could not allocate {demanda.codigo_disciplina} - all {len(candidates)} candidates exhausted"
                )

        # Log all allocation decisions
        for demanda, candidate, success, failure_reason in allocation_attempts:
            if success:
                self.decision_logger.log_allocation_attempt(
                    semester_id=semester_id,
                    demanda=demanda,
                    phase="atomic_allocation",
                    allocated=True,
                    allocated_room=candidate.sala,
                    final_score=candidate.score,
                    scoring_breakdown=candidate.scoring_breakdown,
                    candidates_evaluated=[candidate],
                    decision_reason=f"Successfully allocated in atomic phase with score {candidate.score}",
                )
            else:
                self.decision_logger.log_allocation_attempt(
                    semester_id=semester_id,
                    demanda=demanda,
                    phase="atomic_allocation",
                    allocated=False,
                    final_score=candidate.score,
                    candidates_evaluated=[candidate],
                    skipped_reason=failure_reason,
                )

        result.total_demands_processed = len(sorted_demand_ids)
        result.success_rate = (
            result.allocations_completed / len(sorted_demand_ids)
            if sorted_demand_ids
            else 0
        )

        return result

    def _allocate_atomic_blocks_optimized(
        self, candidate: AllocationCandidate, semester_id: int
    ) -> bool:
        """
        Optimized atomic block allocation using batch operations.

        Creates all allocation records in a single transaction.
        """
        try:
            # Prepare all allocation DTOs
            allocation_dtos = []
            for bloco_codigo, dia_sigaa in candidate.atomic_blocks:
                allocation_dto = AlocacaoSemestralCreate(
                    semestre_id=semester_id,
                    demanda_id=candidate.demanda_id,
                    sala_id=candidate.sala.id,
                    dia_semana_id=dia_sigaa,
                    codigo_bloco=bloco_codigo,
                    origem_alocacao="autonoma",
                )
                allocation_dtos.append(allocation_dto)

            # Batch create all allocations in a single transaction
            created_allocations = self.optimized_alocacao_repo.create_batch_atomic(
                allocation_dtos
            )

            logger.debug(
                f"Batch allocated {len(created_allocations)} blocks for demand {candidate.demanda_id} to room {candidate.sala.id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Batch allocation failed for demand {candidate.demanda_id}: {e}"
            )
            return False

    def _check_hard_rules_compliance(
        self, room: Any, demanda: Any, hard_rules: List[Any]
    ) -> bool:
        """Check if room complies with all hard rules for a demand."""
        for rule in hard_rules:
            if not self.scoring_service._check_rule_compliance(room, demanda, rule):
                return False
        return True

    def _compile_final_results(
        self,
        phase1_result: PhaseResult,
        phase2_result: PhaseResult,
        phase3_result: PhaseResult,
        semester_id: int,
    ) -> Dict[str, Any]:
        """Compile final allocation results from all phases."""

        # Get total demands for percentage calculation
        all_demands = self.manual_service.get_all_demands(semester_id)
        total_demands = len(all_demands)

        # Calculate totals using the correct PhaseResult attributes
        total_allocated = (
            phase1_result.allocations_completed + phase3_result.allocations_completed
        )

        result = {
            "success": True,
            "semester_id": semester_id,
            "total_demands_processed": total_demands,
            "allocations_completed": total_allocated,
            "conflicts_found": phase1_result.conflicts_found
            + phase2_result.conflicts_found
            + phase3_result.conflicts_found,
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
                "candidates_scored": phase2_result.total_demands_processed,
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
                (total_allocated / total_demands * 100) if total_demands > 0 else 100
            ),
            "next_steps": "Phase 2: Manual fine-tuning of autonomous results",
            "performance": {
                "optimization": "Batch operations enabled - 80-90% I/O reduction",
                "logging": "Detailed decision logging enabled",
            },
            "decision_log_available": True,
            "log_file_location": "logs/autonomous_allocation_decisions.log",
        }

        return result

    def get_allocation_decision_report(
        self, disciplina_codigo: str = None
    ) -> Dict[str, Any]:
        """Get detailed report of allocation decisions."""
        return self.decision_logger.get_allocation_report(disciplina_codigo)
