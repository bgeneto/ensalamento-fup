"""
Data Transfer Object schemas for Allocation domain.

Schemas for: Regra, AlocacaoSemestral, ReservaEsporadica
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from src.schemas.academic import DemandaRead


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
    dia_semana_id: int = Field(..., gt=0)
    codigo_bloco: str = Field(..., min_length=1, max_length=10)


class AlocacaoSemestralCreate(AlocacaoSemestralBase):
    """Schema for creating a new AlocacaoSemestral."""

    pass


class AlocacaoSemestralUpdate(BaseModel):
    """Schema for updating a AlocacaoSemestral."""

    semestre_id: Optional[int] = Field(None, gt=0)
    demanda_id: Optional[int] = Field(None, gt=0)
    sala_id: Optional[int] = Field(None, gt=0)
    dia_semana_id: Optional[int] = Field(None, gt=0)
    codigo_bloco: Optional[str] = Field(None, min_length=1, max_length=10)


class AlocacaoSemestralRead(AlocacaoSemestralBase):
    """Schema for reading AlocacaoSemestral."""

    id: int
    demanda: Optional[DemandaRead] = None

    class Config:
        from_attributes = True


# ============================================================================
# RESERVA_ESPORADICA Schemas
# ============================================================================


class ReservaEsporadicaBase(BaseModel):
    """Base schema for ReservaEsporadica (ad-hoc room reservation)."""

    sala_id: int = Field(..., gt=0)
    username_solicitante: str = Field(..., min_length=1, max_length=100)
    titulo_evento: str = Field(..., min_length=1, max_length=255)
    data_reserva: str = Field(..., min_length=10, max_length=10)  # DATE as YYYY-MM-DD
    codigo_bloco: str = Field(..., min_length=1, max_length=10)
    status: str = Field(default="Aprovada", max_length=50)


class ReservaEsporadicaCreate(ReservaEsporadicaBase):
    """Schema for creating a new ReservaEsporadica."""

    pass


class ReservaEsporadicaUpdate(BaseModel):
    """Schema for updating a ReservaEsporadica."""

    sala_id: Optional[int] = Field(None, gt=0)
    username_solicitante: Optional[str] = Field(None, min_length=1, max_length=100)
    titulo_evento: Optional[str] = Field(None, min_length=1, max_length=255)
    data_reserva: Optional[str] = Field(None, min_length=10, max_length=10)
    codigo_bloco: Optional[str] = Field(None, min_length=1, max_length=10)
    status: Optional[str] = Field(None, max_length=50)


class ReservaEsporadicaRead(ReservaEsporadicaBase):
    """Schema for reading ReservaEsporadica (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
