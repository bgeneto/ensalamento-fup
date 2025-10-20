"""
Repository for TipoSala operations.

Provides data access methods for room type queries.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.inventory import TipoSala
from src.schemas.inventory import TipoSalaRead, TipoSalaCreate
from src.repositories.base import BaseRepository


class TipoSalaRepository(BaseRepository[TipoSala, TipoSalaRead]):
    """Repository for TipoSala CRUD operations."""

    def __init__(self, session: Session):
        """Initialize TipoSalaRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, TipoSala)

    def orm_to_dto(self, orm_obj: TipoSala) -> TipoSalaRead:
        """Convert ORM TipoSala model to TipoSalaRead DTO.

        Args:
            orm_obj: TipoSala ORM model instance

        Returns:
            TipoSalaRead DTO
        """
        return TipoSalaRead(
            id=orm_obj.id,
            nome=orm_obj.nome,
            descricao=orm_obj.descricao,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: TipoSalaCreate) -> TipoSala:
        """Convert TipoSalaCreate DTO to ORM TipoSala model for creation.

        Args:
            dto: TipoSalaCreate DTO

        Returns:
            TipoSala ORM model instance (not persisted)
        """
        return TipoSala(
            nome=dto.nome,
            descricao=dto.descricao,
        )
