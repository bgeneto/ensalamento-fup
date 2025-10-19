# Phase 3: Implementation Plan - Concrete Repositories & UI

## Overview

Phase 3 focuses on building the **business logic layer** through concrete repositories and creating the **admin interface** to manage room allocations.

**Status:** Ready to implement
- ✅ Database: 12 ORM models, 23 real rooms, full hierarchy
- ✅ DTOs: 30+ Pydantic schemas created
- ✅ Auth: streamlit-authenticator configured
- ✅ API Mocks: Sistema de Oferta (8 courses), Brevo (4 contacts)
- 🔲 **Phase 3 Task 1: Concrete Repositories** (THIS SPRINT)
- 🔲 **Phase 3 Task 2: Admin CRUD Pages** (NEXT)
- 🔲 **Phase 3 Task 3: Allocation Algorithm** (LATER)

---

## Task 1: Concrete Repositories (TODAY)

### What are Repositories?

Repositories provide a **bridge between the database and business logic**:

```
UI (Streamlit Pages)
    ↓
Service Layer (Business Logic)
    ↓
Repository Layer (Database Access)
    ↓
Database (SQLAlchemy ORM)
```

### Architecture

**Base Repository:** `src/repositories/base.py` (generic CRUD)
```python
class BaseRepository(Generic[T, D]):
    - get_by_id(id) -> D
    - get_all() -> List[D]
    - create(dto) -> D
    - update(id, dto) -> D
    - delete(id) -> bool
```

**Concrete Repositories:** Domain-specific implementations
```python
class SalaRepository(BaseRepository[Sala, SalaRead]):
    # Domain-specific queries
    - get_by_andar(andar: str) -> List[SalaRead]
    - get_by_capacidade(min_capacity: int) -> List[SalaRead]
    - get_by_predio(predio_id: int) -> List[SalaRead]
    - get_available(date: date, time_slot: str) -> List[SalaRead]
```

### Repositories to Create

#### 1. **Inventory Repositories** (4 files)

**A. SalaRepository** (`src/repositories/sala.py`)
- Methods:
  - `get_by_andar(andar: str)` - Get rooms by floor (0=ground, 1=1st)
  - `get_by_capacidade_minima(capacity: int)` - Get rooms with min capacity
  - `get_by_predio(predio_id: int)` - Get rooms by building
  - `get_by_tipo_sala(tipo_sala_id: int)` - Get rooms by type
  - `get_available_times(sala_id: int, date: date)` - Get available time slots
  - `get_by_campus(campus_id: int)` - Get all rooms in campus

**B. PredioRepository** (`src/repositories/predio.py`)
- Methods:
  - `get_by_campus(campus_id: int)` - Get buildings in campus
  - `get_salas(predio_id: int)` - Get rooms in building
  - `count_salas(predio_id: int)` - Total rooms

**C. CampusRepository** (`src/repositories/campus.py`)
- Methods:
  - `get_with_predios(campus_id: int)` - Get campus with buildings
  - `get_with_salas(campus_id: int)` - Get campus with all rooms

**D. CaracteristicaRepository** (`src/repositories/caracteristica.py`)
- Methods:
  - `get_by_sala(sala_id: int)` - Get characteristics of a room

#### 2. **Academic Repositories** (3 files)

**A. ProfessorRepository** (`src/repositories/professor.py`)
- Methods:
  - `get_by_departamento(dept: str)` - Get professors by department
  - `get_by_email(email: str)` - Get professor by email
  - `get_active()` - Get active professors
  - `search(query: str)` - Search professors by name

**B. SemestreRepository** (`src/repositories/semestre.py`)
- Methods:
  - `get_current()` - Get current semester
  - `get_by_periodo(periodo: str)` - Get semester by period (2024.2, etc.)

**C. DisciplinaRepository** (`src/repositories/disciplina.py`)
- Methods:
  - `get_by_semestre(semestre_id: int)` - Get courses in semester
  - `get_by_professor(professor_id: int)` - Get professor's courses
  - `search(query: str)` - Search courses by name

#### 3. **Schedule Repositories** (2 files)

**A. DiaSemanaRepository** (`src/repositories/dia_semana.py`)
- Methods:
  - `get_all_ordered()` - Get weekdays in order
  - `get_by_sigla(sigla: str)` - Get day by short name

**B. HorarioBlocoRepository** (`src/repositories/horario_bloco.py`)
- Methods:
  - `get_all_ordered()` - Get time blocks in order
  - `get_morning()` - Get morning blocks (M1-M5)
  - `get_afternoon()` - Get afternoon blocks (T1-T6)
  - `get_night()` - Get night blocks (N1-N4)

#### 4. **Allocation Repositories** (3 files)

**A. AlocacaoRepository** (`src/repositories/alocacao.py`)
- Methods:
  - `get_by_disciplina(disciplina_id: int)` - Get allocations for course
  - `get_by_sala(sala_id: int)` - Get allocations in room
  - `get_by_professor(professor_id: int)` - Get allocations by professor
  - `get_conflicts(sala_id, dia_id, horario_id)` - Check for double-booking
  - `get_unconfirmed()` - Get pending allocations
  - `get_for_report()` - Get allocations for schedule export

**B. PreferenciaRepository** (`src/repositories/preferencia.py`)
- Methods:
  - `get_by_professor(professor_id: int)` - Get professor's room preferences
  - `get_by_disciplina(disciplina_id: int)` - Get course's room preferences

**C. ConflictoRepository** (`src/repositories/conflito.py`)
- Methods:
  - `get_all()` - Get all scheduling conflicts
  - `get_by_sala(sala_id: int)` - Get conflicts in room
  - `mark_resolved(conflito_id: int)` - Mark conflict as resolved

