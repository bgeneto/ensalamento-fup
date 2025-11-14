"""
Base DTO (Data Transfer Object) schemas using Pydantic.

All other schemas inherit from these base classes for consistent validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Base schema for all DTOs.

    Provides common fields:
    - id: Record identifier
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    """

    model_config = ConfigDict(
        from_attributes=True,  # Allow ORM model conversion
        populate_by_name=True,  # Accept both field name and alias
    )

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BaseCreateSchema(BaseModel):
    """Base schema for CREATE operations (no id or timestamps)."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class BaseUpdateSchema(BaseModel):
    """Base schema for UPDATE operations (all fields optional)."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
