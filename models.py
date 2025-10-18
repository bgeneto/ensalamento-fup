"""
Pydantic models for Sistema de Ensalamento FUP/UnB
Data validation and API response models
"""

from datetime import date, datetime, time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


class BaseResponse(BaseModel):
    """Base model for API responses"""

    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# Enums
class RoleEnum(str, Enum):
    ADMIN = "admin"
    PROFESSOR = "professor"


class SemestreStatusEnum(str, Enum):
    PLANEJAMENTO = "Planejamento"
    EXECUCAO = "Execução"
    FINALIZADO = "Finalizado"


class ReservaStatusEnum(str, Enum):
    APROVADA = "Aprovada"
    PENDENTE = "Pendente"
    CANCELADA = "Cancelada"


class TurnoEnum(str, Enum):
    MANHA = "M"
    TARDE = "T"
    NOITE = "N"


# Base Models
class BaseTimestampedModel(BaseModel):
    """Base model with timestamp fields"""

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Physical Structure Models
class Campus(BaseModel):
    """Campus model"""

    id: Optional[int] = None
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=500)

    class Config:
        from_attributes = True


class Predio(BaseModel):
    """Building model"""

    id: Optional[int] = None
    nome: str = Field(..., min_length=1, max_length=100)
    campus_id: int
    campus: Optional[Campus] = None

    class Config:
        from_attributes = True


class TipoSala(BaseModel):
    """Room type model"""

    id: Optional[int] = None
    nome: str = Field(..., min_length=1, max_length=50)
    descricao: Optional[str] = Field(None, max_length=500)

    class Config:
        from_attributes = True


class Caracteristica(BaseModel):
    """Room characteristic model"""

    id: Optional[int] = None
    nome: str = Field(..., min_length=1, max_length=100)

    class Config:
        from_attributes = True


class Sala(BaseModel):
    """Room model"""

    id: Optional[int] = None
    nome: str = Field(..., min_length=1, max_length=50)
    predio_id: int
    tipo_sala_id: int
    capacidade: int = Field(default=0, ge=0)
    andar: Optional[str] = Field(None, max_length=10)
    tipo_assento: Optional[str] = Field(None, max_length=50)
    predio: Optional[Predio] = None
    tipo_sala: Optional[TipoSala] = None
    caracteristicas: Optional[List[Caracteristica]] = []

    class Config:
        from_attributes = True

    @validator("capacidade")
    def validate_capacity(cls, v):
        if v < 0:
            raise ValueError("Capacity must be non-negative")
        return v


class SalaCaracteristica(BaseModel):
    """Room-characteristic relationship model"""

    sala_id: int
    caracteristica_id: int
    sala: Optional[Sala] = None
    caracteristica: Optional[Caracteristica] = None

    class Config:
        from_attributes = True


# Time Models
class DiaSemana(BaseModel):
    """Day of week model"""

    id_sigaa: int
    nome: str = Field(..., min_length=1, max_length=10)

    class Config:
        from_attributes = True


class HorarioBloco(BaseModel):
    """Time block model"""

    codigo_bloco: str = Field(..., min_length=2, max_length=3)
    turno: str = Field(..., min_length=1, max_length=1)
    horario_inicio: time
    horario_fim: time

    class Config:
        from_attributes = True

    @validator("horario_fim")
    def validate_time_order(cls, v, values):
        if "horario_inicio" in values and v <= values["horario_inicio"]:
            raise ValueError("End time must be after start time")
        return v


# Academic Models
class Semestre(BaseModel):
    """Semester model"""

    id: Optional[int] = None
    nome: str = Field(..., min_length=5, max_length=10, pattern=r"^\d{4}\.\d{1}$")
    status: SemestreStatusEnum = SemestreStatusEnum.PLANEJAMENTO

    class Config:
        from_attributes = True


class Demanda(BaseModel):
    """Demand model for semester courses"""

    id: Optional[int] = None
    semestre_id: int
    codigo_disciplina: str = Field(..., min_length=1, max_length=20)
    nome_disciplina: Optional[str] = Field(None, max_length=200)
    professores_disciplina: Optional[str] = Field(None, max_length=500)
    turma_disciplina: Optional[str] = Field(None, max_length=20)
    vagas_disciplina: Optional[int] = Field(None, ge=0)
    horario_sigaa_bruto: str = Field(..., min_length=1, max_length=50)
    nivel_disciplina: Optional[str] = Field(None, max_length=50)
    semestre: Optional[Semestre] = None

    class Config:
        from_attributes = True

    @validator("vagas_disciplina")
    def validate_vagas(cls, v):
        if v is not None and v < 0:
            raise ValueError("Number of vacancies must be non-negative")
        return v


