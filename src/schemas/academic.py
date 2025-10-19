"""
Data Transfer Object schemas for Academic domain.

Schemas for: Semestre, Demanda, Professor, Usuario
"""

from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


# ============================================================================
# SEMESTRE Schemas
# ============================================================================


class SemestreBase(BaseModel):
    """Base schema for Semestre."""

    nome: str = Field(..., min_length=5, max_length=50)  # e.g., "2025.1"
    status: str = Field(default="Planejamento", max_length=50)


class SemestreCreate(SemestreBase):
    """Schema for creating a new Semestre."""

    pass


class SemestreUpdate(BaseModel):
    """Schema for updating a Semestre."""

    nome: Optional[str] = Field(None, min_length=5, max_length=50)
    status: Optional[str] = Field(None, max_length=50)


class SemestreRead(SemestreBase):
    """Schema for reading Semestre (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    nivel_disciplina: str = Field(default="", max_length=50)


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
    nivel_disciplina: Optional[str] = Field(None, max_length=50)


class DemandaRead(DemandaBase):
    """Schema for reading Demanda (includes timestamps)."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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
    """Schema for reading Usuario (includes timestamps).

    Note: Password is never returned in DTO.
    """

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
