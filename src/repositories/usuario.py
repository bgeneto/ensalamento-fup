"""
Repository for user management (Usuario)

Implements the Repository pattern for user data access,
providing a clean abstraction over database operations with
proper session management and ORM ↔ DTO conversion.
"""

import logging
from typing import List, Optional

from database import DatabaseSession, Usuario as UsuarioORM
from src.repositories.base import BaseRepository
from src.schemas.usuario import (
    UsuarioDTO,
    UsuarioCreateDTO,
    UsuarioUpdateDTO,
    UsuarioSimplifiedDTO,
)

logger = logging.getLogger(__name__)


class UsuarioRepository(BaseRepository[UsuarioORM, UsuarioDTO]):
    """
    Repository for user operations.

    Provides CRUD operations and custom queries for users,
    with automatic ORM ↔ DTO conversion at session boundaries.

    Usage:
        repo = UsuarioRepository()
        users = repo.get_all()
        for user in users:
            print(f"{user.nome_completo} ({user.role})")
    """

    @property
    def orm_model(self) -> type:
        """Return the ORM model class"""
        return UsuarioORM

    def orm_to_dto(self, orm_obj: UsuarioORM) -> UsuarioDTO:
        """
        Convert ORM object to DTO.

        Note: Password hash is NOT included in DTO for security.

        Args:
            orm_obj: SQLAlchemy ORM model instance

        Returns:
            UsuarioDTO: Data transfer object (without password)
        """
        try:
            return UsuarioDTO(
                username=orm_obj.username,
                nome_completo=orm_obj.nome_completo,
                role=orm_obj.role,
                # Intentionally NOT including password_hash for security
            )
        except Exception as e:
            logger.error(f"Error converting Usuario to DTO: {e}", exc_info=True)
            return UsuarioDTO(
                username=orm_obj.username,
                role="professor",
            )

    def dto_to_orm_create(self, dto: UsuarioCreateDTO) -> dict:
        """
        Convert create DTO to ORM constructor kwargs.

        Note: Password must be hashed before storage.
        This method expects the password to already be hashed.

        Args:
            dto: UsuarioCreateDTO with creation data

        Returns:
            dict: Kwargs for ORM model constructor
        """
        return {
            "username": dto.username,
            "nome_completo": dto.nome_completo,
            "role": dto.role,
            # password_hash should be set separately after hashing
        }

    def get_by_username(self, username: str) -> Optional[UsuarioDTO]:
        """
        Get a user by username.

        Args:
            username: Username to search for

        Returns:
            Optional[UsuarioDTO]: User DTO if found, None otherwise

        Example:
            user = repo.get_by_username("professor01")
            if user:
                print(f"Found: {user.nome_completo}")
        """
        try:
            with DatabaseSession() as session:
                orm_obj = (
                    session.query(self.orm_model)
                    .filter(UsuarioORM.username == username)
                    .first()
                )

                if orm_obj:
                    return self.orm_to_dto(orm_obj)
                return None
        except Exception as e:
            logger.error(
                f"Error getting user by username {username}: {e}", exc_info=True
            )
            return None

    def get_by_role(self, role: str) -> List[UsuarioDTO]:
        """
        Get all users with a specific role.

        Args:
            role: Role to filter by (e.g., "admin", "professor")

        Returns:
            List[UsuarioDTO]: Users with the specified role

        Example:
            admins = repo.get_by_role("admin")
        """
        try:
            with DatabaseSession() as session:
                orm_objs = (
                    session.query(self.orm_model).filter(UsuarioORM.role == role).all()
                )

                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(f"Error getting users by role {role}: {e}", exc_info=True)
            return []

    def get_all_simplified(self) -> List[UsuarioSimplifiedDTO]:
        """
        Get all users in simplified format (for dropdowns/lists).

        Returns much less data than full DTOs.

        Returns:
            List[UsuarioSimplifiedDTO]: Simplified user list
        """
        try:
            with DatabaseSession() as session:
                orm_objs = session.query(self.orm_model).all()

                return [
                    UsuarioSimplifiedDTO(
                        username=obj.username,
                        nome_completo=obj.nome_completo or obj.username,
                        role=obj.role,
                    )
                    for obj in orm_objs
                ]
        except Exception as e:
            logger.error(f"Error getting simplified users: {e}", exc_info=True)
            return []

    def exists_username(self, username: str) -> bool:
        """
        Check if a username exists.

        Args:
            username: Username to check

        Returns:
            bool: True if username exists, False otherwise
        """
        try:
            with DatabaseSession() as session:
                return (
                    session.query(self.orm_model)
                    .filter(UsuarioORM.username == username)
                    .first()
                ) is not None
        except Exception as e:
            logger.error(f"Error checking username existence: {e}", exc_info=True)
            return False

    def get_admin_count(self) -> int:
        """
        Get the number of admin users.

        Returns:
            int: Number of admins (0 if error)
        """
        try:
            with DatabaseSession() as session:
                return (
                    session.query(self.orm_model)
                    .filter(UsuarioORM.role == "admin")
                    .count()
                )
        except Exception as e:
            logger.error(f"Error getting admin count: {e}", exc_info=True)
            return 0

    def get_professor_count(self) -> int:
        """
        Get the number of professor users.

        Returns:
            int: Number of professors (0 if error)
        """
        try:
            with DatabaseSession() as session:
                return (
                    session.query(self.orm_model)
                    .filter(UsuarioORM.role == "professor")
                    .count()
                )
        except Exception as e:
            logger.error(f"Error getting professor count: {e}", exc_info=True)
            return 0

    def search_by_nome(self, search_term: str) -> List[UsuarioDTO]:
        """
        Search users by full name (partial match).

        Args:
            search_term: Search term for name

        Returns:
            List[UsuarioDTO]: Matching users
        """
        try:
            with DatabaseSession() as session:
                orm_objs = (
                    session.query(self.orm_model)
                    .filter(UsuarioORM.nome_completo.ilike(f"%{search_term}%"))
                    .all()
                )

                return [self.orm_to_dto(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(f"Error searching users by name: {e}", exc_info=True)
            return []


# ============================================================================
# SINGLETON FACTORY
# ============================================================================


_usuario_repository: Optional[UsuarioRepository] = None


def get_usuario_repository() -> UsuarioRepository:
    """
    Get or create the singleton UsuarioRepository instance.

    This ensures a single repository instance is used throughout
    the application, reducing memory overhead and ensuring
    consistent behavior.

    Returns:
        UsuarioRepository: Singleton instance

    Example:
        repo = get_usuario_repository()
        user = repo.get_by_username("professor01")
    """
    global _usuario_repository
    if _usuario_repository is None:
        _usuario_repository = UsuarioRepository()
    return _usuario_repository
