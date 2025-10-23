"""Service for executing manual allocation operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.schemas.manual_allocation import AllocationResult, ConflictDetail
from src.repositories.alocacao import AlocacaoRepository
from src.repositories.disciplina import DisciplinaRepository
from src.repositories.reserva import ReservaRepository
from src.repositories.semestre import SemestreRepository
from src.schemas.allocation import AlocacaoSemestralCreate
from src.utils.sigaa_parser import SigaaScheduleParser
from src.services.allocation_suggestions import AllocationSuggestionsService


class ManualAllocationService:
    """Service for manual allocation execution with conflict detection."""

    def __init__(self, session: Session):
        """Initialize service with repositories."""
        self.session = session
        self.alocacao_repo = AlocacaoRepository(session)
        self.demanda_repo = DisciplinaRepository(session)
        self.semestre_repo = SemestreRepository(session)
        self.reserva_repo = ReservaRepository(session)
        self.parser = SigaaScheduleParser()
        self.suggestions_service = AllocationSuggestionsService(session)

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
            # Check if there's already an allocation for this time slot
            has_conflict = self.alocacao_repo.check_conflict(
                sala_id, dia_sigaa, bloco_codigo
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

    def get_suggestions_for_demand(self, demanda_id: int, semester_id: int):
        """Get room suggestions for a specific demand."""
        return self.suggestions_service.calculate_suggestions(demanda_id, semester_id)
