"""
Repository for Campus operations.

Provides data access methods for campus queries.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.inventory import Campus
from src.schemas.inventory import CampusRead, CampusCreate
from src.repositories.base import BaseRepository


class CampusRepository(BaseRepository[Campus, CampusRead]):
    """Repository for Campus CRUD operations."""

    def __init__(self, session: Session):
        """Initialize CampusRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, Campus)

    def orm_to_dto(self, orm_obj: Campus) -> CampusRead:
        """Convert ORM Campus model to CampusRead DTO.

        Args:
            orm_obj: Campus ORM model instance

        Returns:
            CampusRead DTO
        """
        return CampusRead(
            id=orm_obj.id,
            nome=orm_obj.nome,
            descricao=orm_obj.descricao,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: CampusCreate) -> Campus:
        """Convert CampusCreate DTO to ORM Campus model for creation.

        Args:
            dto: CampusCreate DTO

        Returns:
            Campus ORM model instance (not persisted)
        """
        return Campus(
            nome=dto.nome,
            descricao=dto.descricao if hasattr(dto, "descricao") else None,
        )
