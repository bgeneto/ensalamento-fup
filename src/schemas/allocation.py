"""
Data Transfer Object schemas for Allocation domain.

Schemas for: Regra, AlocacaoSemestral, ReservaEsporadica
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator

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
    nome_solicitante: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Full name of the person requesting the reservation (required)",
    )
    nome_responsavel: Optional[str] = Field(
        None,
        min_length=5,
        max_length=255,
        description="Full name of the person responsible for the event (optional)",
    )
    regra_recorrencia_json: str = Field(
        ..., min_length=1, description="JSON recurrence rule"
    )

    @field_validator("nome_solicitante")
    @classmethod
    def validate_nome_solicitante(cls, v: str) -> str:
        """Validate that solicitante name is a full name (at least 2 words)."""
        if not v or not v.strip():
            raise ValueError("Solicitante name cannot be empty")

        parts = v.strip().split()
        if len(parts) < 2:
            raise ValueError("Must provide full name (at least first and last name)")

        if any(len(part) < 2 for part in parts):
            raise ValueError("Each part of the name must have at least 2 characters")

        if not all(part.replace("-", "").replace("'", "").isalpha() for part in parts):
            raise ValueError("Name must contain only letters, hyphens, and apostrophes")

        return v.strip()

    @field_validator("nome_responsavel")
    @classmethod
    def validate_nome_responsavel(cls, v: Optional[str]) -> Optional[str]:
        """Validate that responsavel name is a full name if provided."""
        if v is None or not v.strip():
            return None

        parts = v.strip().split()
        if len(parts) < 2:
            raise ValueError("Must provide full name (at least first and last name)")

        if any(len(part) < 2 for part in parts):
            raise ValueError("Each part of the name must have at least 2 characters")

        if not all(part.replace("-", "").replace("'", "").isalpha() for part in parts):
            raise ValueError("Name must contain only letters, hyphens, and apostrophes")

        return v.strip()


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
    nome_solicitante: Optional[str] = Field(None, min_length=5, max_length=255)
    nome_responsavel: Optional[str] = Field(None, min_length=5, max_length=255)
    regra_recorrencia_json: Optional[str] = Field(None, min_length=1)

    @field_validator("nome_solicitante", "nome_responsavel")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate that name is a full name if provided."""
        if v is None:
            return v

        if not v.strip():
            raise ValueError("Name cannot be empty")

        parts = v.strip().split()
        if len(parts) < 2:
            raise ValueError("Must provide full name (at least first and last name)")

        if any(len(part) < 2 for part in parts):
            raise ValueError("Each part of the name must have at least 2 characters")

        if not all(part.replace("-", "").replace("'", "").isalpha() for part in parts):
            raise ValueError("Name must contain only letters, hyphens, and apostrophes")

        return v.strip()


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


# ============================================================================
# BLOCK GROUP Schemas (For Partial/Split Allocation)
# ============================================================================


class BlockGroupBase(BaseModel):
    """Base schema for BlockGroup (group of atomic blocks on the same day).

    Represents a set of time blocks that must be allocated together
    because they are on the same day. Different days can be allocated
    to different rooms for hybrid disciplines.
    """

    day_id: int = Field(..., ge=2, le=7, description="SIGAA day code (2=MON, 3=TUE, ..., 7=SAT)")
    day_name: str = Field(..., min_length=3, max_length=3, description="Human readable day (SEG, TER, etc.)")
    blocks: List[str] = Field(default_factory=list, description="Block codes (M1, M2, T1, etc.)")

    @property
    def block_count(self) -> int:
        """Number of atomic blocks in this group."""
        return len(self.blocks)

    def get_atomic_tuples(self) -> List[Tuple[str, int]]:
        """Get list of (block_code, day_id) tuples for this group."""
        return [(block, self.day_id) for block in self.blocks]

    class Config:
        from_attributes = True


class BlockGroupRead(BlockGroupBase):
    """Schema for reading BlockGroup with computed properties."""

    pass


class BlockGroupScoringBreakdownSchema(BaseModel):
    """Detailed scoring breakdown for a specific block group + room combination."""

    total_score: int = Field(default=0, description="Total score for this block group + room")
    capacity_points: int = Field(default=0, description="Points from capacity check")
    hard_rules_points: int = Field(default=0, description="Points from hard rules compliance")
    soft_preference_points: int = Field(default=0, description="Points from professor preferences")
    historical_frequency_points: int = Field(default=0, description="Points from historical frequency (per day)")

    # Details
    capacity_satisfied: bool = Field(default=False, description="Whether room capacity is adequate")
    hard_rules_satisfied: List[str] = Field(default_factory=list, description="List of satisfied hard rules")
    soft_preferences_satisfied: List[str] = Field(default_factory=list, description="List of satisfied soft preferences")
    historical_allocations: int = Field(default=0, description="Count of historical allocations for THIS DAY")

    class Config:
        from_attributes = True


class BlockGroupRoomScoreSchema(BaseModel):
    """Scoring result for a specific block group + room combination.

    Used in the allocation assistant UI to display per-day room suggestions.
    """

    block_group: BlockGroupBase = Field(..., description="The block group being scored")
    room_id: int = Field(..., gt=0, description="Room ID")
    room_name: str = Field(..., min_length=1, description="Room name")
    room_capacity: int = Field(default=0, ge=0, description="Room capacity")
    room_type: str = Field(default="N/A", description="Room type name")
    building_name: str = Field(default="N/A", description="Building name")
    score: int = Field(default=0, description="Total score")
    breakdown: BlockGroupScoringBreakdownSchema = Field(
        default_factory=BlockGroupScoringBreakdownSchema,
        description="Detailed scoring breakdown"
    )
    has_conflict: bool = Field(default=False, description="Whether room has time conflicts")
    conflict_details: List[str] = Field(default_factory=list, description="List of conflict descriptions")

    class Config:
        from_attributes = True


class PartialAllocationRequest(BaseModel):
    """Request schema for partial/split allocation.

    Allows allocating specific blocks of a demand to a room,
    enabling hybrid disciplines to use different rooms for different days.
    """

    demanda_id: int = Field(..., gt=0, description="Demand ID to allocate")
    sala_id: int = Field(..., gt=0, description="Room ID to allocate to")
    block_codes: Optional[List[str]] = Field(
        default=None,
        description="Specific block codes to allocate (e.g., ['M1', 'M2']). If None, allocates all blocks."
    )
    day_ids: Optional[List[int]] = Field(
        default=None,
        description="Specific day IDs to allocate (e.g., [2, 4] for MON, WED). If None, allocates all days."
    )

    @field_validator('day_ids')
    @classmethod
    def validate_day_ids(cls, v):
        if v is not None:
            for day_id in v:
                if day_id < 2 or day_id > 7:
                    raise ValueError(f"Invalid day_id: {day_id}. Must be 2-7 (MON-SAT)")
        return v

    class Config:
        from_attributes = True


class PartialAllocationResult(BaseModel):
    """Result schema for partial allocation operation."""

    success: bool = Field(..., description="Whether allocation succeeded")
    message: str = Field(..., description="Result message")
    allocated_blocks: List[str] = Field(default_factory=list, description="Blocks that were allocated")
    remaining_blocks: List[str] = Field(default_factory=list, description="Blocks still pending allocation")
    allocation_ids: List[int] = Field(default_factory=list, description="IDs of created allocations")
    room_id: Optional[int] = Field(default=None, description="Room ID allocated to")
    room_name: Optional[str] = Field(default=None, description="Room name allocated to")

    class Config:
        from_attributes = True
