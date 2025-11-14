"""
Repository for DiaSemana (Weekday) operations.

Provides data access methods for weekday queries.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.horario import DiaSemana
from src.schemas.horario import DiaSemanaRead, DiaSemanaCreate
from src.repositories.base import BaseRepository


class DiaSemanaRepository(BaseRepository[DiaSemana, DiaSemanaRead]):
    """Repository for DiaSemana CRUD and queries."""

    def __init__(self, session: Session):
        """Initialize DiaSemanaRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, DiaSemana)

    def orm_to_dto(self, orm_obj: DiaSemana) -> DiaSemanaRead:
        """Convert ORM DiaSemana model to DiaSemanaRead DTO.

        Args:
            orm_obj: DiaSemana ORM model instance

        Returns:
            DiaSemanaRead DTO
        """
        return DiaSemanaRead(
            id_sigaa=orm_obj.id_sigaa,
            nome=orm_obj.nome,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: DiaSemanaCreate) -> DiaSemana:
        """Convert DiaSemanaCreate DTO to ORM DiaSemana model for creation.

        Args:
            dto: DiaSemanaCreate DTO

        Returns:
            DiaSemana ORM model instance (not persisted)
        """
        return DiaSemana(
            id_sigaa=dto.id_sigaa,
            nome=dto.nome,
        )

    # ========================================================================
    # DOMAIN-SPECIFIC QUERY METHODS
    # ========================================================================

    def get_by_id_sigaa(self, id_sigaa: int) -> Optional[DiaSemanaRead]:
        """Get weekday by SIGAA ID (2-7).

        Args:
            id_sigaa: SIGAA weekday ID (2=Monday, 7=Saturday)

        Returns:
            DiaSemanaRead DTO or None if not found
        """
        orm_obj = (
            self.session.query(DiaSemana).filter(DiaSemana.id_sigaa == id_sigaa).first()
        )
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def get_by_nome(self, nome: str) -> Optional[DiaSemanaRead]:
        """Get weekday by name (SEG, TER, QUA, QUI, SEX, SAB).

        Args:
            nome: Weekday name (3-letter abbreviation)

        Returns:
            DiaSemanaRead DTO or None if not found
        """
        orm_obj = self.session.query(DiaSemana).filter(DiaSemana.nome == nome).first()
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def get_weekdays_only(self) -> List[DiaSemanaRead]:
        """Get weekdays only (Monday-Friday), sorted by SIGAA ID.

        Returns:
            List of DiaSemanaRead DTOs (5 items: SIGAA IDs 2-6)
        """
        orm_objs = (
            self.session.query(DiaSemana)
            .filter(DiaSemana.id_sigaa < 7)
            .order_by(DiaSemana.id_sigaa)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_all_ordered(self) -> List[DiaSemanaRead]:
        """Get all weekdays ordered by SIGAA ID.

        Returns:
            List of DiaSemanaRead DTOs sorted by SIGAA ID
        """
        orm_objs = self.session.query(DiaSemana).order_by(DiaSemana.id_sigaa).all()
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_dict_by_id_sigaa(self) -> dict:
        """Get all weekdays as dictionary with id_sigaa as key.

        Returns:
            Dictionary mapping id_sigaa -> DiaSemanaRead DTO
        """
        dias = self.get_all()
        return {dia.id_sigaa: dia for dia in dias}

    def get_dict_by_nome(self) -> dict:
        """Get all weekdays as dictionary with nome as key.

        Returns:
            Dictionary mapping nome -> DiaSemanaRead DTO
        """
        dias = self.get_all()
        return {dia.nome: dia for dia in dias}
