"""
Data Transfer Objects (DTOs) for semester-related entities

These DTOs represent semesters and time management without any database connection.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


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


class SemestreSimplifiedDTO(BaseModel):
    """Simplified semester for lists/dropdowns"""

    id: int
    nome: str
    status: str

    class Config:
        from_attributes = True


# ============================================================================
# TIME-RELATED DTOs
# ============================================================================


class DiaSemanaDTO(BaseModel):
    """Day of week representation"""

    id_sigaa: int
    nome: str

    class Config:
        from_attributes = True


class HorarioBlocoDTO(BaseModel):
    """Time block representation"""

    codigo_bloco: str
    descricao: Optional[str] = None
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None

    class Config:
        from_attributes = True


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


class DemandaSimplifiedDTO(BaseModel):
    """Simplified demand for lists/dropdowns"""

    id: int
    codigo_disciplina: str
    nome_disciplina: str
    turma_disciplina: str

    class Config:
        from_attributes = True
