"""
REFACTORED Semester Service - Using Repository Pattern

This refactors SemesterService to use repositories.
Returns DTOs instead of detached ORM objects.

BEFORE (Returns detached ORM objects):
    def get_all_semestres() -> List[Semestre]:
        with DatabaseSession() as session:
            return session.query(Semestre).all()  # ❌ Returns detached!

AFTER (Returns DTOs - safe):
    def get_all_semestres() -> List[SemestreDTO]:
        return SemestreRepository.get_all_with_counts()  # ✅ Returns DTOs!
"""

import logging
from typing import List, Optional

from src.repositories.semestre import (
    get_semestre_repository,
    get_demanda_repository,
)
from src.schemas.semestre import (
    SemestreDTO,
    SemestreCreateDTO,
    SemestreUpdateDTO,
    DemandaDTO,
    DemandaCreateDTO,
    DemandaUpdateDTO,
)

logger = logging.getLogger(__name__)


class SemesterService:
    """
    Service class for semester management operations.

    This version uses the repository pattern to ensure:
    ✓ No detached ORM objects are returned
    ✓ All data is converted to DTOs at the boundary
    ✓ Clean separation of concerns
    ✓ Easy to test and maintain
    """

    # ===== SEMESTER OPERATIONS =====

    @classmethod
    def get_all_semestres(cls) -> List[SemestreDTO]:
        """
        Get all semesters with demand and allocation counts

        Returns:
            List of SemestreDTO objects (never detached ORM objects)
        """
        try:
            repo = get_semestre_repository()
            return repo.get_all_with_counts()
        except Exception as e:
            logger.exception(f"Error getting all semesters: {e}")
            return []

    @classmethod
    def get_semestre_by_id(cls, semestre_id: int) -> Optional[SemestreDTO]:
        """
        Get a semester by ID

        Args:
            semestre_id: Semester ID

        Returns:
            SemestreDTO or None if not found
        """
        try:
            repo = get_semestre_repository()
            return repo.get_by_id(semestre_id)
        except Exception as e:
            logger.exception(f"Error getting semester by ID {semestre_id}: {e}")
            return None

    @classmethod
    def get_semestre_by_name(cls, nome: str) -> Optional[SemestreDTO]:
        """
        Get a semester by name

        Args:
            nome: Semester name

        Returns:
            SemestreDTO or None if not found
        """
        try:
            repo = get_semestre_repository()
            return repo.get_by_name(nome)
        except Exception as e:
            logger.exception(f"Error getting semester by name '{nome}': {e}")
            return None

    @classmethod
    def get_semestre_by_status(cls, status: str) -> List[SemestreDTO]:
        """
        Get all semesters with a specific status

        Args:
            status: Semester status (PLANEJAMENTO, EXECUCAO, FINALIZADO)

        Returns:
            List of SemestreDTO objects
        """
        try:
            repo = get_semestre_repository()
            return repo.get_by_status(status)
        except Exception as e:
            logger.exception(f"Error getting semesters by status '{status}': {e}")
            return []

    @classmethod
    def get_current_semestre(cls) -> Optional[SemestreDTO]:
        """
        Get the current/active semester

        Returns:
            SemestreDTO or None if no active semester
        """
        try:
            repo = get_semestre_repository()
            return repo.get_current()
        except Exception as e:
            logger.exception(f"Error getting current semester: {e}")
            return None

    @classmethod
    def create_semestre(cls, semestre_data: SemestreCreateDTO) -> Optional[SemestreDTO]:
        """
        Create a new semester

        Args:
            semestre_data: SemestreCreateDTO with semester data

        Returns:
            Created SemestreDTO or None if error
        """
        try:
            repo = get_semestre_repository()
            return repo.create(semestre_data)
        except Exception as e:
            logger.exception(f"Error creating semester: {e}")
            return None

    @classmethod
    def update_semestre(
        cls, semestre_id: int, semestre_data: SemestreUpdateDTO
    ) -> Optional[SemestreDTO]:
        """
        Update a semester

        Args:
            semestre_id: Semester ID
            semestre_data: SemestreUpdateDTO with updated data

        Returns:
            Updated SemestreDTO or None if error
        """
        try:
            repo = get_semestre_repository()
            return repo.update(semestre_id, semestre_data)
        except Exception as e:
            logger.exception(f"Error updating semester {semestre_id}: {e}")
            return None

    @classmethod
    def delete_semestre(cls, semestre_id: int) -> bool:
        """
        Delete a semester

        Args:
            semestre_id: Semester ID

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = get_semestre_repository()
            return repo.delete(semestre_id)
        except Exception as e:
            logger.exception(f"Error deleting semester {semestre_id}: {e}")
            return False

    @classmethod
    def get_semestres_count(cls) -> int:
        """
        Get total count of semesters

        Returns:
            Count of semesters
        """
        try:
            repo = get_semestre_repository()
            return repo.count()
        except Exception as e:
            logger.exception(f"Error counting semesters: {e}")
            return 0

    # ===== DEMAND OPERATIONS =====

    @classmethod
    def get_all_demandas(cls) -> List[DemandaDTO]:
        """
        Get all demands

        Returns:
            List of DemandaDTO objects
        """
        try:
            repo = get_demanda_repository()
            return repo.get_all_with_eager_load()
        except Exception as e:
            logger.exception(f"Error getting all demands: {e}")
            return []

    @classmethod
    def get_demanda_by_id(cls, demanda_id: int) -> Optional[DemandaDTO]:
        """
        Get a demand by ID

        Args:
            demanda_id: Demand ID

        Returns:
            DemandaDTO or None if not found
        """
        try:
            repo = get_demanda_repository()
            return repo.get_by_id(demanda_id)
        except Exception as e:
            logger.exception(f"Error getting demand by ID {demanda_id}: {e}")
            return None

    @classmethod
    def get_demandas_by_semestre(cls, semestre_id: int) -> List[DemandaDTO]:
        """
        Get all demands for a specific semester

        Args:
            semestre_id: Semester ID

        Returns:
            List of DemandaDTO objects
        """
        try:
            repo = get_demanda_repository()
            return repo.get_by_semestre(semestre_id)
        except Exception as e:
            logger.exception(f"Error getting demands for semester {semestre_id}: {e}")
            return []

    @classmethod
    def get_demandas_by_professor(cls, usuario_id: int) -> List[DemandaDTO]:
        """
        Get all demands for a specific professor

        Args:
            usuario_id: Professor/User ID

        Returns:
            List of DemandaDTO objects
        """
        try:
            repo = get_demanda_repository()
            return repo.get_by_professor(usuario_id)
        except Exception as e:
            logger.exception(f"Error getting demands for professor {usuario_id}: {e}")
            return []

    @classmethod
    def get_demandas_by_status(cls, status: str) -> List[DemandaDTO]:
        """
        Get all demands with a specific status

        Args:
            status: Demand status

        Returns:
            List of DemandaDTO objects
        """
        try:
            repo = get_demanda_repository()
            return repo.get_by_status(status)
        except Exception as e:
            logger.exception(f"Error getting demands by status '{status}': {e}")
            return []

    @classmethod
    def create_demanda(cls, demanda_data: DemandaCreateDTO) -> Optional[DemandaDTO]:
        """
        Create a new demand

        Args:
            demanda_data: DemandaCreateDTO with demand data

        Returns:
            Created DemandaDTO or None if error
        """
        try:
            repo = get_demanda_repository()
            return repo.create(demanda_data)
        except Exception as e:
            logger.exception(f"Error creating demand: {e}")
            return None

    @classmethod
    def update_demanda(
        cls, demanda_id: int, demanda_data: DemandaUpdateDTO
    ) -> Optional[DemandaDTO]:
        """
        Update a demand

        Args:
            demanda_id: Demand ID
            demanda_data: DemandaUpdateDTO with updated data

        Returns:
            Updated DemandaDTO or None if error
        """
        try:
            repo = get_demanda_repository()
            return repo.update(demanda_id, demanda_data)
        except Exception as e:
            logger.exception(f"Error updating demand {demanda_id}: {e}")
            return None

    @classmethod
    def delete_demanda(cls, demanda_id: int) -> bool:
        """
        Delete a demand

        Args:
            demanda_id: Demand ID

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = get_demanda_repository()
            return repo.delete(demanda_id)
        except Exception as e:
            logger.exception(f"Error deleting demand {demanda_id}: {e}")
            return False

    @classmethod
    def get_demandas_count(cls) -> int:
        """
        Get total count of demands

        Returns:
            Count of demands
        """
        try:
            repo = get_demanda_repository()
            return repo.count()
        except Exception as e:
            logger.exception(f"Error counting demands: {e}")
            return 0


# ===== CONVENIENCE FUNCTION =====


def get_semester_service() -> SemesterService:
    """Get the semester service"""
    return SemesterService()
