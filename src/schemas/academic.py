"""Data Transfer Object schemas for Academic domain."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# SEMESTRE Schemas
# ============================================================================


class SemestreBase(BaseModel):
    """Base schema for Semestre."""

    nome: str = Field(..., min_length=5, max_length=50)  # e.g., "2025.1"
    status: bool = Field(default=False)


class SemestreCreate(SemestreBase):
    """Schema for creating a new Semestre."""

    pass


class SemestreUpdate(BaseModel):
    """Schema for updating a Semestre."""

    nome: Optional[str] = Field(None, min_length=5, max_length=50)
    status: Optional[bool] = Field(default=False)


class SemestreRead(SemestreBase):
    """Schema for reading Semestre (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# DEMANDA Schemas
# ============================================================================


class DemandaBase(BaseModel):
    """Base schema for Demanda."""

    semestre_id: int = Field(..., gt=0)
    codigo_disciplina: str = Field(..., min_length=1, max_length=50)
    nome_disciplina: str = Field(..., min_length=1, max_length=255)
    professores_disciplina: str = Field(default="", max_length=500)
    turma_disciplina: str = Field(default="", max_length=50)
    vagas_disciplina: int = Field(default=0, ge=0)
    horario_sigaa_bruto: str = Field(..., max_length=255)  # e.g., "24M12 6T34"
    id_oferta_externo: Optional[str] = Field(default=None, max_length=100)
    codigo_curso: str = Field(default="", max_length=50)
    origem: str = Field(default="manual", max_length=20)
    sync_status: str = Field(default="manual", max_length=30)
    api_payload_hash: Optional[str] = Field(default=None, max_length=255)
    api_snapshot_json: dict[str, Any] = Field(default_factory=dict)
    local_overrides_json: dict[str, Any] = Field(default_factory=dict)
    last_seen_in_api_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    removed_from_api_at: Optional[datetime] = None
    preservar_local_em_remocao_api: bool = Field(default=False)
    revalidation_required: bool = Field(default=False)


class DemandaCreate(DemandaBase):
    """Schema for creating a new Demanda."""

    pass


class DemandaUpdate(BaseModel):
    """Schema for updating a Demanda."""

    semestre_id: Optional[int] = Field(None, gt=0)
    codigo_disciplina: Optional[str] = Field(None, min_length=1, max_length=50)
    nome_disciplina: Optional[str] = Field(None, min_length=1, max_length=255)
    professores_disciplina: Optional[str] = Field(None, max_length=500)
    turma_disciplina: Optional[str] = Field(None, max_length=50)
    vagas_disciplina: Optional[int] = Field(None, ge=0)
    horario_sigaa_bruto: Optional[str] = Field(None, max_length=255)
    id_oferta_externo: Optional[str] = Field(None, max_length=100)
    codigo_curso: Optional[str] = Field(None, max_length=50)
    origem: Optional[str] = Field(None, max_length=20)
    sync_status: Optional[str] = Field(None, max_length=30)
    api_payload_hash: Optional[str] = Field(None, max_length=255)
    api_snapshot_json: Optional[dict[str, Any]] = None
    local_overrides_json: Optional[dict[str, Any]] = None
    last_seen_in_api_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    removed_from_api_at: Optional[datetime] = None
    preservar_local_em_remocao_api: Optional[bool] = None
    revalidation_required: Optional[bool] = None


class DemandaRead(DemandaBase):
    """Schema for reading Demanda (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SemesterDemandDeletionResult(BaseModel):
    """Result of removing semester demands."""

    success: bool = Field(default=False)
    semester_id: int
    deleted_demands_count: int = Field(default=0, ge=0)
    preserved_manual_demands_count: int = Field(default=0, ge=0)
    blocked_demands_count: int = Field(default=0, ge=0)
    blocked_demands: list[str] = Field(default_factory=list)
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PROFESSOR Schemas
# ============================================================================


class ProfessorBase(BaseModel):
    """Base schema for Professor."""

    nome_completo: str = Field(..., min_length=1, max_length=255)
    username_login: Optional[str] = Field(default=None, max_length=100)
    tem_baixa_mobilidade: bool = Field(default=False)


class ProfessorCreate(ProfessorBase):
    """Schema for creating a new Professor."""

    pass


class ProfessorUpdate(BaseModel):
    """Schema for updating a Professor."""

    nome_completo: Optional[str] = Field(None, min_length=1, max_length=255)
    username_login: Optional[str] = Field(None, max_length=100)
    tem_baixa_mobilidade: Optional[bool] = None


class ProfessorRead(ProfessorBase):
    """Schema for reading Professor (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# USUARIO Schemas
# ============================================================================


class UsuarioBase(BaseModel):
    """Base schema for Usuario."""

    username: str = Field(..., min_length=3, max_length=100)
    nome_completo: Optional[str] = Field(None, max_length=255)
    role: str = Field(default="professor", max_length=50)


class UsuarioCreate(UsuarioBase):
    """Schema for creating a new Usuario.

    Note: Password is NOT stored here. Authentication is handled
    by streamlit-authenticator via YAML configuration.
    """

    pass


class UsuarioUpdate(BaseModel):
    """Schema for updating a Usuario."""

    username: Optional[str] = Field(None, min_length=3, max_length=100)
    nome_completo: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(None, max_length=50)


class UsuarioRead(UsuarioBase):
    """Schema for reading Usuario.

    Note: Password is never returned in DTO.
    Usuario table only has username/password_hash/nome_completo/role.
    """

    model_config = ConfigDict(from_attributes=True)
