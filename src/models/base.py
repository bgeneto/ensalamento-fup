"""
Base ORM model with common fields (id, created_at, updated_at).

All other models inherit from this base class.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BaseModel(Base):
    """
    Base model for all ORM entities.

    Provides common fields:
    - id: Primary key (auto-incrementing)
    - created_at: Timestamp when record was created
    - updated_at: Timestamp when record was last updated
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        """String representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
