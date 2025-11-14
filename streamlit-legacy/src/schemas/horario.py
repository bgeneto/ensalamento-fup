"""
Data Transfer Object schemas for Schedule domain.

Schemas for: DiaSemana, HorarioBloco
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# DIA_SEMANA Schemas
# ============================================================================


class DiaSemanaBase(BaseModel):
    """Base schema for DiaSemana."""

    id_sigaa: int = Field(..., ge=2, le=7)  # SIGAA day IDs: 2-7
    nome: str = Field(..., min_length=3, max_length=3)  # SEG, TER, QUA, QUI, SEX, SAB


class DiaSemanaCreate(DiaSemanaBase):
    """Schema for creating a new DiaSemana."""

    pass


class DiaSemanaUpdate(BaseModel):
    """Schema for updating a DiaSemana."""

    id_sigaa: Optional[int] = Field(None, ge=2, le=7)
    nome: Optional[str] = Field(None, min_length=3, max_length=3)


class DiaSemanaRead(DiaSemanaBase):
    """Schema for reading DiaSemana."""

    class Config:
        from_attributes = True


# ============================================================================
# HORARIO_BLOCO Schemas
# ============================================================================


class HorarioBlocoBase(BaseModel):
    """Base schema for HorarioBloco."""

    codigo_bloco: str = Field(..., min_length=2, max_length=2)  # M1, M2, T1, etc.
    turno: str = Field(
        ..., min_length=1, max_length=1
    )  # M (morning), T (afternoon), N (night)
    horario_inicio: str = Field(..., max_length=5)  # HH:MM format
    horario_fim: str = Field(..., max_length=5)  # HH:MM format


class HorarioBlocoCreate(HorarioBlocoBase):
    """Schema for creating a new HorarioBloco."""

    pass


class HorarioBlocoUpdate(BaseModel):
    """Schema for updating a HorarioBloco."""

    codigo_bloco: Optional[str] = Field(None, min_length=2, max_length=2)
    turno: Optional[str] = Field(None, min_length=1, max_length=1)
    horario_inicio: Optional[str] = Field(None, max_length=5)
    horario_fim: Optional[str] = Field(None, max_length=5)


class HorarioBlocoRead(HorarioBlocoBase):
    """Schema for reading HorarioBloco."""

    class Config:
        from_attributes = True
