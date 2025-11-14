"""
Data Transfer Object schemas for Inventory domain.

Schemas for: Campus, Predio, TipoSala, Sala, Caracteristica
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# CAMPUS Schemas
# ============================================================================


class CampusBase(BaseModel):
    """Base schema for Campus."""

    nome: str = Field(..., min_length=1, max_length=255)
    descricao: str = Field(default="", max_length=255)


class CampusCreate(CampusBase):
    """Schema for creating a new Campus."""

    pass


class CampusUpdate(BaseModel):
    """Schema for updating a Campus."""

    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    descricao: Optional[str] = Field(None, max_length=255)


class CampusRead(CampusBase):
    """Schema for reading Campus (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PREDIO Schemas
# ============================================================================


class PredioBase(BaseModel):
    """Base schema for Predio."""

    nome: str = Field(..., min_length=1, max_length=255)
    descricao: str = Field(..., min_length=1, max_length=255)
    campus_id: int = Field(..., gt=0)


class PredioCreate(PredioBase):
    """Schema for creating a new Predio."""

    pass


class PredioUpdate(BaseModel):
    """Schema for updating a Predio."""

    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    descricao: Optional[str] = Field(None, min_length=1, max_length=255)
    campus_id: Optional[int] = Field(None, gt=0)


class PredioRead(PredioBase):
    """Schema for reading Predio (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# TIPO_SALA Schemas
# ============================================================================


class TipoSalaBase(BaseModel):
    """Base schema for TipoSala."""

    nome: str = Field(..., min_length=1, max_length=100)


class TipoSalaCreate(TipoSalaBase):
    """Schema for creating a new TipoSala."""

    pass


class TipoSalaUpdate(BaseModel):
    """Schema for updating a TipoSala."""

    nome: Optional[str] = Field(None, min_length=1, max_length=100)


class TipoSalaRead(TipoSalaBase):
    """Schema for reading TipoSala (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# CARACTERISTICA Schemas
# ============================================================================


class CaracteristicaBase(BaseModel):
    """Base schema for Caracteristica."""

    nome: str = Field(..., min_length=1, max_length=100)


class CaracteristicaCreate(CaracteristicaBase):
    """Schema for creating a new Caracteristica."""

    pass


class CaracteristicaUpdate(BaseModel):
    """Schema for updating a Caracteristica."""

    nome: Optional[str] = Field(None, min_length=1, max_length=100)


class CaracteristicaRead(CaracteristicaBase):
    """Schema for reading Caracteristica (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# SALA Schemas
# ============================================================================


class SalaBase(BaseModel):
    """Base schema for Sala."""

    nome: str = Field(..., min_length=1, max_length=255)
    descricao: Optional[str] = Field(default=None, max_length=500)
    predio_id: int = Field(..., gt=0)
    tipo_sala_id: int = Field(..., gt=0)
    capacidade: int = Field(default=30, ge=1)
    andar: Optional[int] = Field(default=None)


class SalaCreate(SalaBase):
    """Schema for creating a new Sala."""

    pass


class SalaUpdate(BaseModel):
    """Schema for updating a Sala."""

    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    descricao: Optional[str] = Field(None, max_length=500)
    predio_id: Optional[int] = Field(None, gt=0)
    tipo_sala_id: Optional[int] = Field(None, gt=0)
    capacidade: Optional[int] = Field(None, ge=1)
    andar: Optional[int] = Field(None)


class SalaRead(SalaBase):
    """Schema for reading Sala (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
