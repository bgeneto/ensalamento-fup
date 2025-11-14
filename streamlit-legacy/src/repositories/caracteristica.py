"""
Repository for Caracteristica operations.

Provides data access methods for room characteristic queries.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.inventory import Caracteristica
from src.schemas.inventory import CaracteristicaRead, CaracteristicaCreate
from src.repositories.base import BaseRepository


class CaracteristicaRepository(BaseRepository[Caracteristica, CaracteristicaRead]):
    """Repository for Caracteristica CRUD operations."""

    def __init__(self, session: Session):
        """Initialize CaracteristicaRepository.

        Args:
            session: SQLAlchemy session
        """
        super().__init__(session, Caracteristica)

    def orm_to_dto(self, orm_obj: Caracteristica) -> CaracteristicaRead:
        """Convert ORM Caracteristica model to CaracteristicaRead DTO.

        Args:
            orm_obj: Caracteristica ORM model instance

        Returns:
            CaracteristicaRead DTO
        """
        return CaracteristicaRead(
            id=orm_obj.id,
            nome=orm_obj.nome,
            descricao=None,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def dto_to_orm_create(self, dto: CaracteristicaCreate) -> Caracteristica:
        """Convert CaracteristicaCreate DTO to ORM Caracteristica model for creation.

        Args:
            dto: CaracteristicaCreate DTO

        Returns:
            Caracteristica ORM model instance (not persisted)
        """
        return Caracteristica(nome=dto.nome)
