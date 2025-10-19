"""
Data Transfer Objects (DTOs) for room-related entities

DTOs are Pydantic models that represent data without any database connection.
They're completely safe to return from services and use in Streamlit pages.

Key benefits:
- No DetachedInstance errors
- Type-safe and validated
- Easy to serialize to JSON
- Clear API contracts
- Separation of concerns
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUM DTOs
# ============================================================================


class SemestreStatusDTO(str, Enum):
    """Semester status"""

    PLANEJAMENTO = "Planejamento"
    EXECUCAO = "Execução"
    FINALIZADO = "Finalizado"


class ReservaStatusDTO(str, Enum):
    """Reservation status"""

    APROVADA = "Aprovada"
    PENDENTE = "Pendente"
    CANCELADA = "Cancelada"


# ============================================================================
# CAMPUS DTOs
# ============================================================================


class CampusDTO(BaseModel):
    """Minimal campus representation"""

    id: int
    nome: str
    descricao: Optional[str] = None
    sigla: Optional[str] = None

    class Config:
        from_attributes = True


class CampusCreateDTO(BaseModel):
    """DTO for creating a campus"""

    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=500)
    sigla: Optional[str] = Field(None, max_length=10)


class CampusUpdateDTO(BaseModel):
    """DTO for updating a campus"""

    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=500)
    sigla: Optional[str] = Field(None, max_length=10)


# ============================================================================
# PREDIO (BUILDING) DTOs
# ============================================================================


class PredioDTO(BaseModel):
    """Minimal building representation"""

    id: int
    nome: str
    campus_id: int
    campus: Optional[CampusDTO] = None

    class Config:
        from_attributes = True


class PredioDetailDTO(PredioDTO):
    """Detailed building representation"""

    salas_count: Optional[int] = 0


class PredioCreateDTO(BaseModel):
    """DTO for creating a building"""

    nome: str = Field(..., min_length=1, max_length=100)
    campus_id: int


class PredioUpdateDTO(BaseModel):
    """DTO for updating a building"""

    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    campus_id: Optional[int] = None


# ============================================================================
# TIPO SALA (ROOM TYPE) DTOs
# ============================================================================


class TipoSalaDTO(BaseModel):
    """Room type representation"""

    id: int
    nome: str
    descricao: Optional[str] = None

    class Config:
        from_attributes = True


class TipoSalaCreateDTO(BaseModel):
    """DTO for creating a room type"""

    nome: str = Field(..., min_length=1, max_length=50)
    descricao: Optional[str] = Field(None, max_length=500)


class TipoSalaUpdateDTO(BaseModel):
    """DTO for updating a room type"""

    nome: Optional[str] = Field(None, min_length=1, max_length=50)
    descricao: Optional[str] = Field(None, max_length=500)


# ============================================================================
# CARACTERISTICA (CHARACTERISTIC) DTOs
# ============================================================================


class CaracteristicaDTO(BaseModel):
    """Room characteristic representation"""

    id: int
    nome: str

    class Config:
        from_attributes = True


class CaracteristicaCreateDTO(BaseModel):
    """DTO for creating a characteristic"""

    nome: str = Field(..., min_length=1, max_length=100)


class CaracteristicaUpdateDTO(BaseModel):
    """DTO for updating a characteristic"""

    nome: Optional[str] = Field(None, min_length=1, max_length=100)


# ============================================================================
# SALA (ROOM) DTOs - The Main Model
# ============================================================================


class SalaDTO(BaseModel):
    """
    Complete room representation with all nested data.

    This is the primary DTO returned from repositories.
    It contains all information about a room including related entities.
    """

    id: int
    nome: str
    codigo: Optional[str] = None
    capacidade: int
    andar: Optional[str] = None
    tipo_assento: Optional[str] = None

    # Relationships - represented as nested DTOs, not ORM objects
    predio: Optional[PredioDTO] = None
    tipo_sala: Optional[TipoSalaDTO] = None
    caracteristicas: List[CaracteristicaDTO] = []

    class Config:
        from_attributes = True


class SalaSimplifiedDTO(BaseModel):
    """Simplified room representation for lists"""

    id: int
    nome: str
    capacidade: int
    predio_nome: str
    tipo_sala_nome: str

    class Config:
        from_attributes = True


class SalaDetailDTO(SalaDTO):
    """Extended room details"""

    alocacoes_count: Optional[int] = 0
    reservas_count: Optional[int] = 0
    ultima_atualizacao: Optional[datetime] = None


class SalaCreateDTO(BaseModel):
    """DTO for creating a room"""

    nome: str = Field(..., min_length=1, max_length=50)
    codigo: Optional[str] = Field(None, max_length=20)
    predio_id: int
    tipo_sala_id: int
    capacidade: int = Field(..., gt=0, le=500)
    andar: Optional[str] = Field(None, max_length=10)
    tipo_assento: Optional[str] = Field(None, max_length=50)


class SalaUpdateDTO(BaseModel):
    """DTO for updating a room"""

    nome: Optional[str] = Field(None, min_length=1, max_length=50)
    codigo: Optional[str] = Field(None, max_length=20)
    predio_id: Optional[int] = None
    tipo_sala_id: Optional[int] = None
    capacidade: Optional[int] = Field(None, gt=0, le=500)
    andar: Optional[str] = Field(None, max_length=10)
    tipo_assento: Optional[str] = Field(None, max_length=50)


# ============================================================================
# RESPONSE DTOs
# ============================================================================


class ResponseDTO(BaseModel):
    """Generic response DTO"""

    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginatedResponseDTO(BaseModel):
    """Paginated response DTO"""

    success: bool = True
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def create_paginated_response(
    data: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 20,
    success: bool = True,
    message: Optional[str] = None,
) -> PaginatedResponseDTO:
    """Create a paginated response"""
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponseDTO(
        success=success,
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message=message,
    )


def create_response(
    data: Optional[Any] = None,
    success: bool = True,
    message: Optional[str] = None,
) -> ResponseDTO:
    """Create a response"""
    return ResponseDTO(
        success=success,
        message=message,
        data=data,
    )
