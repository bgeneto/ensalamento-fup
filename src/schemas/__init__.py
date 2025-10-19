"""
Schemas Module (DTOs - Data Transfer Objects)

This module contains Pydantic models that represent data in a database-agnostic way.
DTOs are used as the boundary between the database layer and the rest of the application.

Key benefits:
- Complete separation from SQLAlchemy ORM
- Type-safe and validated
- Easy to serialize to JSON
- No detached instance errors
- Clear API contracts

Usage:
```python
from src.schemas.sala import SalaDTO, SalaCreateDTO

# Receive a DTO from service
room: SalaDTO = service.get_sala_by_id(1)

# Use in Streamlit
st.write(f"Room: {room.nome}")
st.write(f"Building: {room.predio.nome}")  # Nested DTO - safe!

# Create new room
new_room_data = SalaCreateDTO(
    nome="New Room",
    predio_id=1,
    tipo_sala_id=1,
    capacidade=30
)
created = service.create_sala(new_room_data)
```
"""

from src.schemas.sala import (
    SalaDTO,
    SalaSimplifiedDTO,
    SalaDetailDTO,
    SalaCreateDTO,
    SalaUpdateDTO,
    PredioDTO,
    TipoSalaDTO,
    CaracteristicaDTO,
    CampusDTO,
    ResponseDTO,
    PaginatedResponseDTO,
    create_response,
    create_paginated_response,
)
from src.schemas.alocacao import (
    AlocacaoSemestralDTO,
    AlocacaoCreateDTO,
    AlocacaoUpdateDTO,
    AlocacaoSimplifiedDTO,
    DiaSemanaDTO,
    HorarioBlocoDTO,
)
from src.schemas.usuario import (
    UsuarioDTO,
    UsuarioCreateDTO,
    UsuarioUpdateDTO,
    UsuarioSimplifiedDTO,
    LoginRequestDTO,
    LoginResponseDTO,
    ChangePasswordDTO,
    RoleEnum,
)
from src.schemas.semestre import (
    SemestreDTO,
    SemestreCreateDTO,
    SemestreUpdateDTO,
    SemestreSimplifiedDTO,
    DemandaDTO,
    DemandaCreateDTO,
    DemandaUpdateDTO,
    DemandaSimplifiedDTO,
    SemestreStatusEnum,
)

__all__ = [
    # Sala DTOs
    "SalaDTO",
    "SalaSimplifiedDTO",
    "SalaDetailDTO",
    "SalaCreateDTO",
    "SalaUpdateDTO",
    "PredioDTO",
    "TipoSalaDTO",
    "CaracteristicaDTO",
    "CampusDTO",
    # Alocacao DTOs
    "AlocacaoSemestralDTO",
    "AlocacaoCreateDTO",
    "AlocacaoUpdateDTO",
    "AlocacaoSimplifiedDTO",
    "DiaSemanaDTO",
    "HorarioBlocoDTO",
    # Usuario DTOs
    "UsuarioDTO",
    "UsuarioCreateDTO",
    "UsuarioUpdateDTO",
    "UsuarioSimplifiedDTO",
    "LoginRequestDTO",
    "LoginResponseDTO",
    "ChangePasswordDTO",
    "RoleEnum",
    # Semestre DTOs
    "SemestreDTO",
    "SemestreCreateDTO",
    "SemestreUpdateDTO",
    "SemestreSimplifiedDTO",
    "DemandaDTO",
    "DemandaCreateDTO",
    "DemandaUpdateDTO",
    "DemandaSimplifiedDTO",
    "SemestreStatusEnum",
    # Response helpers
    "ResponseDTO",
    "PaginatedResponseDTO",
    "create_response",
    "create_paginated_response",
]

__all__ = [
    "SalaDTO",
    "SalaSimplifiedDTO",
    "SalaDetailDTO",
    "SalaCreateDTO",
    "SalaUpdateDTO",
    "PredioDTO",
    "TipoSalaDTO",
    "CaracteristicaDTO",
    "CampusDTO",
    "ResponseDTO",
    "PaginatedResponseDTO",
    "create_response",
    "create_paginated_response",
]
