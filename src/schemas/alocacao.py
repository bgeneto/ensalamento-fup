"""
Data Transfer Objects (DTOs) for allocation-related entities

These DTOs represent semester allocations without any database connection.
They provide a complete, type-safe representation of allocation data.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============================================================================
# ALLOCATION DTOs
# ============================================================================


class DiaSemanaDTO(BaseModel):
    """Day of week DTO"""

    id_sigaa: int
    nome: str

    class Config:
        from_attributes = True


class HorarioBlocoDTO(BaseModel):
    """Time block DTO"""

    codigo_bloco: str
    descricao: Optional[str] = None
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None

    class Config:
        from_attributes = True


class AlocacaoSemestralDTO(BaseModel):
    """Complete semester allocation representation"""

    id: int
    demanda_id: int
    sala_id: int
    dia_semana_id: int
    codigo_bloco: str
    # Nested relationships (converted to DTOs to prevent detached objects)
    demanda: Optional[Dict[str, Any]] = None  # Will be populated in repository
    sala_nome: Optional[str] = None
    sala_capacidade: Optional[int] = None
    predio_nome: Optional[str] = None
    dia_semana_nome: Optional[str] = None
    horario_bloco: Optional[HorarioBlocoDTO] = None
    disciplina_codigo: Optional[str] = None
    disciplina_nome: Optional[str] = None
    turma: Optional[str] = None

    class Config:
        from_attributes = True


class AlocacaoCreateDTO(BaseModel):
    """DTO for creating allocations"""

    demanda_id: int
    sala_id: int
    dia_semana_id: int
    codigo_bloco: str


class AlocacaoUpdateDTO(BaseModel):
    """DTO for updating allocations"""

    sala_id: Optional[int] = None
    dia_semana_id: Optional[int] = None
    codigo_bloco: Optional[str] = None


class AlocacaoSimplifiedDTO(BaseModel):
    """Simplified allocation for lists/dropdowns"""

    id: int
    sala_nome: str
    disciplina_codigo: str
    disciplina_nome: str
    dia_semana_nome: str
    horario_bloco: str

    class Config:
        from_attributes = True


# ============================================================================
# SEMESTER DTOs
# ============================================================================


class SemestreStatusEnum(str):
    """Semester status values"""

    PLANEJAMENTO = "Planejamento"
    EXECUCAO = "Execução"
    FINALIZADO = "Finalizado"


class SemestreDTO(BaseModel):
    """Complete semester representation"""

    id: int
    nome: str
    status: str
    demandas_count: int = 0
    alocacoes_count: int = 0

    class Config:
        from_attributes = True


class SemestreCreateDTO(BaseModel):
    """DTO for creating semesters"""

    nome: str = Field(..., min_length=1, max_length=10)
    status: str = Field(default="Planejamento")


class SemestreUpdateDTO(BaseModel):
    """DTO for updating semesters"""

    nome: Optional[str] = None
    status: Optional[str] = None


# ============================================================================
# DEMAND DTOs
# ============================================================================


class DemandaDTO(BaseModel):
    """Complete demand representation"""

    id: int
    semestre_id: int
    codigo_disciplina: str
    nome_disciplina: Optional[str] = None
    professores_disciplina: Optional[str] = None
    turma_disciplina: Optional[str] = None
    vagas_disciplina: Optional[int] = None
    horario_sigaa_bruto: str
    nivel_disciplina: Optional[str] = None
    alocacoes_count: int = 0

    class Config:
        from_attributes = True


class DemandaCreateDTO(BaseModel):
    """DTO for creating demands"""

    semestre_id: int
    codigo_disciplina: str = Field(..., min_length=1, max_length=20)
    nome_disciplina: Optional[str] = None
    professores_disciplina: Optional[str] = None
    turma_disciplina: Optional[str] = None
    vagas_disciplina: Optional[int] = None
    horario_sigaa_bruto: str
    nivel_disciplina: Optional[str] = None


class DemandaUpdateDTO(BaseModel):
    """DTO for updating demands"""

    nome_disciplina: Optional[str] = None
    professores_disciplina: Optional[str] = None
    turma_disciplina: Optional[str] = None
    vagas_disciplina: Optional[int] = None
    nivel_disciplina: Optional[str] = None


# ============================================================================
# RESPONSE DTOs
# ============================================================================


class ResponseDTO(BaseModel):
    """Generic response wrapper"""

    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginatedResponseDTO(BaseModel):
    """Paginated response wrapper"""

    success: bool = True
    message: Optional[str] = None
    data: List[Dict[str, Any]] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def create_response(data: Any, message: str = "", success: bool = True) -> ResponseDTO:
    """Create a response DTO"""
    return ResponseDTO(
        success=success,
        message=message,
        data=data if isinstance(data, dict) else {"result": data},
    )


def create_paginated_response(
    data: List[Any], total: int, page: int = 1, page_size: int = 10
) -> PaginatedResponseDTO:
    """Create a paginated response DTO"""
    return PaginatedResponseDTO(
        success=True,
        data=data,
        total=total,
        page=page,
        page_size=page_size,
    )
