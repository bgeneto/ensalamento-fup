"""
Base repository class for all data access operations

This provides a foundation for all repository implementations with:
- Common CRUD operations
- Proper session management
- Error handling
- Logging
- Type safety
"""

import logging
from typing import TypeVar, Generic, List, Optional, Type, Any
from abc import ABC, abstractmethod
from database import DatabaseSession
from sqlalchemy.orm import Session
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Type variables for generic repository
T = TypeVar("T")  # ORM model type
D = TypeVar("D", bound=BaseModel)  # DTO type


class BaseRepository(ABC, Generic[T, D]):
    """
    Abstract base repository providing common CRUD operations.

    Subclasses must implement:
    - orm_to_dto(): Convert ORM model to DTO
    - get_orm_model(): Return the ORM model class
    """

    @property
    @abstractmethod
    def orm_model(self) -> Type[T]:
        """Return the ORM model class"""
        pass

    @abstractmethod
    def orm_to_dto(self, orm_obj: T) -> D:
        """Convert ORM model instance to DTO"""
        pass

    @abstractmethod
    def dto_to_orm_create(self, dto: BaseModel) -> dict:
        """Convert create DTO to ORM constructor kwargs"""
        pass

    # ===== CREATE OPERATIONS =====

    def create(self, dto: D) -> Optional[D]:
        """
        Create a new record from DTO

        Args:
            dto: Data transfer object with creation data

        Returns:
            DTO of created object, or None if error
        """
        try:
            with DatabaseSession() as session:
                # Convert DTO to ORM kwargs
                orm_data = self.dto_to_orm_create(dto)

                # Create ORM instance
                orm_obj = self.orm_model(**orm_data)

                # Save
                session.add(orm_obj)
                session.flush()  # Get the ID

                # Convert back to DTO and return
                return self.orm_to_dto(orm_obj)

        except Exception as e:
            logger.exception(f"Error creating {self.orm_model.__name__}: {e}")
            return None

    # ===== READ OPERATIONS =====

    def get_by_id(self, obj_id: int) -> Optional[D]:
        """
        Get a record by ID

        Args:
            obj_id: The primary key

        Returns:
            DTO or None if not found
        """
        try:
            with DatabaseSession() as session:
                orm_obj = (
                    session.query(self.orm_model)
                    .filter(self.orm_model.id == obj_id)
                    .first()
                )

                if orm_obj:
                    return self.orm_to_dto(orm_obj)
                return None

        except Exception as e:
            logger.exception(
                f"Error getting {self.orm_model.__name__} by ID {obj_id}: {e}"
            )
            return None

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[D]:
        """
        Get all records (with optional pagination)

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of DTOs
        """
        try:
            with DatabaseSession() as session:
                query = session.query(self.orm_model)

                if offset > 0:
                    query = query.offset(offset)

                if limit:
                    query = query.limit(limit)

                orm_objs = query.all()

                # Convert all to DTOs while still in session
                return [self.orm_to_dto(obj) for obj in orm_objs]

        except Exception as e:
            logger.exception(f"Error getting all {self.orm_model.__name__}: {e}")
            return []

    # ===== UPDATE OPERATIONS =====

    def update(self, obj_id: int, dto_data: BaseModel) -> Optional[D]:
        """
        Update a record

        Args:
            obj_id: The primary key
            dto_data: DTO with updated data

        Returns:
            DTO of updated object, or None if error
        """
        try:
            with DatabaseSession() as session:
                orm_obj = (
                    session.query(self.orm_model)
                    .filter(self.orm_model.id == obj_id)
                    .first()
                )

                if not orm_obj:
                    logger.warning(
                        f"Record not found: {self.orm_model.__name__} ID {obj_id}"
                    )
                    return None

                # Update fields from DTO
                for field, value in dto_data.dict(exclude_unset=True).items():
                    if hasattr(orm_obj, field) and value is not None:
                        setattr(orm_obj, field, value)

                session.flush()

                return self.orm_to_dto(orm_obj)

        except Exception as e:
            logger.exception(
                f"Error updating {self.orm_model.__name__} ID {obj_id}: {e}"
            )
            return None

    # ===== DELETE OPERATIONS =====

    def delete(self, obj_id: int) -> bool:
        """
        Delete a record by ID

        Args:
            obj_id: The primary key

        Returns:
            True if deleted, False if not found or error
        """
        try:
            with DatabaseSession() as session:
                orm_obj = (
                    session.query(self.orm_model)
                    .filter(self.orm_model.id == obj_id)
                    .first()
                )

                if not orm_obj:
                    logger.warning(
                        f"Record not found for deletion: {self.orm_model.__name__} ID {obj_id}"
                    )
                    return False

                session.delete(orm_obj)
                return True

        except Exception as e:
            logger.exception(
                f"Error deleting {self.orm_model.__name__} ID {obj_id}: {e}"
            )
            return False

    # ===== COUNT OPERATIONS =====

    def count(self) -> int:
        """
        Count total records

        Returns:
            Total count
        """
        try:
            with DatabaseSession() as session:
                return session.query(self.orm_model).count()
        except Exception as e:
            logger.exception(f"Error counting {self.orm_model.__name__}: {e}")
            return 0

    def count_where(self, **filters) -> int:
        """
        Count records matching filters

        Args:
            **filters: Field=value pairs for WHERE clause

        Returns:
            Count of matching records
        """
        try:
            with DatabaseSession() as session:
                query = session.query(self.orm_model)

                for field, value in filters.items():
                    if hasattr(self.orm_model, field):
                        query = query.filter(getattr(self.orm_model, field) == value)

                return query.count()

        except Exception as e:
            logger.exception(f"Error counting {self.orm_model.__name__}: {e}")
            return 0

    # ===== UTILITY METHODS =====

    def exists(self, obj_id: int) -> bool:
        """Check if a record exists"""
        return self.count_where(id=obj_id) > 0

    def exists_where(self, **filters) -> bool:
        """Check if any record matches the filters"""
        return self.count_where(**filters) > 0

    def get_first(self) -> Optional[D]:
        """Get the first record"""
        try:
            with DatabaseSession() as session:
                orm_obj = session.query(self.orm_model).first()
                if orm_obj:
                    return self.orm_to_dto(orm_obj)
                return None
        except Exception as e:
            logger.exception(f"Error getting first {self.orm_model.__name__}: {e}")
            return None

    # ===== ERROR HANDLING =====

    def handle_error(self, message: str, exception: Exception = None) -> None:
        """
        Centralized error handling

        Args:
            message: Error message
            exception: Exception object (optional)
        """
        if exception:
            logger.exception(f"{message}: {exception}")
        else:
            logger.error(message)

    # ===== BULK OPERATIONS =====

    def get_multiple(self, ids: List[int]) -> List[D]:
        """
        Get multiple records by IDs

        Args:
            ids: List of primary keys

        Returns:
            List of DTOs
        """
        try:
            with DatabaseSession() as session:
                orm_objs = (
                    session.query(self.orm_model)
                    .filter(self.orm_model.id.in_(ids))
                    .all()
                )

                return [self.orm_to_dto(obj) for obj in orm_objs]

        except Exception as e:
            logger.exception(f"Error getting multiple {self.orm_model.__name__}: {e}")
            return []

    def delete_multiple(self, ids: List[int]) -> bool:
        """
        Delete multiple records

        Args:
            ids: List of primary keys

        Returns:
            True if successful, False if error
        """
        try:
            with DatabaseSession() as session:
                session.query(self.orm_model).filter(
                    self.orm_model.id.in_(ids)
                ).delete()
                return True

        except Exception as e:
            logger.exception(f"Error deleting multiple {self.orm_model.__name__}: {e}")
            return False
