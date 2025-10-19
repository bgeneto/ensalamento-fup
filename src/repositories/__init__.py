"""
Repositories Module

This module contains all repository implementations following the repository pattern.
Each repository encapsulates all database queries for a specific entity and handles
the conversion between ORM models and DTOs.

Key principles:
- All database access goes through repositories
- Repositories convert ORM objects to DTOs at the boundary
- Services receive DTOs, never ORM objects
- Streamlit pages work only with DTOs
- No detached instance errors

Usage:
```python
from src.repositories.sala import get_sala_repository

repo = get_sala_repository()
rooms = repo.get_all_with_eager_load()  # Returns List[SalaDTO]
```
"""

from src.repositories.sala import SalaRepository, get_sala_repository
from src.repositories.alocacao import AlocacaoRepository, get_alocacao_repository
from src.repositories.usuario import UsuarioRepository, get_usuario_repository
from src.repositories.semestre import (
    SemestreRepository,
    DemandaRepository,
    get_semestre_repository,
    get_demanda_repository,
)

__all__ = [
    # Sala
    "SalaRepository",
    "get_sala_repository",
    # Alocacao
    "AlocacaoRepository",
    "get_alocacao_repository",
    # Usuario
    "UsuarioRepository",
    "get_usuario_repository",
    # Semestre & Demanda
    "SemestreRepository",
    "DemandaRepository",
    "get_semestre_repository",
    "get_demanda_repository",
]
