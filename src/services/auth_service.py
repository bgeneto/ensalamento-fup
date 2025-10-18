"""
Authentication service for Sistema de Ensalamento FUP/UnB
Handles user authentication, registration, and session management
"""

import bcrypt
import yaml
import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime
import os
from pathlib import Path
from database import DatabaseSession, Usuario
from models import UsuarioCreate, UsuarioUpdate
from config import AUTH_COOKIE_NAME, AUTH_COOKIE_EXPIRY_DAYS


class AuthService:
    """Service class for authentication operations"""

    _authenticator = None
    _config = None

    @classmethod
    def get_authenticator(cls):
        """Get or create streamlit-authenticator instance"""
        if cls._authenticator is None:
            cls._initialize_authenticator()
        return cls._authenticator

    @classmethod
    def _initialize_authenticator(cls):
        """Initialize streamlit-authenticator with configuration"""
        try:
            import streamlit_authenticator as stauth

            # Load authentication configuration
            config = cls._get_auth_config()

            # Create authenticator
            cls._authenticator = stauth.Authenticate(
                config["credentials"],
                config["cookie"]["name"],
                config["cookie"]["key"],
                config["cookie"]["expiry_days"],
            )
            cls._config = config

        except Exception as e:
            print(f"Error initializing authenticator: {e}")
            # Create minimal config for first run
            cls._create_minimal_config()

    @classmethod
    def _get_auth_config(cls) -> Dict[str, Any]:
        """Load authentication configuration from database or create default"""
        with DatabaseSession() as session:
            users = session.query(Usuario).all()

            if not users:
                # No users exist, return minimal config
                return cls._create_minimal_config()

            # Build credentials from database users
            credentials = {"usernames": {}}
            cookie_config = {
                "name": AUTH_COOKIE_NAME,
                "key": "default_signature_key",  # In production, use a secure random key
                "expiry_days": AUTH_COOKIE_EXPIRY_DAYS,
            }
            preauthorized = {"emails": []}

            for user in users:
                credentials["usernames"][user.username] = {
                    "name": user.nome_completo or user.username,
                    "password": user.password_hash,  # Already hashed
                    "email": f"{user.username}@unb.br",  # Default email
                    "role": user.role,
                }

                # Add admin emails to preauthorized list
                if user.role == "admin":
                    preauthorized["emails"].append(f"{user.username}@unb.br")

            return {
                "credentials": credentials,
                "cookie": cookie_config,
                "preauthorized": preauthorized,
            }

    @classmethod
    def _create_minimal_config(cls) -> Dict[str, Any]:
        """Create minimal authentication configuration for first run"""
        return {
            "credentials": {"usernames": {}},
            "cookie": {
                "name": AUTH_COOKIE_NAME,
                "key": "default_signature_key_change_in_production",
                "expiry_days": AUTH_COOKIE_EXPIRY_DAYS,
            },
            "preauthorized": {"emails": []},
        }

    @classmethod
    def create_user(
        cls,
        username: str,
        password: str,
        nome_completo: str = None,
        role: str = "professor",
    ) -> Optional[Usuario]:
        """Create a new user in the database"""
        try:
            with DatabaseSession() as session:
                # Check if user already exists
                existing_user = (
                    session.query(Usuario).filter(Usuario.username == username).first()
                )
                if existing_user:
                    return None

                # Hash password
                password_hash = bcrypt.hashpw(
                    password.encode("utf-8"), bcrypt.gensalt()
                ).decode("utf-8")

                # Create user
                new_user = Usuario(
                    username=username,
                    password_hash=password_hash,
                    nome_completo=nome_completo,
                    role=role,
                )

                session.add(new_user)
                session.flush()

                # Reset authenticator to reload config
                cls._authenticator = None

                # Update the auth config file
                cls._update_auth_config_file()

                return new_user

        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    @classmethod
    def get_user_role(cls, username: str) -> Optional[str]:
        """Get user role by username (within session context)"""
        try:
            with DatabaseSession() as session:
                user = (
                    session.query(Usuario).filter(Usuario.username == username).first()
                )
                return user.role if user else None
        except Exception as e:
            print(f"Error getting user role: {e}")
            return None

    @classmethod
    def get_user_by_username(cls, username: str) -> Optional[Usuario]:
        """Get user by username"""
        try:
            with DatabaseSession() as session:
                return (
                    session.query(Usuario).filter(Usuario.username == username).first()
                )
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    @classmethod
    def get_all_users(cls) -> list[Usuario]:
        """Get all users"""
        try:
            with DatabaseSession() as session:
                return session.query(Usuario).order_by(Usuario.username).all()
        except Exception as e:
            print(f"Error getting users: {e}")
            return []

    @classmethod
    def update_user(cls, username: str, user_data: UsuarioUpdate) -> Optional[Usuario]:
        """Update user information"""
        try:
            with DatabaseSession() as session:
                user = (
                    session.query(Usuario).filter(Usuario.username == username).first()
                )
                if not user:
                    return None

                # Update fields
                if user_data.nome_completo is not None:
                    user.nome_completo = user_data.nome_completo
                if user_data.role is not None:
                    user.role = user_data.role

                # Reset authenticator to reload config
                cls._authenticator = None

                # Update the auth config file
                cls._update_auth_config_file()

                return user

        except Exception as e:
            print(f"Error updating user: {e}")
            return None

    @classmethod
    def delete_user(cls, username: str) -> bool:
        """Delete a user"""
        try:
            with DatabaseSession() as session:
                user = (
                    session.query(Usuario).filter(Usuario.username == username).first()
                )
                if not user:
                    return False

                # Don't allow deletion of the last admin
                if user.role == "admin":
                    admin_count = (
                        session.query(Usuario).filter(Usuario.role == "admin").count()
                    )
                    if admin_count <= 1:
                        return False

                session.delete(user)

                # Reset authenticator to reload config
                cls._authenticator = None

                # Update the auth config file
                cls._update_auth_config_file()

                return True

        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    @classmethod
    def verify_password(cls, username: str, password: str) -> bool:
        """Verify user password"""
        try:
            with DatabaseSession() as session:
                user = (
                    session.query(Usuario).filter(Usuario.username == username).first()
                )
                if not user:
                    return False

                return bcrypt.checkpw(
                    password.encode("utf-8"), user.password_hash.encode("utf-8")
                )

        except Exception as e:
            print(f"Error verifying password: {e}")
            return False

    @classmethod
    def update_password(
        cls, username: str, old_password: str, new_password: str
    ) -> bool:
        """Update user password"""
        try:
            # Verify old password first
            if not cls.verify_password(username, old_password):
                return False

            with DatabaseSession() as session:
                user = (
                    session.query(Usuario).filter(Usuario.username == username).first()
                )
                if not user:
                    return False

                # Hash new password
                password_hash = bcrypt.hashpw(
                    new_password.encode("utf-8"), bcrypt.gensalt()
                ).decode("utf-8")
                user.password_hash = password_hash

                # Reset authenticator to reload config
                cls._authenticator = None

                return True

        except Exception as e:
            print(f"Error updating password: {e}")
            return False

    @classmethod
    def create_initial_admin(
        cls, username: str = "admin", password: str = "admin123"
    ) -> bool:
        """Create initial admin user if no admin exists"""
        try:
            with DatabaseSession() as session:
                # Check if admin user exists
                existing_admin = (
                    session.query(Usuario).filter(Usuario.role == "admin").first()
                )
                if existing_admin:
                    return True

                # Create admin user
                admin_user = cls.create_user(
                    username=username,
                    password=password,
                    nome_completo="Administrador do Sistema",
                    role="admin",
                )

                if admin_user:
                    print(f"Initial admin user created: {username}")
                    return True
                else:
                    return False

        except Exception as e:
            print(f"Error creating initial admin: {e}")
            return False

    @classmethod
    def get_user_stats(cls) -> Dict[str, int]:
        """Get user statistics"""
        try:
            with DatabaseSession() as session:
                total_users = session.query(Usuario).count()
                admin_users = (
                    session.query(Usuario).filter(Usuario.role == "admin").count()
                )
                professor_users = (
                    session.query(Usuario).filter(Usuario.role == "professor").count()
                )

                return {
                    "total": total_users,
                    "admin": admin_users,
                    "professor": professor_users,
                }

        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {"total": 0, "admin": 0, "professor": 0}

    @classmethod
    def _update_auth_config_file(cls):
        """Update the auth config YAML file after database changes"""
        try:
            config = cls._get_auth_config()
            config_path = Path("data/auth_config.yaml")
            config_path.parent.mkdir(exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as file:
                yaml.dump(config, file, default_flow_style=False, allow_unicode=True)

        except Exception as e:
            print(f"Error updating auth config file: {e}")

    @classmethod
    def _ensure_initial_admin(cls):
        """Ensure initial admin user exists"""
        with DatabaseSession() as session:
            # Check if any users exist
            user_count = session.query(Usuario).count()

            if user_count == 0:
                # Create initial admin user
                cls.create_initial_admin()
                # Update the config file after creating admin
                cls._update_auth_config_file()

    @classmethod
    def is_admin(cls, username: str) -> bool:
        """Check if user has admin role"""
        role = cls.get_user_role(username)
        return role == "admin"

    @classmethod
    def authenticate_user(cls, username: str, password: str) -> bool:
        """Authenticate user with username and password"""
        return cls.verify_password(username, password)

    @classmethod
    def reset_all_passwords(cls, default_password: str = "temp123") -> bool:
        """Reset all users' passwords to default (for emergency use)"""
        try:
            with DatabaseSession() as session:
                users = session.query(Usuario).all()
                password_hash = bcrypt.hashpw(
                    default_password.encode("utf-8"), bcrypt.gensalt()
                ).decode("utf-8")

                for user in users:
                    user.password_hash = password_hash

                # Reset authenticator to reload config
                cls._authenticator = None

                return True

        except Exception as e:
            print(f"Error resetting passwords: {e}")
            return False


# Authentication helper functions for Streamlit
def require_auth():
    """Decorator to require authentication for a function"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if (
                "authentication_status" not in st.session_state
                or not st.session_state["authentication_status"]
            ):
                st.error("Por favor, faça login para acessar esta página.")
                return None
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_admin():
    """Decorator to require admin role for a function"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if (
                "authentication_status" not in st.session_state
                or not st.session_state["authentication_status"]
            ):
                st.error("Por favor, faça login para acessar esta página.")
                return None

            if "username" in st.session_state:
                if not AuthService.is_admin(st.session_state["username"]):
                    st.error(
                        "Acesso negado. Esta função requer privilégios de administrador."
                    )
                    return None

            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_current_user() -> Optional[str]:
    """Get current authenticated username"""
    return st.session_state.get("username")


def is_current_user_admin() -> bool:
    """Check if current user is admin"""
    username = get_current_user()
    return username is not None and AuthService.is_admin(username)


def get_current_user_role() -> str:
    """Get current user's role"""
    username = get_current_user()
    if not username:
        return "guest"
    role = AuthService.get_user_role(username)
    return role if role else "guest"
