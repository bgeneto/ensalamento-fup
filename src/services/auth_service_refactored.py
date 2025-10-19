"""
REFACTORED Auth Service - Using Repository Pattern

This refactors AuthService to use repositories.
Returns DTOs instead of detached ORM objects.

BEFORE (Returns detached ORM objects):
    def get_user_by_username(username: str) -> Usuario:
        with DatabaseSession() as session:
            return session.query(Usuario).filter(...).first()  # ❌ Returns detached!

AFTER (Returns DTOs - safe):
    def get_user_by_username(username: str) -> UsuarioDTO:
        return UsuarioRepository.get_by_username(username)  # ✅ Returns DTO!
"""

import logging
import bcrypt
from typing import Optional, List

from src.repositories.usuario import get_usuario_repository
from src.schemas.usuario import (
    UsuarioDTO,
    UsuarioCreateDTO,
    UsuarioUpdateDTO,
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service class for authentication operations.

    This version uses the repository pattern to ensure:
    ✓ No detached ORM objects are returned
    ✓ All data is converted to DTOs at the boundary
    ✓ Clean separation of concerns
    ✓ Easy to test and maintain
    """

    # ===== USER OPERATIONS =====

    @classmethod
    def get_user_by_username(cls, username: str) -> Optional[UsuarioDTO]:
        """
        Get a user by username

        Args:
            username: Username

        Returns:
            UsuarioDTO or None if not found
        """
        try:
            repo = get_usuario_repository()
            return repo.get_by_username(username)
        except Exception as e:
            logger.exception(f"Error getting user by username '{username}': {e}")
            return None

    @classmethod
    def get_user_by_id(cls, usuario_id: int) -> Optional[UsuarioDTO]:
        """
        Get a user by ID

        Args:
            usuario_id: User ID

        Returns:
            UsuarioDTO or None if not found
        """
        try:
            repo = get_usuario_repository()
            return repo.get_by_id(usuario_id)
        except Exception as e:
            logger.exception(f"Error getting user by ID {usuario_id}: {e}")
            return None

    @classmethod
    def get_all_users(cls) -> List[UsuarioDTO]:
        """
        Get all users

        Returns:
            List of UsuarioDTO objects
        """
        try:
            repo = get_usuario_repository()
            return repo.get_all()
        except Exception as e:
            logger.exception(f"Error getting all users: {e}")
            return []

    @classmethod
    def get_users_by_role(cls, role: str) -> List[UsuarioDTO]:
        """
        Get all users with a specific role

        Args:
            role: User role (admin, professor, coordinator, etc.)

        Returns:
            List of UsuarioDTO objects
        """
        try:
            repo = get_usuario_repository()
            return repo.get_by_role(role)
        except Exception as e:
            logger.exception(f"Error getting users by role '{role}': {e}")
            return []

    @classmethod
    def get_users_by_department(cls, departamento: str) -> List[UsuarioDTO]:
        """
        Get all users in a specific department

        Args:
            departamento: Department name

        Returns:
            List of UsuarioDTO objects
        """
        try:
            repo = get_usuario_repository()
            return repo.get_by_departamento(departamento)
        except Exception as e:
            logger.exception(f"Error getting users by department '{departamento}': {e}")
            return []

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional[UsuarioDTO]:
        """
        Authenticate a user with username and password

        Args:
            username: Username
            password: Plain text password

        Returns:
            UsuarioDTO if authentication successful, None otherwise
        """
        try:
            user = cls.get_user_by_username(username)
            if not user:
                logger.warning(f"Authentication failed: user '{username}' not found")
                return None

            # Verify password
            if bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            ):
                logger.info(f"User '{username}' authenticated successfully")
                return user
            else:
                logger.warning(
                    f"Authentication failed: invalid password for '{username}'"
                )
                return None

        except Exception as e:
            logger.exception(f"Error during authentication for '{username}': {e}")
            return None

    @classmethod
    def create_user(cls, user_data: UsuarioCreateDTO) -> Optional[UsuarioDTO]:
        """
        Create a new user

        Args:
            user_data: UsuarioCreateDTO with user data

        Returns:
            Created UsuarioDTO or None if error
        """
        try:
            repo = get_usuario_repository()
            return repo.create(user_data)
        except Exception as e:
            logger.exception(f"Error creating user: {e}")
            return None

    @classmethod
    def update_user(
        cls, usuario_id: int, user_data: UsuarioUpdateDTO
    ) -> Optional[UsuarioDTO]:
        """
        Update a user

        Args:
            usuario_id: User ID
            user_data: UsuarioUpdateDTO with updated data

        Returns:
            Updated UsuarioDTO or None if error
        """
        try:
            repo = get_usuario_repository()
            return repo.update(usuario_id, user_data)
        except Exception as e:
            logger.exception(f"Error updating user {usuario_id}: {e}")
            return None

    @classmethod
    def delete_user(cls, usuario_id: int) -> bool:
        """
        Delete a user

        Args:
            usuario_id: User ID

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = get_usuario_repository()
            return repo.delete(usuario_id)
        except Exception as e:
            logger.exception(f"Error deleting user {usuario_id}: {e}")
            return False

    @classmethod
    def get_users_count(cls) -> int:
        """
        Get total count of users

        Returns:
            Count of users
        """
        try:
            repo = get_usuario_repository()
            return repo.count()
        except Exception as e:
            logger.exception(f"Error counting users: {e}")
            return 0

    @classmethod
    def search_users(cls, search_term: str) -> List[UsuarioDTO]:
        """
        Search users by name or username

        Args:
            search_term: Search term

        Returns:
            List of matching UsuarioDTO objects
        """
        try:
            repo = get_usuario_repository()
            # Search by name or username
            all_users = repo.get_all()
            search_lower = search_term.lower()
            return [
                u
                for u in all_users
                if search_lower in u.nome_completo.lower()
                or search_lower in u.username.lower()
            ]
        except Exception as e:
            logger.exception(f"Error searching users with term '{search_term}': {e}")
            return []

    @classmethod
    def user_exists(cls, username: str) -> bool:
        """
        Check if a user exists

        Args:
            username: Username

        Returns:
            True if user exists, False otherwise
        """
        try:
            return cls.get_user_by_username(username) is not None
        except Exception as e:
            logger.exception(f"Error checking if user exists: {e}")
            return False

    @classmethod
    def get_user_role(cls, username: str) -> Optional[str]:
        """
        Get the role of a user

        Args:
            username: Username

        Returns:
            User role or None if user not found
        """
        try:
            user = cls.get_user_by_username(username)
            return user.role if user else None
        except Exception as e:
            logger.exception(f"Error getting user role for '{username}': {e}")
            return None

    @classmethod
    def is_admin(cls, username: str) -> bool:
        """
        Check if a user is an admin

        Args:
            username: Username

        Returns:
            True if user is admin, False otherwise
        """
        try:
            return cls.get_user_role(username) == "admin"
        except Exception as e:
            logger.exception(f"Error checking if user is admin: {e}")
            return False

    @classmethod
    def is_professor(cls, username: str) -> bool:
        """
        Check if a user is a professor

        Args:
            username: Username

        Returns:
            True if user is professor, False otherwise
        """
        try:
            return cls.get_user_role(username) == "professor"
        except Exception as e:
            logger.exception(f"Error checking if user is professor: {e}")
            return False

    @classmethod
    def change_password(
        cls, usuario_id: int, old_password: str, new_password: str
    ) -> bool:
        """
        Change a user's password

        Args:
            usuario_id: User ID
            old_password: Current password (plain text)
            new_password: New password (plain text)

        Returns:
            True if successful, False otherwise
        """
        try:
            user = cls.get_user_by_id(usuario_id)
            if not user:
                logger.warning(f"User {usuario_id} not found for password change")
                return False

            # Verify old password
            if not bcrypt.checkpw(
                old_password.encode("utf-8"), user.password_hash.encode("utf-8")
            ):
                logger.warning(f"Invalid old password for user {usuario_id}")
                return False

            # Hash new password
            new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

            # Update user
            repo = get_usuario_repository()
            update_data = UsuarioUpdateDTO(password_hash=new_hash.decode("utf-8"))
            result = repo.update(usuario_id, update_data)

            if result:
                logger.info(f"Password changed for user {usuario_id}")
                return True
            else:
                logger.warning(f"Failed to change password for user {usuario_id}")
                return False

        except Exception as e:
            logger.exception(f"Error changing password for user {usuario_id}: {e}")
            return False


# ===== UTILITY FUNCTIONS =====


def get_current_user() -> Optional[str]:
    """
    Get current logged-in user from Streamlit session state

    Returns:
        Username if user is logged in, None otherwise
    """
    try:
        import streamlit as st

        return st.session_state.get("username")
    except Exception as e:
        logger.exception(f"Error getting current user from session: {e}")
        return None


def is_current_user_admin() -> bool:
    """
    Check if current user is admin

    Returns:
        True if current user is admin, False otherwise
    """
    username = get_current_user()
    return username is not None and AuthService.is_admin(username)


def get_current_user_role() -> str:
    """
    Get current user's role from Streamlit session state

    Returns:
        User role (admin, professor, etc.) or 'guest' if not logged in
    """
    username = get_current_user()
    if not username:
        return "guest"

    user = AuthService.get_user_by_username(username)
    if user:
        return user.role
    return "guest"


# ===== CONVENIENCE FUNCTION =====


def get_auth_service() -> AuthService:
    """Get the auth service"""
    return AuthService()
