"""
Repository for Predio (Building) operations.

Provides data access methods for building queries.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.inventory import Predio
from src.schemas.inventory import PredioRead, PredioCreate
from src.repositories.base import BaseRepository


class PredioRepository(BaseRepository[Predio, PredioRead]):
    """Repository for Predio (building) CRUD operations."""

    def __init__(self, session: Session):
        """Initialize PredioRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, Predio)

    def orm_to_dto(self, orm_obj: Predio) -> PredioRead:
        """Convert ORM Predio model to PredioRead DTO.

        Args:
            orm_obj: Predio ORM model instance

        Returns:
            PredioRead DTO
        """
        return PredioRead(
            id=orm_obj.id,
            nome=orm_obj.nome,
            descricao=orm_obj.descricao,  # Required field, should not be None in DB
            campus_id=orm_obj.campus_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: PredioCreate) -> Predio:
        """Convert PredioCreate DTO to ORM Predio model for creation.

        Args:
            dto: PredioCreate DTO

        Returns:
            Predio ORM model instance (not persisted)
        """
        return Predio(
            nome=dto.nome,
            descricao=dto.descricao,
            campus_id=dto.campus_id,
        )

    def get_by_campus(self, campus_id: int) -> List[PredioRead]:
        """Get all buildings in a specific campus.

        Args:
            campus_id: Campus ID

        Returns:
            List of PredioRead DTOs sorted by building name
        """
        orm_objs = (
            self.session.query(Predio)
            .filter(Predio.campus_id == campus_id)
            .order_by(Predio.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]
