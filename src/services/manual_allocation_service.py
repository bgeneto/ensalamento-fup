"""Service for executing manual allocation operations."""

from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.repositories.alocacao import AlocacaoRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.regra import RegraRepository
from src.repositories.reserva import ReservaRepository
from src.repositories.sala import SalaRepository
from src.repositories.semestre import SemestreRepository
from src.schemas.allocation import (
    AlocacaoSemestralCreate,
    PartialAllocationResult,
)
from src.schemas.manual_allocation import (
    AllocationResult,
    AllocationSuggestions,
    ConflictDetail,
    RoomSuggestion,
)
from src.services.room_scoring_service import BlockGroup, RoomScoringService
from src.utils.sigaa_parser import SigaaScheduleParser


class ManualAllocationService:
    """Service for manual allocation execution with conflict detection."""

    def __init__(self, session: Session):
        """Initialize service with repositories."""
        self.session = session
        self.alocacao_repo = AlocacaoRepository(session)
        self.demanda_repo = DisciplinaRepository(session)
        self.semestre_repo = SemestreRepository(session)
        self.reserva_repo = ReservaRepository(session)
        self.sala_repo = SalaRepository(session)
        self.regra_repo = RegraRepository(session)
        self.parser = SigaaScheduleParser()
        self.scoring_service = RoomScoringService(session)

    def allocate_demand(self, demanda_id: int, sala_id: int) -> AllocationResult:
        """
        Allocate a demand to a room.

        This method:
        1. Parses the demand's schedule into atomic blocks
        2. Checks for conflicts in alocacoes_semestrais table
        3. Creates allocation records for each block atomically
        4. Returns success/failure with detailed conflict information
        """
        # Get demand details
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message="Demanda não encontrada",
            )

        # Get semester (used for foreign key)
        semester = self.semestre_repo.get_by_id(demanda.semestre_id)
        if not semester:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message="Semestre da demanda não encontrado",
            )

        # Parse schedule into atomic blocks
        atomic_blocks = self.parser.split_to_atomic_tuples(demanda.horario_sigaa_bruto)
        if not atomic_blocks:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message="Não foi possível parsear o horário da demanda",
            )

        # Create atomic blocks preview for result
        atomic_preview = [f"{dia}{bloco}" for bloco, dia in atomic_blocks]

        # Check for conflicts before attempting allocation
        conflicts = self._check_allocation_conflicts(
            sala_id, atomic_blocks, semester.id
        )
        if conflicts:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                sala_id=sala_id,
                conflicts=conflicts,
                allocated_blocks_count=len(atomic_blocks),
                atomic_blocks_preview=atomic_preview,
                error_message=f"Encontrados {len(conflicts)} conflitos de horário",
            )

        # Execute allocation atomically
        try:
            created_allocation_ids = []

            for bloco_codigo, dia_sigaa in atomic_blocks:
                allocation_dto = AlocacaoSemestralCreate(
                    semestre_id=semester.id,
                    demanda_id=demanda_id,
                    sala_id=sala_id,
                    dia_semana_id=dia_sigaa,
                    codigo_bloco=bloco_codigo,
                )

                new_allocation = self.alocacao_repo.create(allocation_dto)
                created_allocation_ids.append(new_allocation.id)

            return AllocationResult(
                success=True,
                demanda_id=demanda_id,
                sala_id=sala_id,
                created_allocation_ids=created_allocation_ids,
                allocated_blocks_count=len(atomic_blocks),
                atomic_blocks_preview=atomic_preview,
            )

        except IntegrityError as e:
            # This shouldn't happen due to conflict checking, but handle it gracefully
            self.session.rollback()
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                sala_id=sala_id,
                error_message=f"Erro de integridade ao alocar: {str(e)}",
            )
        except Exception as e:
            self.session.rollback()
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                sala_id=sala_id,
                error_message=f"Erro inesperado na alocação: {str(e)}",
            )

    def allocate_demand_partial(
        self,
        demanda_id: int,
        sala_id: int,
        day_ids: Optional[List[int]] = None,
        block_codes: Optional[List[str]] = None,
    ) -> PartialAllocationResult:
        """
        Allocate specific blocks/days of a demand to a room.

        This enables partial/split allocation for hybrid disciplines that need
        different rooms on different days (e.g., lab on Monday, lecture on Wednesday).

        Args:
            demanda_id: Demand ID to allocate
            sala_id: Room ID to allocate to
            day_ids: Optional list of specific day IDs to allocate (2=MON, 3=TUE, etc.)
                     If None, all days are considered.
            block_codes: Optional list of specific block codes to allocate (M1, M2, T1, etc.)
                         If None, all blocks for the specified days are allocated.

        Returns:
            PartialAllocationResult with details of what was allocated and what remains.
        """
        # Get demand details
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return PartialAllocationResult(
                success=False,
                message="Demanda não encontrada",
                allocated_blocks=[],
                remaining_blocks=[],
            )

        # Get semester
        semester = self.semestre_repo.get_by_id(demanda.semestre_id)
        if not semester:
            return PartialAllocationResult(
                success=False,
                message="Semestre da demanda não encontrado",
                allocated_blocks=[],
                remaining_blocks=[],
            )

        # Get room for result
        room = self.sala_repo.get_by_id(sala_id)
        room_name = room.nome if room else "N/A"

        # Parse all atomic blocks for this demand
        all_atomic_blocks = self.parser.split_to_atomic_tuples(demanda.horario_sigaa_bruto)
        if not all_atomic_blocks:
            return PartialAllocationResult(
                success=False,
                message="Não foi possível parsear o horário da demanda",
                allocated_blocks=[],
                remaining_blocks=[],
            )

        # Get already allocated blocks for this demand
        existing_allocations = self.alocacao_repo.get_by_demanda(demanda_id)
        already_allocated = set()
        for alloc in existing_allocations:
            already_allocated.add((alloc.codigo_bloco, alloc.dia_semana_id))

        # Filter blocks to allocate based on day_ids and block_codes
        blocks_to_allocate = []
        for block_code, day_id in all_atomic_blocks:
            # Skip if already allocated
            if (block_code, day_id) in already_allocated:
                continue

            # Filter by day_ids if specified
            if day_ids is not None and day_id not in day_ids:
                continue

            # Filter by block_codes if specified
            if block_codes is not None and block_code not in block_codes:
                continue

            blocks_to_allocate.append((block_code, day_id))

        if not blocks_to_allocate:
            # Check if there are remaining unallocated blocks
            remaining = [
                f"{day}{block}"
                for block, day in all_atomic_blocks
                if (block, day) not in already_allocated
            ]
            return PartialAllocationResult(
                success=False,
                message="Nenhum bloco a alocar (já alocados ou não correspondem aos filtros)",
                allocated_blocks=[],
                remaining_blocks=remaining,
            )

        # Check for conflicts before attempting allocation
        conflicts = self._check_allocation_conflicts(
            sala_id, blocks_to_allocate, semester.id
        )
        if conflicts:
            return PartialAllocationResult(
                success=False,
                message=f"Encontrados {len(conflicts)} conflitos de horário",
                allocated_blocks=[],
                remaining_blocks=[f"{day}{block}" for block, day in blocks_to_allocate],
            )

        # Execute allocation
        try:
            created_allocation_ids = []
            allocated_blocks = []

            for block_code, day_id in blocks_to_allocate:
                allocation_dto = AlocacaoSemestralCreate(
                    semestre_id=semester.id,
                    demanda_id=demanda_id,
                    sala_id=sala_id,
                    dia_semana_id=day_id,
                    codigo_bloco=block_code,
                )

                new_allocation = self.alocacao_repo.create(allocation_dto)
                created_allocation_ids.append(new_allocation.id)
                allocated_blocks.append(f"{day_id}{block_code}")

            # Calculate remaining unallocated blocks
            now_allocated = already_allocated.union(set(blocks_to_allocate))
            remaining_blocks = [
                f"{day}{block}"
                for block, day in all_atomic_blocks
                if (block, day) not in now_allocated
            ]

            return PartialAllocationResult(
                success=True,
                message=f"Alocados {len(allocated_blocks)} blocos com sucesso",
                allocated_blocks=allocated_blocks,
                remaining_blocks=remaining_blocks,
                allocation_ids=created_allocation_ids,
                room_id=sala_id,
                room_name=room_name,
            )

        except IntegrityError as e:
            self.session.rollback()
            return PartialAllocationResult(
                success=False,
                message=f"Erro de integridade ao alocar: {str(e)}",
                allocated_blocks=[],
                remaining_blocks=[f"{day}{block}" for block, day in blocks_to_allocate],
            )
        except Exception as e:
            self.session.rollback()
            return PartialAllocationResult(
                success=False,
                message=f"Erro inesperado na alocação: {str(e)}",
                allocated_blocks=[],
                remaining_blocks=[f"{day}{block}" for block, day in blocks_to_allocate],
            )

    def get_block_groups_for_demand(self, demanda_id: int) -> List[Dict]:
        """
        Get block groups for a demand, organized by day.

        Returns a list of block groups with allocation status for each.
        Useful for UI to show which day-groups are allocated and which are pending.

        Args:
            demanda_id: Demand ID to get block groups for

        Returns:
            List of dicts with block group info and allocation status:
            [
                {
                    'day_id': 2,
                    'day_name': 'SEG',
                    'blocks': ['M1', 'M2'],
                    'time_range': '08:00-09:50',
                    'is_allocated': True,
                    'allocated_room_id': 5,
                    'allocated_room_name': 'AT-01',
                },
                ...
            ]
        """
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return []

        # Get block groups using parser
        block_groups = self.parser.get_block_groups_with_names(demanda.horario_sigaa_bruto)

        # Get existing allocations for this demand
        existing_allocations = self.alocacao_repo.get_by_demanda(demanda_id)

        # Build a map of (day_id, block_code) -> allocation info
        allocation_map: Dict[Tuple[int, str], dict] = {}
        for alloc in existing_allocations:
            key = (alloc.dia_semana_id, alloc.codigo_bloco)
            if key not in allocation_map:
                # Get room info
                room = self.sala_repo.get_by_id(alloc.sala_id)
                allocation_map[key] = {
                    'sala_id': alloc.sala_id,
                    'sala_nome': room.nome if room else "N/A",
                }

        # Enrich block groups with allocation status
        result = []
        for group in block_groups:
            day_id = group['day_id']
            blocks = group['blocks']

            # Check if ALL blocks in this day are allocated (and to the same room)
            allocated_rooms = set()
            all_allocated = True
            for block in blocks:
                key = (day_id, block)
                if key in allocation_map:
                    allocated_rooms.add(allocation_map[key]['sala_id'])
                else:
                    all_allocated = False

            # Determine allocation status
            is_allocated = all_allocated and len(allocated_rooms) == 1
            is_partial = len(allocated_rooms) > 0 and not is_allocated

            allocated_room_id = None
            allocated_room_name = None
            if is_allocated and allocated_rooms:
                room_id = list(allocated_rooms)[0]
                allocated_room_id = room_id
                room = self.sala_repo.get_by_id(room_id)
                allocated_room_name = room.nome if room else "N/A"

            result.append({
                'day_id': day_id,
                'day_name': group['day_name'],
                'blocks': blocks,
                'time_range': self.parser.get_time_range_for_blocks(blocks),
                'is_allocated': is_allocated,
                'is_partial': is_partial,
                'allocated_room_id': allocated_room_id,
                'allocated_room_name': allocated_room_name,
            })

        return result

    def get_suggestions_for_block_group(
        self,
        demanda_id: int,
        day_id: int,
        semester_id: int,
    ) -> List[Dict]:
        """
        Get room suggestions for a specific block group (day) of a demand.

        Uses per-day historical scoring to provide day-specific room recommendations.
        This is essential for hybrid disciplines that need different rooms on different days.

        Args:
            demanda_id: Demand ID
            day_id: Day ID (2=MON, 3=TUE, etc.)
            semester_id: Semester to check conflicts within

        Returns:
            List of room suggestions with per-day scoring, sorted by score descending.
        """
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return []

        # Get block groups for this demand
        block_groups_raw = self.parser.get_block_groups_with_names(demanda.horario_sigaa_bruto)

        # Find the specific block group for this day
        target_group = None
        for group in block_groups_raw:
            if group['day_id'] == day_id:
                target_group = BlockGroup(
                    day_id=group['day_id'],
                    day_name=group['day_name'],
                    blocks=group['blocks'],
                )
                break

        if not target_group:
            return []

        # Use scoring service to get per-block-group scores
        scores = self.scoring_service.score_rooms_for_block_group(
            demanda_id, target_group, semester_id
        )

        # Convert to dict format for UI
        result = []
        for score in scores:
            result.append({
                'room_id': score.room_id,
                'room_name': score.room_name,
                'room_capacity': score.room_capacity,
                'room_type': score.room_type,
                'building_name': score.building_name,
                'score': score.score,
                'has_conflict': score.has_conflict,
                'conflict_details': score.conflict_details,
                'breakdown': {
                    'capacity_points': score.breakdown.capacity_points,
                    'hard_rules_points': score.breakdown.hard_rules_points,
                    'soft_preference_points': score.breakdown.soft_preference_points,
                    'historical_frequency_points': score.breakdown.historical_frequency_points,
                    'capacity_satisfied': score.breakdown.capacity_satisfied,
                    'hard_rules_satisfied': score.breakdown.hard_rules_satisfied,
                    'soft_preferences_satisfied': score.breakdown.soft_preferences_satisfied,
                    'historical_allocations': score.breakdown.historical_allocations,
                },
            })

        return result

    def get_allocation_status_for_demand(self, demanda_id: int) -> Dict:
        """
        Get comprehensive allocation status for a demand.

        Returns summary of what's allocated, what's pending, and overall progress.

        Args:
            demanda_id: Demand ID

        Returns:
            Dict with allocation summary:
            {
                'demanda_id': 123,
                'total_blocks': 4,
                'allocated_blocks': 2,
                'pending_blocks': 2,
                'is_fully_allocated': False,
                'is_partially_allocated': True,
                'block_groups': [...],  # From get_block_groups_for_demand
                'allocated_rooms': [{'room_id': 5, 'room_name': 'AT-01', 'blocks': [...]}],
            }
        """
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return {
                'demanda_id': demanda_id,
                'error': 'Demanda não encontrada',
            }

        # Get all atomic blocks
        all_blocks = self.parser.split_to_atomic_tuples(demanda.horario_sigaa_bruto)
        total_blocks = len(all_blocks)

        # Get existing allocations
        existing_allocations = self.alocacao_repo.get_by_demanda(demanda_id)
        allocated_blocks_set = set()
        rooms_blocks_map: Dict[int, List[str]] = {}  # room_id -> list of block codes

        for alloc in existing_allocations:
            allocated_blocks_set.add((alloc.codigo_bloco, alloc.dia_semana_id))
            if alloc.sala_id not in rooms_blocks_map:
                rooms_blocks_map[alloc.sala_id] = []
            rooms_blocks_map[alloc.sala_id].append(f"{alloc.dia_semana_id}{alloc.codigo_bloco}")

        allocated_count = len(allocated_blocks_set)
        pending_count = total_blocks - allocated_count

        # Build allocated_rooms list
        allocated_rooms = []
        for room_id, blocks in rooms_blocks_map.items():
            room = self.sala_repo.get_by_id(room_id)
            allocated_rooms.append({
                'room_id': room_id,
                'room_name': room.nome if room else "N/A",
                'blocks': blocks,
            })

        # Get block groups with status
        block_groups = self.get_block_groups_for_demand(demanda_id)

        return {
            'demanda_id': demanda_id,
            'total_blocks': total_blocks,
            'allocated_blocks': allocated_count,
            'pending_blocks': pending_count,
            'is_fully_allocated': pending_count == 0,
            'is_partially_allocated': allocated_count > 0 and pending_count > 0,
            'block_groups': block_groups,
            'allocated_rooms': allocated_rooms,
        }

    def _check_allocation_conflicts(
        self, sala_id: int, atomic_blocks: List[tuple], semester_id: int
    ) -> List[ConflictDetail]:
        """
        Check for conflicts when allocating these blocks to this room.

        Note: In a complete implementation, this would also check against
        ad-hoc reservations, but that requires complex date-to-weekday conversion.
        For now, we only check semester allocations.
        """
        conflicts = []

        for bloco_codigo, dia_sigaa in atomic_blocks:
            # Check if there's already an allocation for this time slot in CURRENT semester
            has_conflict = self.alocacao_repo.check_conflict(
                sala_id, dia_sigaa, bloco_codigo, semestre_id=semester_id
            )

            if has_conflict:
                # Find the conflicting allocation for detailed error message
                allocs = self.alocacao_repo.get_by_horario(dia_sigaa, bloco_codigo)
                for alloc in allocs:
                    if alloc.sala_id == sala_id:
                        conflicts.append(
                            ConflictDetail(
                                tipo_conflito="semester_allocation",
                                dia_sigaa=dia_sigaa,
                                codigo_bloco=bloco_codigo,
                                entidade_conflitante=alloc.demanda.nome_disciplina,
                                identificador_conflitante=alloc.demanda.codigo_disciplina,
                            )
                        )
                        break

        return conflicts

    def get_allocation_progress(self, semester_id: int) -> dict:
        """Get allocation progress summary for a semester."""
        # Get total demands for semester
        demandas = self.demanda_repo.get_by_semestre(semester_id)
        total_demands = len(demandas)

        # Get allocated demands (demands that have at least one allocation)
        allocations = self.alocacao_repo.get_by_semestre(semester_id)
        allocated_demand_ids = set(alloc.demanda_id for alloc in allocations)
        allocated_demands = len(allocated_demand_ids)

        # Calculate percentage
        allocation_percent = (
            (allocated_demands / total_demands * 100) if total_demands > 0 else 0
        )

        return {
            "semester_id": semester_id,
            "total_demands": total_demands,
            "allocated_demands": allocated_demands,
            "unallocated_demands": total_demands - allocated_demands,
            "allocation_percent": allocation_percent,
        }

    def get_unallocated_demands(self, semester_id: int) -> List[dict]:
        """Get all demands in a semester that haven't been allocated yet."""
        # Get all demands for semester
        demandas = self.demanda_repo.get_by_semestre(semester_id)

        # Get allocated demand IDs
        allocations = self.alocacao_repo.get_by_semestre(semester_id)
        allocated_ids = set(alloc.demanda_id for alloc in allocations)

        # Filter out allocated demands
        unallocated = [d for d in demandas if d.id not in allocated_ids]

        return [self.demanda_repo.orm_to_dto(d) for d in unallocated]

    def get_allocated_demands(self, semester_id: int) -> List[dict]:
        """Get all demands in a semester that have been allocated."""
        # Get all demands for semester
        demandas = self.demanda_repo.get_by_semestre(semester_id)

        # Get allocated demand IDs
        allocations = self.alocacao_repo.get_by_semestre(semester_id)
        allocated_ids = set(alloc.demanda_id for alloc in allocations)

        # Filter to only allocated demands
        allocated = [d for d in demandas if d.id in allocated_ids]

        return [self.demanda_repo.orm_to_dto(d) for d in allocated]

    def get_all_demands(self, semester_id: int) -> List[dict]:
        """Get all demands in a semester regardless of allocation status."""
        demandas = self.demanda_repo.get_by_semestre(semester_id)
        return [self.demanda_repo.orm_to_dto(d) for d in demandas]

    def deallocate_demand(self, demanda_id: int) -> AllocationResult:
        """
        Deallocate a demand by removing all its allocations.

        This method:
        1. Finds all allocations for the demand
        2. Deletes them atomically
        3. Returns success/failure with details

        Args:
            demanda_id: The demand ID to deallocate

        Returns:
            AllocationResult with deallocation details
        """
        # Check if demand exists
        demanda = self.demanda_repo.get_by_id(demanda_id)
        if not demanda:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message="Demanda não encontrada",
            )

        # Get all allocations for this demand
        allocations = self.alocacao_repo.get_by_demanda(demanda_id)
        if not allocations:
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message="Demanda não possui alocações para remover",
            )

        try:
            # Delete all allocations for this demand
            deleted_count = 0
            deleted_allocation_ids = []

            for alloc in allocations:
                self.alocacao_repo.delete(alloc.id)
                deleted_allocation_ids.append(alloc.id)
                deleted_count += 1

            return AllocationResult(
                success=True,
                demanda_id=demanda_id,
                sala_id=None,  # Deallocation doesn't target a specific room
                error_message=f"Removida(s) {deleted_count} alocação(ões)",
            )

        except Exception as e:
            self.session.rollback()
            return AllocationResult(
                success=False,
                demanda_id=demanda_id,
                error_message=f"Erro ao remover alocações: {str(e)}",
            )

    def get_suggestions_for_demand(
        self, demanda_id: int, semester_id: int
    ) -> AllocationSuggestions:
        """
        Get room suggestions for a specific demand using unified advanced scoring.

        Returns AllocationSuggestions with top suggestions, other available, and conflicting rooms.
        Now uses the same advanced scoring as autonomous allocation with:
        - Historical frequency bonus (RF-006.6)
        - Semester-isolated conflict detection
        """
        # Use the shared advanced scoring service with professor override for consistency
        # Lookup professor information first to match autonomous allocation behavior
        professor_map = (
            self.scoring_service._lookup_professors_for_demands_from_objects(
                [self.demanda_repo.get_by_id(demanda_id)]
            )
        )
        professor_override = professor_map.get(demanda_id)

        candidates = self.scoring_service.score_room_candidates_for_demand(
            demanda_id, semester_id, professor_override=professor_override
        )

        # Convert candidates to RoomSuggestion format for compatibility
        top_suggestions = []
        other_available = []
        conflicting_rooms = []

        for candidate in candidates:
            # Calculate additional compatibility metrics for RoomSuggestion format
            demanda = self.demanda_repo.get_by_id(demanda_id)
            if not demanda:
                continue

            # ✅ Trust scoring service results instead of re-checking rules
            # The scoring service already validated hard rules compliance
            hard_compliant = (
                bool(candidate.scoring_breakdown.hard_rules_satisfied)
                if candidate.scoring_breakdown
                else True
            )

            # Build violation messages from scoring breakdown
            rule_violations = []
            if (
                candidate.scoring_breakdown
                and not candidate.scoring_breakdown.hard_rules_satisfied
            ):
                # Get rules that were NOT satisfied
                hard_rules = self.regra_repo.find_rules_by_disciplina(
                    demanda.codigo_disciplina
                )
                hard_rules = [r for r in hard_rules if r.prioridade == 0]

                # If hard_rules_satisfied is empty list, all rules failed
                if (
                    isinstance(candidate.scoring_breakdown.hard_rules_satisfied, list)
                    and not candidate.scoring_breakdown.hard_rules_satisfied
                ):
                    for rule in hard_rules:
                        # Only add violations if description exists and has content
                        if rule.descricao and rule.descricao.strip():
                            # Avoid duplicate prefix if already in description
                            if rule.descricao.startswith("🔒 Obrigatório:"):
                                rule_violations.append(rule.descricao)
                            else:
                                rule_violations.append(
                                    f"🔒 Obrigatório: {rule.descricao}"
                                )

            # Generate detailed scoring breakdown for UI display
            breakdown_data = None
            if candidate.scoring_breakdown:
                breakdown_data = {
                    "capacity_points": candidate.scoring_breakdown.capacity_points,
                    "hard_rules_points": candidate.scoring_breakdown.hard_rules_points,
                    "soft_preference_points": candidate.scoring_breakdown.soft_preference_points,
                    "historical_frequency_points": candidate.scoring_breakdown.historical_frequency_points,
                    "capacity_satisfied": candidate.scoring_breakdown.capacity_satisfied,
                    "hard_rules_satisfied": candidate.scoring_breakdown.hard_rules_satisfied,
                    "soft_preferences_satisfied": candidate.scoring_breakdown.soft_preferences_satisfied,
                    "historical_allocations": candidate.scoring_breakdown.historical_allocations,
                }

            # Create RoomSuggestion object
            suggestion = RoomSuggestion(
                sala_id=candidate.sala.id,
                nome_sala=self._get_room_full_name(candidate.sala),
                tipo_sala_nome=self._get_room_type_name(candidate.sala.tipo_sala_id),
                capacidade=candidate.sala.capacidade or 0,
                andar=candidate.sala.andar,
                predio_nome=self._get_building_name(candidate.sala.predio_id),
                compatibility_score=candidate.score,
                hard_rules_compliant=hard_compliant,
                soft_preferences_compliant=(
                    bool(
                        candidate.scoring_breakdown
                        and candidate.scoring_breakdown.soft_preferences_satisfied
                    )
                    if candidate.scoring_breakdown
                    else True
                ),
                meets_capacity=(candidate.sala.capacidade or 0)
                >= demanda.vagas_disciplina,
                has_conflicts=candidate.has_conflicts,
                conflict_details=(
                    [
                        # Note: conflict_details need to be provided by RoomScoringService with more formatting
                        # For now, just indicate there are conflicts
                        "Conflito detectado neste horário"
                    ]
                    if candidate.has_conflicts
                    else []
                ),
                rule_violations=rule_violations,
                motivation_reason=(
                    self._generate_detailed_motivation_reason(
                        candidate.scoring_breakdown
                    )
                    if candidate.scoring_breakdown
                    else self._generate_motivation_reason(
                        hard_compliant,
                        True,  # soft preferences assumed
                        (candidate.sala.capacidade or 0) >= demanda.vagas_disciplina,
                        candidate.has_conflicts,
                    )
                ),
                scoring_breakdown=breakdown_data,
            )

            # Categorize based on conflicts and scoring
            if candidate.has_conflicts:
                conflicting_rooms.append(suggestion)
            else:
                # Prioritize top suggestions (highest scores first)
                if candidate.score >= 5:  # Good hard rule + soft rule match
                    top_suggestions.append(suggestion)
                else:
                    other_available.append(suggestion)

        # Sort by score (highest first) within each category
        top_suggestions.sort(key=lambda s: s.compatibility_score, reverse=True)
        other_available.sort(key=lambda s: s.compatibility_score, reverse=True)

        return AllocationSuggestions(
            demanda_id=demanda_id,
            top_suggestions=top_suggestions[:3],  # Limit to top 3
            other_available=other_available,
            conflicting_rooms=conflicting_rooms[
                :10
            ],  # Limit conflicting to avoid overload
        )

    def _manual_check_rule_compliance(self, demanda, room, rule) -> bool:
        """
        [DEPRECATED] Check rule compliance for RoomSuggestion creation.

        ⚠️ This method is no longer used. Rule compliance is now checked by
        RoomScoringService._check_rule_compliance() to avoid duplicate logic
        and data inconsistency issues.

        Kept for backward compatibility but should be removed in future refactor.
        """
        import json

        try:
            config = json.loads(rule.config_json)

            if rule.tipo_regra == "DISCIPLINA_TIPO_SALA":
                required_type_id = config.get("tipo_sala_id")
                return room.tipo_sala_id == required_type_id

            elif rule.tipo_regra == "DISCIPLINA_SALA":
                required_room_id = config.get("sala_id")
                return room.id == required_room_id

            elif rule.tipo_regra == "DISCIPLINA_CARACTERISTICA":
                required_char = config.get("caracteristica_nome")
                room_chars = self._get_room_characteristics(room.id)
                char_names = [self._get_characteristic_name(cid) for cid in room_chars]
                return required_char in char_names

        except (json.JSONDecodeError, KeyError):
            return False

        return True

    def _get_room_full_name(self, room) -> str:
        """Get room full name (building-room)."""
        building_name = self._get_building_name(room.predio_id)
        return f"{building_name}: {room.nome}"

    def _get_building_name(self, predio_id: int) -> str:
        """Get building name by ID."""
        if not predio_id:
            return "N/A"
        # Use direct query since we need to access predios table
        stmt = text("SELECT nome FROM predios WHERE id = :pid")
        row = self.session.execute(stmt, {"pid": predio_id}).fetchone()
        return row[0] if row else "N/A"

    def _get_room_type_name(self, tipo_sala_id: int) -> str:
        """Get room type name by ID."""
        if not tipo_sala_id:
            return "N/A"
        stmt = text("SELECT nome FROM tipos_sala WHERE id = :tid")
        row = self.session.execute(stmt, {"tid": tipo_sala_id}).fetchone()
        return row[0] if row else "N/A"

    def _get_characteristic_name(self, caracteristica_id: int) -> str:
        """Get characteristic name by ID."""
        stmt = text("SELECT nome FROM caracteristicas WHERE id = :cid")
        row = self.session.execute(stmt, {"cid": caracteristica_id}).fetchone()
        return row[0] if row else ""

    def _get_room_characteristics(self, sala_id: int):
        """Get characteristic IDs for a room."""
        stmt = text(
            "SELECT caracteristica_id FROM sala_caracteristicas WHERE sala_id = :sala_id"
        )
        rows = self.session.execute(stmt, {"sala_id": sala_id}).fetchall()
        return {row[0] for row in rows}

    def _generate_motivation_reason(
        self, hard_compliant, soft_compliant, meets_capacity, has_conflicts
    ) -> str:
        """Generate human-readable motivation for suggestion."""
        reasons = []

        if hard_compliant:
            reasons.append("Atende requisitos obrigatórios")
        else:
            reasons.append("Não atende todos os requisitos obrigatórios")

        if soft_compliant:
            reasons.append("Atende preferências do professor")

        if meets_capacity:
            reasons.append("Capacidade adequada")
        else:
            reasons.append("Capacidade insuficiente")

        if has_conflicts:
            reasons.append("Tem conflitos")

        return "; ".join(reasons) if reasons else "Avaliação neutra"

    def _generate_detailed_motivation_reason(self, breakdown) -> str:
        """
        Generate detailed, human-readable explanation of scoring breakdown.

        Shows exactly how each point was earned for maximum transparency.
        """
        if not breakdown:
            return "Avaliação padrão"

        parts = []

        # Capacity
        if breakdown.capacity_points > 0:
            parts.append("✅ Capacidade adequada (+1)")
        else:
            parts.append("❌ Capacidade insuficiente (+0)")

        # Hard rules
        if (
            isinstance(breakdown.hard_rules_satisfied, list)
            and breakdown.hard_rules_satisfied
        ):
            rules_text = "; ".join(breakdown.hard_rules_satisfied)
            parts.append(
                f"✅ Regras obrigatórias (+{breakdown.hard_rules_points}): {rules_text}"
            )
        elif breakdown.hard_rules_points == 0:
            parts.append("❌ Regras obrigatórias não atendidas (+0)")

        # Soft preferences (only if hard rules pass)
        if (
            breakdown.hard_rules_points > 0
            and isinstance(breakdown.soft_preferences_satisfied, list)
            and breakdown.soft_preferences_satisfied
        ):
            prefs_text = "; ".join(breakdown.soft_preferences_satisfied)
            parts.append(
                f"✅ Preferências do professor (+{breakdown.soft_preference_points}): {prefs_text}"
            )
        elif breakdown.hard_rules_points == 0:
            parts.append(
                "⏸️ Preferências não verificadas (regras obrigatórias falharam)"
            )

        # Historical frequency
        if breakdown.historical_frequency_points > 0:
            parts.append(
                f"📈 Disciplina já alocada aqui {breakdown.historical_allocations}x (+{breakdown.historical_frequency_points})"
            )
        else:
            parts.append("📉 Disciplina nunca alocada aqui (+0)")

        return " | ".join(parts)
