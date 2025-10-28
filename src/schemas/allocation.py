"""
Data Transfer Object schemas for Allocation domain.

Schemas for: Regra, AlocacaoSemestral, ReservaEsporadica
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum

from src.schemas.academic import DemandaRead


# ============================================================================
# RECURRENCE TYPE ENUMS
# ============================================================================


class TipoRecorrencia(str, Enum):
    """Recurrence pattern types."""

    UNICA = "unica"
    DIARIA = "diaria"
    SEMANAL = "semanal"
    MENSAL = "mensal"


class PosicaoMes(str, Enum):
    """Position in month for nth-day patterns."""

    PRIMEIRA = 1
    SEGUNDA = 2
    TERCEIRA = 3
    QUARTA = 4
    ULTIMA = 5


# ============================================================================
# REGRA RECORRENCIA Schemas
# ============================================================================


class RegraRecorrenciaBase(BaseModel):
    """Base schema for recurrence rules."""

    tipo: TipoRecorrencia = Field(..., description="Type of recurrence pattern")

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v):
        if v not in TipoRecorrencia:
            raise ValueError(f"Invalid recurrence type: {v}")
        return v


class RegraUnica(RegraRecorrenciaBase):
    """Single occurrence recurrence rule."""

    tipo: TipoRecorrencia = Field(default=TipoRecorrencia.UNICA, frozen=True)


class RegraDiaria(RegraRecorrenciaBase):
    """Daily recurrence rule."""

    tipo: TipoRecorrencia = Field(default=TipoRecorrencia.DIARIA, frozen=True)
    intervalo: int = Field(
        default=1, ge=1, le=365, description="Days between occurrences"
    )
    fim: str = Field(..., description="End date in YYYY-MM-DD format")


class RegraSemanal(RegraRecorrenciaBase):
    """Weekly recurrence rule."""

    tipo: TipoRecorrencia = Field(default=TipoRecorrencia.SEMANAL, frozen=True)
    dias: List[int] = Field(
        ...,
        min_items=1,
        max_items=7,
        description="Days of week (2=SEG, 3=TER, ..., 7=SAB)",
    )
    fim: str = Field(..., description="End date in YYYY-MM-DD format")

    @field_validator("dias")
    @classmethod
    def validate_dias(cls, v):
        for dia in v:
            if dia < 2 or dia > 7:
                raise ValueError(f"Invalid day of week: {dia}. Must be 2-7 (SEG-SAB)")
        return sorted(set(v))  # Remove duplicates and sort


class RegraMensalDia(RegraRecorrenciaBase):
    """Monthly recurrence by day of month."""

    tipo: TipoRecorrencia = Field(default=TipoRecorrencia.MENSAL, frozen=True)
    dia_mes: int = Field(..., ge=1, le=31, description="Day of month (1-31)")
    fim: str = Field(..., description="End date in YYYY-MM-DD format")


class RegraMensalPosicao(RegraRecorrenciaBase):
    """Monthly recurrence by nth-day pattern."""

    tipo: TipoRecorrencia = Field(default=TipoRecorrencia.MENSAL, frozen=True)
    posicao: PosicaoMes = Field(
        ..., description="Position in month (1st, 2nd, 3rd, 4th, last)"
    )
    dia_semana: int = Field(
        ..., ge=2, le=7, description="Day of week (2=SEG, ..., 7=SAB)"
    )
    fim: str = Field(..., description="End date in YYYY-MM-DD format")


# Union type for all recurrence rules
RegraRecorrencia = Union[
    RegraUnica, RegraDiaria, RegraSemanal, RegraMensalDia, RegraMensalPosicao
]


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


# ============================================================================
# RESERVA_EVENTO Schemas
# ============================================================================


class ReservaEventoBase(BaseModel):
    """Base schema for ReservaEvento (parent recurring event)."""

    sala_id: int = Field(..., gt=0)
    titulo_evento: str = Field(..., min_length=1, max_length=255)
    username_criador: str = Field(..., min_length=1, max_length=100)
    nome_solicitante: Optional[str] = Field(None, max_length=255)
    nome_responsavel: Optional[str] = Field(None, max_length=255)
    regra_recorrencia_json: str = Field(
        ..., min_length=1, description="JSON recurrence rule"
    )
    status: str = Field(default="Aprovada", max_length=50)


class ReservaEventoCreate(ReservaEventoBase):
    """Schema for creating a new ReservaEvento."""

    @field_validator("regra_recorrencia_json")
    @classmethod
    def validate_regra_json(cls, v):
        try:
            import json

            rule = json.loads(v)
            if not isinstance(rule, dict):
                raise ValueError("Recurrence rule must be a JSON object")
            if "tipo" not in rule:
                raise ValueError("Recurrence rule must have a 'tipo' field")
            return v
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format for recurrence rule")


class ReservaEventoUpdate(BaseModel):
    """Schema for updating a ReservaEvento."""

    sala_id: Optional[int] = Field(None, gt=0)
    titulo_evento: Optional[str] = Field(None, min_length=1, max_length=255)
    username_criador: Optional[str] = Field(None, min_length=1, max_length=100)
    nome_solicitante: Optional[str] = Field(None, max_length=255)
    nome_responsavel: Optional[str] = Field(None, max_length=255)
    regra_recorrencia_json: Optional[str] = Field(None, min_length=1)
    status: Optional[str] = Field(None, max_length=50)


class ReservaEventoRead(ReservaEventoBase):
    """Schema for reading ReservaEvento (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReservaEventoReadWithOccurrences(ReservaEventoRead):
    """Schema for reading ReservaEvento with its occurrences."""

    ocorrencias: List["ReservaOcorrenciaRead"] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ============================================================================
# RESERVA_OCORRENCIA Schemas
# ============================================================================


class ReservaOcorrenciaBase(BaseModel):
    """Base schema for ReservaOcorrencia (individual occurrence)."""

    evento_id: int = Field(..., gt=0)
    data_reserva: str = Field(..., min_length=10, max_length=10)  # DATE as YYYY-MM-DD
    codigo_bloco: str = Field(..., min_length=1, max_length=10)
    status_excecao: Optional[str] = Field(None, max_length=50)


class ReservaOcorrenciaCreate(ReservaOcorrenciaBase):
    """Schema for creating a new ReservaOcorrencia."""

    pass


class ReservaOcorrenciaUpdate(BaseModel):
    """Schema for updating a ReservaOcorrencia."""

    evento_id: Optional[int] = Field(None, gt=0)
    data_reserva: Optional[str] = Field(None, min_length=10, max_length=10)
    codigo_bloco: Optional[str] = Field(None, min_length=1, max_length=10)
    status_excecao: Optional[str] = Field(None, max_length=50)


class ReservaOcorrenciaRead(ReservaOcorrenciaBase):
    """Schema for reading ReservaOcorrencia (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReservaOcorrenciaReadWithEvent(ReservaOcorrenciaRead):
    """Schema for reading ReservaOcorrencia with its parent event."""

    evento: Optional[ReservaEventoRead] = None

    class Config:
        from_attributes = True


# Forward reference resolution
ReservaEventoReadWithOccurrences.model_rebuild()
ReservaOcorrenciaReadWithEvent.model_rebuild()
