"""
Generic repository base class using Repository Pattern with DTOs.

Provides template for all repository subclasses with generic CRUD operations.
"""

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

# Generic types
T = TypeVar("T")  # ORM Model type
D = TypeVar("D")  # DTO type


class BaseRepository(Generic[T, D]):
    """
    Generic repository base class for Repository Pattern.

    Parameters:
    - T: ORM model type (e.g., Sala)
    - D: DTO type (e.g., SalaDTO)

    All repository subclasses inherit from this and implement:
    - orm_to_dto(orm_obj) -> D: Convert ORM model to DTO
    - dto_to_orm_create(dto) -> T: Convert DTO to ORM model for creation
    """

    def __init__(self, session: Session, model_class: Type[T]):
        """
        Initialize repository.

        Args:
            session: SQLAlchemy session
            model_class: ORM model class
        """
        self.session = session
        self.model_class = model_class

    def orm_to_dto(self, orm_obj: T) -> D:
        """
        Convert ORM model to DTO.

        Subclasses must implement this method.

        Args:
            orm_obj: ORM model instance

        Returns:
            DTO instance
        """
        raise NotImplementedError("Subclasses must implement orm_to_dto()")

    def dto_to_orm_create(self, dto: D) -> T:
        """
        Convert DTO to ORM model for creation.

        Subclasses must implement this method.

        Args:
            dto: DTO instance

        Returns:
            ORM model instance
        """
        raise NotImplementedError("Subclasses must implement dto_to_orm_create()")

    def get_by_id(self, id: int) -> Optional[D]:
        """
        Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            DTO or None if not found
        """
        orm_obj = (
            self.session.query(self.model_class)
            .filter(self.model_class.id == id)
            .first()
        )
        if orm_obj:
            return self.orm_to_dto(orm_obj)
        return None

    def get_all(self) -> List[D]:
        """
        Get all entities.

        Returns:
            List of DTOs
        """
        orm_objs = self.session.query(self.model_class).all()
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def create(self, dto: D) -> D:
        """
        Create new entity.

        Args:
            dto: DTO with entity data

        Returns:
            Created DTO with ID
        """
        orm_obj = self.dto_to_orm_create(dto)
        self.session.add(orm_obj)
        self.session.commit()
        self.session.refresh(orm_obj)
        return self.orm_to_dto(orm_obj)

    def update(self, id: int, dto: D) -> Optional[D]:
        """
        Update existing entity.

        Args:
            id: Entity ID
            dto: DTO with updated data

        Returns:
            Updated DTO or None if not found
        """
        orm_obj = (
            self.session.query(self.model_class)
            .filter(self.model_class.id == id)
            .first()
        )
        if not orm_obj:
            return None

        # Update attributes from DTO
        for key, value in dto.model_dump(
            exclude_unset=True, exclude={"id", "created_at", "updated_at"}
        ).items():
            if hasattr(orm_obj, key):
                setattr(orm_obj, key, value)

        self.session.commit()
        self.session.refresh(orm_obj)
        return self.orm_to_dto(orm_obj)

    def delete(self, id: int) -> bool:
        """
        Delete entity.

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        orm_obj = (
            self.session.query(self.model_class)
            .filter(self.model_class.id == id)
            .first()
        )
        if not orm_obj:
            return False

        self.session.delete(orm_obj)
        self.session.commit()
        return True

    def delete_all(self) -> int:
        """
        Delete all entities (useful for testing).

        Returns:
            Number of entities deleted
        """
        count = self.session.query(self.model_class).delete()
        self.session.commit()
        return count