# Rule Models
class Regra(BaseModel):
    """Allocation rule model"""

    id: Optional[int] = None
    descricao: str = Field(..., min_length=1, max_length=500)
    tipo_regra: str = Field(..., min_length=1, max_length=50)
    config_json: str = Field(..., min_length=1)
    prioridade: int = Field(default=1, ge=1, le=10)

    class Config:
        from_attributes = True


# Allocation Models
class AlocacaoSemestral(BaseModel):
    """Semester allocation model"""

    id: Optional[int] = None
    demanda_id: int
    sala_id: int
    dia_semana_id: int
    codigo_bloco: str
    demanda: Optional[Demanda] = None
    sala: Optional[Sala] = None
    dia_semana: Optional[DiaSemana] = None
    horario_bloco: Optional[HorarioBloco] = None

    class Config:
        from_attributes = True


# Reservation Models
class ReservaEsporadica(BaseModel):
    """Sporadic reservation model"""

    id: Optional[int] = None
    sala_id: int
    username_solicitante: str = Field(..., min_length=1, max_length=50)
    titulo_evento: str = Field(..., min_length=1, max_length=200)
    data_reserva: date
    codigo_bloco: str = Field(..., min_length=2, max_length=3)
    status: ReservaStatusEnum = ReservaStatusEnum.APROVADA
    sala: Optional[Sala] = None
    solicitante: Optional["Usuario"] = None
    horario_bloco: Optional[HorarioBloco] = None

    class Config:
        from_attributes = True

    @validator("data_reserva")
    def validate_date_not_past(cls, v):
        if v < date.today():
            raise ValueError("Reservation date cannot be in the past")
        return v


# User Models
class Usuario(BaseModel):
    """User model"""

    username: str = Field(..., min_length=3, max_length=50)
    password_hash: str = Field(..., min_length=60)  # bcrypt hash length
    nome_completo: Optional[str] = Field(None, max_length=200)
    role: RoleEnum = RoleEnum.PROFESSOR

    class Config:
        from_attributes = True


