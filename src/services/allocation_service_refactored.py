"""
REFACTORED Allocation Service - Using Repository Pattern

This refactors AllocationService to use repositories.
Returns DTOs instead of detached ORM objects.

BEFORE (Returns detached ORM objects):
    def get_allocations() -> List[AlocacaoSemestral]:
        with DatabaseSession() as session:
            return session.query(AlocacaoSemestral).all()  # ❌ Returns detached!

AFTER (Returns DTOs - safe):
    def get_allocations() -> List[AlocacaoSemestralDTO]:
        return AlocacaoRepository.get_all_with_eager_load()  # ✅ Returns DTOs!
"""

import logging
from typing import List, Optional, Dict, Any

from src.repositories.alocacao import get_alocacao_repository
from src.repositories.sala import get_sala_repository
from src.repositories.semestre import get_semestre_repository, get_demanda_repository
from src.schemas.alocacao import (
    AlocacaoSemestralDTO,
    AlocacaoCreateDTO,
    AlocacaoUpdateDTO,
    DemandaDTO,
)
from src.schemas.sala import SalaDTO
from src.schemas.semestre import SemestreDTO

logger = logging.getLogger(__name__)


class AllocationService:
    """
    Service class for room allocation operations.

    This version uses the repository pattern to ensure:
    ✓ No detached ORM objects are returned
    ✓ All data is converted to DTOs at the boundary
    ✓ Clean separation of concerns
    ✓ Easy to test and maintain
    """

    # ===== ALLOCATION OPERATIONS =====

    @classmethod
    def get_all_allocations(cls) -> List[AlocacaoSemestralDTO]:
        """
        Get all room allocations

        Returns:
            List of AlocacaoSemestralDTO objects (never detached ORM objects)
        """
        try:
            repo = get_alocacao_repository()
            return repo.get_all_with_eager_load()
        except Exception as e:
            logger.exception(f"Error getting all allocations: {e}")
            return []

    @classmethod
    def get_allocation_by_id(cls, alocacao_id: int) -> Optional[AlocacaoSemestralDTO]:
        """
        Get an allocation by ID

        Args:
            alocacao_id: Allocation ID

        Returns:
            AlocacaoSemestralDTO or None if not found
        """
        try:
            repo = get_alocacao_repository()
            return repo.get_by_id(alocacao_id)
        except Exception as e:
            logger.exception(f"Error getting allocation by ID {alocacao_id}: {e}")
            return None

    @classmethod
    def get_allocations_by_sala(cls, sala_id: int) -> List[AlocacaoSemestralDTO]:
        """
        Get all allocations for a specific room

        Args:
            sala_id: Room ID

        Returns:
            List of AlocacaoSemestralDTO objects
        """
        try:
            repo = get_alocacao_repository()
            return repo.get_by_sala(sala_id)
        except Exception as e:
            logger.exception(f"Error getting allocations for room {sala_id}: {e}")
            return []

    @classmethod
    def get_allocations_by_demanda(cls, demanda_id: int) -> List[AlocacaoSemestralDTO]:
        """
        Get all allocations for a specific demand

        Args:
            demanda_id: Demand ID

        Returns:
            List of AlocacaoSemestralDTO objects
        """
        try:
            repo = get_alocacao_repository()
            return repo.get_by_demanda(demanda_id)
        except Exception as e:
            logger.exception(f"Error getting allocations for demand {demanda_id}: {e}")
            return []

    @classmethod
    def get_allocations_by_semestre(
        cls, semestre_id: int
    ) -> List[AlocacaoSemestralDTO]:
        """
        Get all allocations for a specific semester

        Args:
            semestre_id: Semester ID

        Returns:
            List of AlocacaoSemestralDTO objects
        """
        try:
            repo = get_alocacao_repository()
            return repo.get_by_semestre(semestre_id)
        except Exception as e:
            logger.exception(
                f"Error getting allocations for semester {semestre_id}: {e}"
            )
            return []

    @classmethod
    def check_allocation_conflict(
        cls,
        sala_id: int,
        dia_semana_id: int,
        codigo_bloco: str,
        semestre_id: int,
        exclude_alocacao_id: Optional[int] = None,
    ) -> bool:
        """
        Check if there's a conflict for the given time slot in the room

        Args:
            sala_id: Room ID
            dia_semana_id: Day of week ID
            codigo_bloco: Time block code
            semestre_id: Semester ID
            exclude_alocacao_id: Allocation ID to exclude from conflict check (for updates)

        Returns:
            True if conflict exists, False otherwise
        """
        try:
            repo = get_alocacao_repository()
            return repo.check_conflict(
                sala_id, dia_semana_id, codigo_bloco, semestre_id, exclude_alocacao_id
            )
        except Exception as e:
            logger.exception(f"Error checking allocation conflict: {e}")
            return False

    @classmethod
    def create_allocation(
        cls, allocation_data: AlocacaoCreateDTO
    ) -> Optional[AlocacaoSemestralDTO]:
        """
        Create a new allocation

        Args:
            allocation_data: AlocacaoCreateDTO with allocation data

        Returns:
            Created AlocacaoSemestralDTO or None if error
        """
        try:
            repo = get_alocacao_repository()
            return repo.create(allocation_data)
        except Exception as e:
            logger.exception(f"Error creating allocation: {e}")
            return None

    @classmethod
    def update_allocation(
        cls, alocacao_id: int, allocation_data: AlocacaoUpdateDTO
    ) -> Optional[AlocacaoSemestralDTO]:
        """
        Update an allocation

        Args:
            alocacao_id: Allocation ID
            allocation_data: AlocacaoUpdateDTO with updated data

        Returns:
            Updated AlocacaoSemestralDTO or None if error
        """
        try:
            repo = get_alocacao_repository()
            return repo.update(alocacao_id, allocation_data)
        except Exception as e:
            logger.exception(f"Error updating allocation {alocacao_id}: {e}")
            return None

    @classmethod
    def delete_allocation(cls, alocacao_id: int) -> bool:
        """
        Delete an allocation

        Args:
            alocacao_id: Allocation ID

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = get_alocacao_repository()
            return repo.delete(alocacao_id)
        except Exception as e:
            logger.exception(f"Error deleting allocation {alocacao_id}: {e}")
            return False

    @classmethod
    def get_allocations_count(cls) -> int:
        """
        Get total count of allocations

        Returns:
            Count of allocations
        """
        try:
            repo = get_alocacao_repository()
            return repo.count()
        except Exception as e:
            logger.exception(f"Error counting allocations: {e}")
            return 0

    @classmethod
    def get_available_rooms(
        cls, semestre_id: int, dia_semana_id: int, codigo_bloco: str
    ) -> List[SalaDTO]:
        """
        Get available rooms for a specific time slot

        Args:
            semestre_id: Semester ID
            dia_semana_id: Day of week ID
            codigo_bloco: Time block code

        Returns:
            List of available SalaDTO objects
        """
        try:
            # Get all allocations for this time slot
            alocacao_repo = get_alocacao_repository()
            allocations = alocacao_repo.get_by_time_slot(
                dia_semana_id, codigo_bloco, semestre_id
            )
            allocated_sala_ids = {a.sala_id for a in allocations}

            # Get all rooms and filter out allocated ones
            sala_repo = get_sala_repository()
            all_rooms = sala_repo.get_all_with_eager_load()

            return [room for room in all_rooms if room.id not in allocated_sala_ids]
        except Exception as e:
            logger.exception(f"Error getting available rooms: {e}")
            return []

    # ===== UTILITY METHODS =====

    @classmethod
    def find_suitable_rooms(
        cls, demanda: DemandaDTO, exclude_allocated: bool = True
    ) -> List[SalaDTO]:
        """
        Find suitable rooms for a specific demand

        Args:
            demanda: DemandaDTO object
            exclude_allocated: Whether to exclude already allocated rooms

        Returns:
            List of suitable SalaDTO objects
        """
        try:
            sala_repo = get_sala_repository()
            all_rooms = sala_repo.get_all_with_eager_load()

            suitable_rooms = []
            for room in all_rooms:
                # Filter by capacity
                if room.capacidade < demanda.vagas_disciplina:
                    continue

                if exclude_allocated:
                    # Check if room is available for all time slots in demand schedule
                    is_available = True
                    # TODO: Implement schedule conflict checking with demanda.horario_sigaa_bruto
                    if not is_available:
                        continue

                suitable_rooms.append(room)

            return suitable_rooms
        except Exception as e:
            logger.exception(f"Error finding suitable rooms: {e}")
            return []


# ===== CONVENIENCE FUNCTION =====


def get_allocation_service() -> AllocationService:
    """Get the allocation service"""
    return AllocationService()
