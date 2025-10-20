"""
Data Transfer Object schemas for Allocation domain.

Schemas for: Regra, AlocacaoSemestral, ReservaEsporadica
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# REGRA Schemas
# ============================================================================


class RegraBase(BaseModel):
    """Base schema for Regra (allocation rule)."""

    descricao: str = Field(..., min_length=1, max_length=255)
    tipo_regra: str = Field(
        ..., min_length=1, max_length=100
    )  # e.g., "DISCIPLINA_TIPO_SALA"
    config_json: str = Field(..., min_length=1)  # JSON configuration
    prioridade: int = Field(default=0, ge=0)  # 0=hard, >0=soft preference


class RegraCreate(RegraBase):
    """Schema for creating a new Regra."""

    pass


class RegraUpdate(BaseModel):
    """Schema for updating a Regra."""

    descricao: Optional[str] = Field(None, min_length=1, max_length=255)
    tipo_regra: Optional[str] = Field(None, min_length=1, max_length=100)
    config_json: Optional[str] = Field(None, min_length=1)
    prioridade: Optional[int] = Field(None, ge=0)


class RegraRead(RegraBase):
    """Schema for reading Regra (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ALOCACAO_SEMESTRAL Schemas
# ============================================================================


class AlocacaoSemestralBase(BaseModel):
    """Base schema for AlocacaoSemestral (semester allocation)."""

    semestre_id: int = Field(..., gt=0)
    demanda_id: int = Field(..., gt=0)
    sala_id: int = Field(..., gt=0)
    professor_id: Optional[int] = Field(default=None)
    alocada: bool = Field(default=False)
    confiavel: bool = Field(default=False)
    motivo_nao_alocacao: str = Field(default="", max_length=255)


class AlocacaoSemestralCreate(AlocacaoSemestralBase):
    """Schema for creating a new AlocacaoSemestral."""

    pass


class AlocacaoSemestralUpdate(BaseModel):
    """Schema for updating a AlocacaoSemestral."""

    semestre_id: Optional[int] = Field(None, gt=0)
    demanda_id: Optional[int] = Field(None, gt=0)
    sala_id: Optional[int] = Field(None, gt=0)
    professor_id: Optional[int] = None
    alocada: Optional[bool] = None
    confiavel: Optional[bool] = None
    motivo_nao_alocacao: Optional[str] = Field(None, max_length=255)


class AlocacaoSemestralRead(AlocacaoSemestralBase):
    """Schema for reading AlocacaoSemestral (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# RESERVA_ESPORADICA Schemas
# ============================================================================


class ReservaEsporadicaBase(BaseModel):
    """Base schema for ReservaEsporadica (ad-hoc room reservation)."""

    sala_id: int = Field(..., gt=0)
    dia_semana_id: int = Field(..., gt=0)
    horario_bloco_id: int = Field(..., gt=0)
    semestre_id: int = Field(..., gt=0)
    motivo: str = Field(default="", max_length=255)
    confirmada: bool = Field(default=False)


class ReservaEsporadicaCreate(ReservaEsporadicaBase):
    """Schema for creating a new ReservaEsporadica."""

    pass


class ReservaEsporadicaUpdate(BaseModel):
    """Schema for updating a ReservaEsporadica."""

    sala_id: Optional[int] = Field(None, gt=0)
    dia_semana_id: Optional[int] = Field(None, gt=0)
    horario_bloco_id: Optional[int] = Field(None, gt=0)
    semestre_id: Optional[int] = Field(None, gt=0)
    motivo: Optional[str] = Field(None, max_length=255)
    confirmada: Optional[bool] = None


class ReservaEsporadicaRead(ReservaEsporadicaBase):
    """Schema for reading ReservaEsporadica (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