class UsuarioCreate(BaseModel):
    """User creation model"""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    nome_completo: Optional[str] = Field(None, max_length=200)
    role: RoleEnum = RoleEnum.PROFESSOR

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class UsuarioUpdate(BaseModel):
    """User update model"""

    nome_completo: Optional[str] = Field(None, max_length=200)
    role: Optional[RoleEnum] = None


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model"""

    username: str
    password: str


class LoginResponse(BaseResponse):
    """Login response model"""

    username: str
    nome_completo: Optional[str] = None
    role: str


# Database Models (for internal operations)
class DatabaseConnectionInfo(BaseModel):
    """Database connection information"""

    database_path: str
    is_connected: bool
    tables_count: int
    last_modified: Optional[datetime] = None


# Filter Models
class SalaFilter(BaseModel):
    """Room filter model"""

    predio_id: Optional[int] = None
    tipo_sala_id: Optional[int] = None
    capacidade_min: Optional[int] = None
    capacidade_max: Optional[int] = None
    caracteristicas: Optional[List[int]] = None


class ReservaFilter(BaseModel):
    """Reservation filter model"""

    sala_id: Optional[int] = None
    username_solicitante: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    status: Optional[ReservaStatusEnum] = None


# Search Models
class SearchRequest(BaseModel):
    """Search request model"""

    query: str = Field(..., min_length=1, max_length=200)
    tipo_busca: str = Field(
        default="todos", pattern=r"^(todos|salas|disciplinas|professores|reservas)$"
    )


# Export Models
class ExportRequest(BaseModel):
    """Export request model"""

    formato: str = Field(..., pattern=r"^(pdf|excel|csv)$")
    semestre_id: Optional[int] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    filtro_sala: Optional[List[int]] = None


# Utility Models
class AvailabilityCheck(BaseModel):
    """Availability check model"""

    sala_id: int
    data: date
    codigo_bloco: str
    is_available: bool
    conflicts: Optional[List[str]] = None


class AllocationRuleConfig(BaseModel):
    """Allocation rule configuration model"""

    professores_sala: Optional[Dict[str, int]] = {}  # professor -> sala_id
    disciplinas_tipo_sala: Optional[Dict[str, int]] = {}  # discipline -> tipo_sala_id
    capacidade_sugerida: Optional[Dict[str, int]] = {}  # discipline -> capacity
    preferencias: Optional[Dict[str, Any]] = {}


# Update Usuario model to include forward reference
Usuario.model_rebuild()


# INVENTORY MANAGEMENT MODELS


class CampusCreate(BaseModel):
    """Model for creating a campus"""

    nome: str
    descricao: Optional[str] = None


class CampusUpdate(BaseModel):
    """Model for updating a campus"""

    nome: Optional[str] = None
    descricao: Optional[str] = None


class PredioCreate(BaseModel):
    """Model for creating a building"""

    nome: str
    descricao: Optional[str] = None
    campus_id: int


class PredioUpdate(BaseModel):
    """Model for updating a building"""

    nome: Optional[str] = None
    descricao: Optional[str] = None
    campus_id: Optional[int] = None


class TipoSalaCreate(BaseModel):
    """Model for creating a room type"""

    nome: str
    descricao: Optional[str] = None


class TipoSalaUpdate(BaseModel):
    """Model for updating a room type"""

    nome: Optional[str] = None
    descricao: Optional[str] = None


class CaracteristicaCreate(BaseModel):
    """Model for creating a characteristic"""

    nome: str


class CaracteristicaUpdate(BaseModel):
    """Model for updating a characteristic"""

    nome: Optional[str] = None


class SalaCreate(BaseModel):
    """Model for creating a room"""

    nome: str
    capacidade: int
    andar: int
    predio_id: int
    tipo_sala_id: int
    caracteristicas: Optional[List[int]] = []


class SalaUpdate(BaseModel):
    """Model for updating a room"""

    nome: Optional[str] = None
    capacidade: Optional[int] = None
    andar: Optional[int] = None
    predio_id: Optional[int] = None
    tipo_sala_id: Optional[int] = None
    caracteristicas: Optional[List[int]] = None


# SEMESTER MANAGEMENT MODELS


class DemandaCreate(BaseModel):
    """Model for creating a demand"""

    semestre_id: int
    codigo_disciplina: str = Field(..., min_length=1, max_length=20)
    nome_disciplina: Optional[str] = Field(None, max_length=200)
    professores_disciplina: Optional[str] = Field(None, max_length=500)
    turma_disciplina: Optional[str] = Field(None, max_length=20)
    vagas_disciplina: Optional[int] = Field(None, ge=0)
    horario_sigaa_bruto: str = Field(..., min_length=1, max_length=50)
    nivel_disciplina: Optional[str] = Field(None, max_length=50)

    @validator("vagas_disciplina")
    def validate_vagas(cls, v):
        if v is not None and v < 0:
            raise ValueError("Number of vacancies must be non-negative")
        return v


class DemandaUpdate(BaseModel):
    """Model for updating a demand"""

    nome_disciplina: Optional[str] = Field(None, max_length=200)
    professores_disciplina: Optional[str] = Field(None, max_length=500)
    turma_disciplina: Optional[str] = Field(None, max_length=20)
    vagas_disciplina: Optional[int] = Field(None, ge=0)
    horario_sigaa_bruto: Optional[str] = Field(None, min_length=1, max_length=50)
    nivel_disciplina: Optional[str] = Field(None, max_length=50)

    @validator("vagas_disciplina")
    def validate_vagas(cls, v):
        if v is not None and v < 0:
            raise ValueError("Number of vacancies must be non-negative")
        return v


# ALLOCATION MANAGEMENT MODELS


class AlocacaoSemestralCreate(BaseModel):
    """Model for creating a semester allocation"""

    demanda_id: int = Field(..., gt=0)
    sala_id: int = Field(..., gt=0)
    dia_semana_id: int = Field(..., gt=0)
    codigo_bloco: str = Field(..., min_length=2, max_length=3)

    @validator("codigo_bloco")
    def validate_codigo_bloco(cls, v):
        if not v or len(v) < 2:
            raise ValueError("Time block code must be at least 2 characters")
        return v


class AlocacaoSemestralUpdate(BaseModel):
    """Model for updating a semester allocation"""

    sala_id: Optional[int] = Field(None, gt=0)
    dia_semana_id: Optional[int] = Field(None, gt=0)
    codigo_bloco: Optional[str] = Field(None, min_length=2, max_length=3)

    @validator("codigo_bloco")
    def validate_codigo_bloco(cls, v):
        if v is not None and len(v) < 2:
            raise ValueError("Time block code must be at least 2 characters")
        return v


class AllocationRuleCreate(BaseModel):
    """Model for creating an allocation rule"""

    descricao: str = Field(..., min_length=1, max_length=500)
    tipo_regra: str = Field(..., min_length=1, max_length=50)
    config_json: str = Field(..., min_length=1)
    prioridade: int = Field(default=1, ge=1, le=10)

    @validator("prioridade")
    def validate_prioridade(cls, v):
        if v < 1 or v > 10:
            raise ValueError("Priority must be between 1 and 10")
        return v