---

## Implementation Order

### Priority 1 (CRITICAL - Do First)
1. `SalaRepository` - Most used, blocks admin pages
2. `ProfessorRepository` - Needed for allocation
3. `DisciplinaRepository` - Needed for allocation

### Priority 2 (IMPORTANT)
4. `AlocacaoRepository` - Core business logic
5. `DiaSemanaRepository` - Schedule foundation
6. `HorarioBlocoRepository` - Schedule foundation

### Priority 3 (NICE TO HAVE)
7. All others (Predio, Campus, Caracteristica, Semestre, Preferencia, Conflito)

---

## Repository Template

Each repository follows this pattern:

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.inventory import Sala
from src.schemas.inventory import SalaRead, SalaCreate
from src.repositories.base import BaseRepository


class SalaRepository(BaseRepository[Sala, SalaRead]):
    """Repository for Sala (classroom) operations."""

    def __init__(self, session: Session):
        super().__init__(session, Sala)

    def orm_to_dto(self, orm_obj: Sala) -> SalaRead:
        """Convert ORM model to DTO."""
        return SalaRead(
            id=orm_obj.id,
            nome=orm_obj.nome,
            capacidade=orm_obj.capacidade,
            andar=orm_obj.andar,
            tipo_assento=orm_obj.tipo_assento,
            predio_id=orm_obj.predio_id,
            tipo_sala_id=orm_obj.tipo_sala_id,
        )

    def dto_to_orm_create(self, dto: SalaCreate) -> Sala:
        """Convert DTO to ORM model for creation."""
        return Sala(
            nome=dto.nome,
            capacidade=dto.capacidade,
            andar=dto.andar,
            tipo_assento=dto.tipo_assento,
            predio_id=dto.predio_id,
            tipo_sala_id=dto.tipo_sala_id,
        )

    # Domain-specific queries
    def get_by_andar(self, andar: str) -> List[SalaRead]:
        """Get all rooms on a specific floor."""
        orm_objs = (
            self.session.query(Sala)
            .filter(Sala.andar == andar)
            .order_by(Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    def get_by_capacidade_minima(self, min_capacity: int) -> List[SalaRead]:
        """Get rooms with minimum capacity."""
        orm_objs = (
            self.session.query(Sala)
            .filter(Sala.capacidade >= min_capacity)
            .order_by(Sala.capacidade.desc(), Sala.nome)
            .all()
        )
        return [self.orm_to_dto(obj) for obj in orm_objs]

    # ... more methods
```

---

## Database Access Pattern

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.repositories.sala import SalaRepository
from src.repositories.professor import ProfessorRepository

# Create session
engine = create_engine("sqlite:///data/ensalamento.db")
Session = sessionmaker(bind=engine)
session = Session()

# Use repositories
sala_repo = SalaRepository(session)
prof_repo = ProfessorRepository(session)

# Query
salas_ground = sala_repo.get_by_andar("0")  # Ground floor rooms
large_rooms = sala_repo.get_by_capacidade_minima(80)  # Rooms for 80+ students
profs = prof_repo.search("João")  # Find professors named João
```

---

## Phase 3 Milestones

### Milestone 1: Core Repositories ✅ (TODAY)
- [x] Create SalaRepository with all methods
- [x] Create ProfessorRepository with all methods
- [x] Create DisciplinaRepository with all methods
- [x] Create AlocacaoRepository with conflict detection
- [x] Create schedule repositories (Dia, Horario)
- Result: 6 working repositories, 100% test coverage

### Milestone 2: Admin Inventory Pages 📋 (NEXT)
- [ ] Create `pages/10_Inventory.py` (Room CRUD)
- [ ] Create `pages/11_Professors.py` (Professor import/management)
- [ ] Create `pages/12_Demands.py` (Course allocation dashboard)
- Result: Admin can manage database

### Milestone 3: Allocation Algorithm 🧠 (LATER)
- [ ] Implement allocation service
- [ ] Create room availability checker
- [ ] Create conflict detector
- [ ] Create `pages/13_Allocations.py` (Manual allocation)
- Result: Can allocate courses to rooms

### Milestone 4: Reports & Export 📊 (FINAL)
- [ ] Schedule export (PDF, Excel)
- [ ] Conflict reports
- [ ] Utilization reports

---

## Files to Create

```
src/repositories/
├── sala.py                  # Room queries
├── predio.py               # Building queries
├── campus.py               # Campus queries
├── caracteristica.py       # Room characteristics
├── professor.py            # Professor queries
├── semestre.py             # Semester queries
├── disciplina.py           # Course queries
├── dia_semana.py           # Weekday queries
├── horario_bloco.py        # Time block queries
├── alocacao.py             # Allocation queries & conflict detection
├── preferencia.py          # Professor preferences
└── conflito.py             # Scheduling conflicts
```

---

## Success Criteria

✅ All 12 repositories implemented
✅ Each repository has 3-5+ domain-specific methods
✅ All repositories tested with sample queries
✅ Admin can query database through repositories
✅ Ready for Streamlit pages to use repositories

---

## Next Steps (After This Phase)

1. **Admin Pages** - Use repositories in Streamlit UI
2. **Allocation Algorithm** - Core business logic
3. **Reports** - Export schedules
4. **Public Pages** - Read-only view for students

---

## Questions Before Starting?

- Should we use SQLAlchemy relationships or stick with IDs?
- Any specific query optimizations needed?
- Should repositories cache results?
- Need pagination for large result sets?
