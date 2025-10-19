"""
COMPREHENSIVE REFACTORING STRATEGY: Eliminating DetachedInstance Errors

This document outlines a complete architectural redesign to eliminate SQLAlchemy
DetachedInstance errors in a Streamlit application.

Key Problems with Current Architecture:
1. Services return SQLAlchemy ORM models directly
2. ORM objects become detached when session closes
3. Streamlit pages try to access relationships on detached objects
4. No clear separation between DB layer and business logic
5. Mixing of ORM models and Pydantic models inconsistently

SOLUTION OVERVIEW:
==================

We'll implement a layered architecture:

┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Pages (UI)                      │
│              Consume DTOs, never access DB                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Service Layer (NEW)                        │
│        Returns DTOs/Dicts, never SQLAlchemy models           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│             Repository Layer (NEW)                           │
│    Handles all DB queries, session management               │
│    Converts ORM ↔ DTOs at this layer only                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│          Database Models (existing ORM)                      │
│              SQLAlchemy models (database.py)                 │
└─────────────────────────────────────────────────────────────┘

THREE DESIGN PATTERNS:
=====================

1. DATA TRANSFER OBJECTS (DTOs) - RECOMMENDED
   ✅ Use Pydantic models for all data transfer
   ✅ Complete isolation from SQLAlchemy
   ✅ Easy serialization (JSON-friendly)
   ✅ Type-safe and validated

   Example:
   class RoomDTO(BaseModel):
       id: int
       nome: str
       capacidade: int
       predio_nome: str
       tipo_sala_nome: str

2. REPOSITORY PATTERN
   ✅ Centralizes all DB queries
   ✅ Clean session management
   ✅ Easy to test (mock repositories)
   ✅ Clear separation of concerns

   Example:
   class RoomRepository:
       def get_all(self) -> List[RoomDTO]: ...
       def get_by_id(self, id: int) -> RoomDTO: ...

3. STREAMLIT SESSION STATE CACHING
   ✅ Cache DTOs in st.session_state
   ✅ Avoid repeated queries
   ✅ Reduce database load
   ✅ Faster UI response

   Example:
   if 'rooms' not in st.session_state:
       st.session_state.rooms = repository.get_all()
   rooms = st.session_state.rooms

IMPLEMENTATION PLAN:
====================

Phase 1: Create DTOs (Data Transfer Objects)
   → src/schemas/
   → Separate Pydantic models for each entity
   → Include relationships as nested DTOs
   → Complete separation from ORM

Phase 2: Create Repository Layer
   → src/repositories/
   → One repository per entity
   → All DB queries happen here
   → ORM ↔ DTO conversion happens here only
   → Proper session management

Phase 3: Refactor Services
   → Keep existing service interface
   → Change implementation to use repositories
   → Return DTOs instead of ORM models
   → Add logging for debugging

Phase 4: Update Streamlit Pages
   → Work with DTOs only
   → No direct DB access
   → Add session state caching
   → Simpler, cleaner pages

Phase 5: Migration (Optional)
   → Gradually migrate existing services
   → Full backward compatibility
   → Can refactor incrementally

BENEFITS OF THIS APPROACH:
==========================

1. ELIMINATES DETACHED INSTANCE ERRORS
   ✓ No ORM objects leave the repository layer
   ✓ All data is converted to DTOs before returning
   ✓ DTOs are just data, not tied to sessions

2. IMPROVES CODE MAINTAINABILITY
   ✓ Clear separation of concerns
   ✓ Easy to understand data flow
   ✓ Centralized DB logic
   ✓ Easy to add new features

3. ENHANCES PERFORMANCE
   ✓ Cache DTOs in Streamlit session state
   ✓ Reduce unnecessary DB queries
   ✓ Faster page loads
   ✓ Better user experience

4. ENABLES TESTING
   ✓ Mock repositories for unit tests
   ✓ No database needed for tests
   ✓ Fast test execution
   ✓ Easy to verify behavior

5. INCREASES RELIABILITY
   ✓ No more silent detached errors
   ✓ Clear error handling
   ✓ Type-safe throughout
   ✓ Validated data at boundaries

6. FUTURE-PROOFS THE CODE
   ✓ Easy to switch databases
   ✓ Easy to add caching layers
   ✓ Easy to add authentication/authorization
   ✓ Ready for REST API

FILE STRUCTURE AFTER REFACTORING:
==================================

src/
├── schemas/               (NEW - DTOs/Pydantic models)
│   ├── __init__.py
│   ├── campus.py         (CampusDTO, CampusCreateDTO, etc.)
│   ├── predio.py
│   ├── sala.py
│   ├── alocacao.py
│   ├── demanda.py
│   ├── usuario.py
│   └── ...
│
├── repositories/         (NEW - Data access layer)
│   ├── __init__.py
│   ├── base.py           (BaseRepository with common methods)
│   ├── campus.py         (CampusRepository)
│   ├── predio.py
│   ├── sala.py
│   ├── alocacao.py
│   ├── demanda.py
│   └── ...
│
├── services/             (REFACTORED - Business logic)
│   ├── inventory_service.py    (Uses repositories)
│   ├── allocation_service.py   (Uses repositories)
│   └── ...
│
├── utils/
│   ├── error_handler.py  (Existing)
│   └── ...
│
└── pages/
    └── ...               (Updated to use DTOs)

database.py              (ORM models - unchanged)
models.py               (Existing Pydantic models - can be kept as-is)

KEY IMPLEMENTATION DETAILS:
===========================

1. PYDANTIC DTO EXAMPLE:
```python
# src/schemas/sala.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PredioDTO(BaseModel):
    id: int
    nome: str

class TipoSalaDTO(BaseModel):
    id: int
    nome: str

class SalaDTO(BaseModel):
    id: int
    nome: str
    codigo: str
    capacidade: int
    andar: Optional[str]
    predio: PredioDTO           # ← Nested DTO
    tipo_sala: TipoSalaDTO      # ← Nested DTO
    caracteristicas: List[str]

class SalaCreateDTO(BaseModel):
    nome: str
    predio_id: int
    tipo_sala_id: int
    capacidade: int
    andar: Optional[str] = None
```

2. REPOSITORY PATTERN EXAMPLE:
```python
# src/repositories/sala.py
from typing import List, Optional
from database import DatabaseSession, Sala as SalaORM
from src.schemas.sala import SalaDTO, SalaCreateDTO

class SalaRepository:

    @staticmethod
    def get_all() -> List[SalaDTO]:
        """Get all rooms with relationships"""
        with DatabaseSession() as session:
            salas = session.query(SalaORM)\
                .options(
                    joinedload(SalaORM.predio),
                    joinedload(SalaORM.tipo_sala),
                    joinedload(SalaORM.caracteristicas)
                )\
                .all()

            # Convert ORM → DTO while still in session
            return [SalaRepository._orm_to_dto(s) for s in salas]

    @staticmethod
    def get_by_id(sala_id: int) -> Optional[SalaDTO]:
        """Get room by ID"""
        with DatabaseSession() as session:
            sala = session.query(SalaORM)\
                .options(
                    joinedload(SalaORM.predio),
                    joinedload(SalaORM.tipo_sala),
                    joinedload(SalaORM.caracteristicas)
                )\
                .filter(SalaORM.id == sala_id)\
                .first()

            if sala:
                return SalaRepository._orm_to_dto(sala)
            return None

    @staticmethod
    def _orm_to_dto(sala_orm: SalaORM) -> SalaDTO:
        """Convert ORM model to DTO"""
        return SalaDTO(
            id=sala_orm.id,
            nome=sala_orm.nome,
            codigo=sala_orm.codigo,
            capacidade=sala_orm.capacidade,
            andar=sala_orm.andar,
            predio=PredioDTO(
                id=sala_orm.predio.id,
                nome=sala_orm.predio.nome
            ),
            tipo_sala=TipoSalaDTO(
                id=sala_orm.tipo_sala.id,
                nome=sala_orm.tipo_sala.nome
            ),
            caracteristicas=[c.nome for c in sala_orm.caracteristicas]
        )
```

3. SERVICE LAYER EXAMPLE:
```python
# src/services/inventory_service.py (REFACTORED)
from typing import List, Optional
from src.repositories.sala import SalaRepository
from src.schemas.sala import SalaDTO, SalaCreateDTO

class InventoryService:

    @classmethod
    def get_all_salas(cls) -> List[SalaDTO]:
        """Get all rooms - returns DTOs only"""
        try:
            return SalaRepository.get_all()
        except Exception as e:
            logger.exception(f"Error getting salas: {e}")
            return []

    @classmethod
    def get_sala_by_id(cls, sala_id: int) -> Optional[SalaDTO]:
        """Get room by ID - returns DTO only"""
        try:
            return SalaRepository.get_by_id(sala_id)
        except Exception as e:
            logger.exception(f"Error getting sala: {e}")
            return None
```

4. STREAMLIT PAGE EXAMPLE:
```python
# pages/3_Admin_Rooms.py (REFACTORED)
import streamlit as st
from src.services.inventory_service import InventoryService

# Use Streamlit session state for caching
if 'rooms' not in st.session_state:
    st.session_state.rooms = InventoryService.get_all_salas()

rooms = st.session_state.rooms  # ← List of DTOs, not ORM objects

for room in rooms:
    # ✅ No detached instance errors - it's just data!
    st.write(f"Room: {room.nome}")
    st.write(f"Building: {room.predio.nome}")  # ← Nested DTO, safe
    st.write(f"Capacity: {room.capacidade}")
```

MIGRATION STRATEGY:
===================

Option A: BIG BANG (All at once)
- Pros: Complete solution quickly
- Cons: Risk of breaking everything
- Time: 2-3 days
- Recommended if: Small codebase, good test coverage

Option B: INCREMENTAL (One service at a time)
- Pros: Lower risk, can test gradually
- Cons: Takes longer, mixed architecture temporarily
- Time: 1-2 weeks
- Recommended if: Large codebase, critical stability

INCREMENTAL APPROACH:
Step 1: Create repository for Salas
Step 2: Refactor InventoryService
Step 3: Update pages using InventoryService
Step 4: Repeat for other services
Step 5: Remove old code when done

ERROR HANDLING BENEFITS:
========================

Current approach with repositories and DTOs:
```
Session closes → DTO returned → No error
         ↓
    DTO used in page → Still no error
         ↓
    ✅ Clean, simple, no DetachedInstance
```

Versus current approach:
```
Session closes → ORM returned → Object detached
         ↓
    Page tries .relationship → ❌ DetachedInstanceError
```

TESTING BENEFITS:
=================

With repositories, testing is easy:

```python
# tests/test_repositories/test_sala.py
from unittest.mock import Mock, patch
from src.repositories.sala import SalaRepository
from src.schemas.sala import SalaDTO

def test_get_all_salas():
    """Test getting all rooms"""
    # Mock the DatabaseSession
    mock_orm_objects = [...]  # Create mock ORM objects

    # Would be called by repository
    # No real database needed!
    dtos = SalaRepository.get_all()

    assert len(dtos) > 0
    assert all(isinstance(d, SalaDTO) for d in dtos)

def test_get_sala_by_id():
    """Test getting single room"""
    dto = SalaRepository.get_by_id(1)

    assert dto is not None
    assert dto.id == 1
```

PERFORMANCE OPTIMIZATION:
=========================

With DTOs and Streamlit session state:

```python
import streamlit as st
import time

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_rooms_cached():
    """Cached version - avoids repeated queries"""
    return InventoryService.get_all_salas()

# First load: hits database
start = time.time()
rooms = get_rooms_cached()
# Takes 200ms

# Subsequent loads: uses cache
rooms = get_rooms_cached()
# Takes 2ms (100x faster!)
```

BACKWARDS COMPATIBILITY:
========================

The services can maintain their interface:

```python
# Old interface (can stay the same)
def get_all_salas():  # ← Same method name
    return SalaRepository.get_all()  # ← Just different internals

# Callers don't need to change:
rooms = InventoryService.get_all_salas()  # ← Works the same
for room in rooms:
    print(room.nome)  # ← DTOs have the same attributes
```

NEXT STEPS:
===========

1. Review this strategy document
2. Choose migration approach (Big Bang vs Incremental)
3. Create base repository class
4. Create schema/DTOs for all entities
5. Implement repositories one by one
6. Refactor services to use repositories
7. Update pages to use DTOs
8. Run full test suite
9. Deploy with confidence

ESTIMATED TIME:
===============

Phase 1 (DTOs): 1-2 hours
Phase 2 (Base Repository): 1-2 hours
Phase 3 (Service Repositories): 4-6 hours
Phase 4 (Service Refactoring): 2-3 hours
Phase 5 (Page Updates): 2-3 hours
Phase 6 (Testing): 2-3 hours
Phase 7 (Deployment): 1 hour

TOTAL: 13-20 hours (~2-3 days of active work)

This is an investment that will pay dividends through:
- Eliminated DetachedInstance errors
- Faster development
- Easier testing
- Better code quality
- Clearer architecture
- Future-ready design

QUESTIONS?
==========

This document provides a complete blueprint for eliminating the DetachedInstance
problem. The repository pattern with DTOs is a proven approach used in enterprise
applications.

Key principles:
✓ All DB access in repositories only
✓ All conversions at repository boundary
✓ Services and pages only work with DTOs
✓ Sessions never leave repository layer
✓ Clear, layered architecture
✓ Easy to understand and maintain
"""
