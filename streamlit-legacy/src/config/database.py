"""
Database connection and session management.

Provides DatabaseSession context manager for managing SQLAlchemy sessions.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings

# Import all models to ensure they are registered with BaseModel.registry
# IMPORTANT: This must happen BEFORE engine creation to resolve relationships
from src.models import academic, allocation, inventory, horario  # noqa: F401


# Create database engine
def get_db_engine() -> Engine:
    """
    Create and return SQLAlchemy engine.

    Returns:
        Engine: SQLAlchemy engine instance
    """
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=(
            {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
        ),
        echo=settings.DEBUG,
    )

    # Enable foreign keys for SQLite
    if "sqlite" in settings.DATABASE_URL:

        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Create session factory
_engine = get_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


class DatabaseSession:
    """Context manager for database sessions."""

    def __init__(self):
        """Initialize database session manager."""
        self.session: Session | None = None

    def __enter__(self) -> Session:
        """Enter context and create session."""
        self.session = SessionLocal()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and close session."""
        if self.session:
            self.session.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Get a database session using context manager.

    Usage:
        with get_db_session() as session:
            # Use session

    Yields:
        Session: SQLAlchemy session
    """
    with DatabaseSession() as session:
        yield session
