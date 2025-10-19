# Architecture Visualization - Repository Pattern Implementation

## 1. Problem → Solution Flow

```
BEFORE (Broken):
┌─────────────┐
│Streamlit    │
│  Page       │
└──────┬──────┘
       │ wants data
       ↓
┌─────────────────┐
│Service Layer    │
│InventoryService│
└──────┬──────────┘
       │ queries database
       ↓
┌─────────────────┐
│SQLAlchemy ORM   │
│Session.query()  │
└──────┬──────────┘
       │ returns ORM objects
       ↓
┌─────────────────┐    ← Session closes
│Page tries to    │       Objects DETACH
│access nested    │
│relationships    │
│room.predio      │
│  .nome          │
└─────────────────┘
       │
       ↓ ❌ CRASH!
  DetachedInstance
     ERROR


AFTER (Fixed):
┌─────────────┐
│Streamlit    │
│  Page       │
└──────┬──────┘
       │ wants data
       ↓
┌──────────────────┐
│Service Layer     │
│(Refactored)      │
└──────┬───────────┘
       │ uses repository
       ↓
┌──────────────────┐
│Repository Layer  │  ← NEW!
│  SalaRepository  │
│ orm_to_dto()     │
└──────┬───────────┘
       │
       ├─ Opens Session
       ├─ Queries ORM
       ├─ Converts to DTO (while session open)
       └─ Closes Session
       │
       ↓ returns DTO (no DB connection)
┌──────────────────┐
│DTO Object       │
│ (safe to return) │
└──────┬───────────┘
       │
       ↓
│Page accesses:   │
│room.predio.nome │ ✓ Works! Safe!
└──────────────────┘
```

## 2. Layered Architecture Detailed View

```
╔════════════════════════════════════════════════════════╗
║            STREAMLIT UI LAYER                          ║
║  pages/3_Admin_Rooms.py                                ║
║  pages/4_Admin_Allocations.py                          ║
║  pages/2_Admin_Users.py                                ║
║  ────────────────────────────────────────────────      ║
║  • Displays data                                       ║
║  • User interactions                                   ║
║  • Works with DTOs ONLY                                ║
║  • NEVER touches database                              ║
╚═════════════════════╤══════════════════════════════════╝
                      │ imports
                      ↓
╔════════════════════════════════════════════════════════╗
║            SERVICE LAYER                               ║
║  inventory_service_refactored.py                       ║
║  allocation_service_refactored.py (TODO)               ║
║  semester_service_refactored.py (TODO)                 ║
║  auth_service_refactored.py (TODO)                     ║
║  ────────────────────────────────────────────────      ║
║  • Business logic                                      ║
║  • Uses repositories                                   ║
║  • Returns DTOs                                        ║
║  • Error handling                                      ║
╚═════════════════════╤══════════════════════════════════╝
                      │ uses
                      ↓
╔════════════════════════════════════════════════════════╗
║         REPOSITORY LAYER (NEW - Core Pattern)          ║
║                                                        ║
║  src/repositories/                                     ║
║  ├── base.py (BaseRepository<T, D>)                    ║
║  ├── sala.py (SalaRepository) ✓ DONE                   ║
║  ├── alocacao.py (AlocacaoRepository) ✓ DONE           ║
║  ├── usuario.py (UsuarioRepository) ✓ DONE             ║
║  └── semestre.py (Semestre + DemandaRepository) ✓ DONE ║
║                                                        ║
║  ────────────────────────────────────────────────      ║
║  • All database queries live here                      ║
║  • Session management (open/close)                     ║
║  • ORM ↔ DTO conversion (KEY!)                         ║
║  • Eager loading prevents N+1 queries                  ║
║  • Error handling                                      ║
║  • Custom query methods (search, filter, etc)          ║
║                                                        ║
║  Pattern for each repository:                          ║
║  ┌─────────────────────────────────────┐               ║
║  │ def get_all():                      │               ║
║  │   with DatabaseSession():           │ ← session open
║  │     orm_objects = query()           │               ║
║  │     return [orm_to_dto(obj)          │ ← convert NOW
║  │            for obj in orm_objects]   │               ║
║  │ ← session closes, DTOs are safe ✓   │               ║
║  └─────────────────────────────────────┘               ║
╚═════════════════════╤══════════════════════════════════╝
                      │ uses ORM, returns DTO
                      ↓
╔════════════════════════════════════════════════════════╗
║          ORM LAYER (SQLAlchemy)                        ║
║                                                        ║
║  database.py models:                                   ║
║  • Campus                                              ║
║  • Predio                                              ║
║  • Sala                                                ║
║  • AlocacaoSemestral                                   ║
║  • Usuario                                             ║
║  • Semestre                                            ║
║  • Demanda                                             ║
║  • etc.                                                ║
║                                                        ║
║  ────────────────────────────────────────────────      ║
║  • SQLAlchemy model definitions                        ║
║  • Relationships defined here                          ║
║  • NEVER accessed directly by pages/services           ║
║  • ONLY used inside repositories                       ║
║  • Objects become detached outside session             ║
╚═════════════════════╤══════════════════════════════════╝
                      │ uses
                      ↓
╔════════════════════════════════════════════════════════╗
║          DTO LAYER (Pydantic Models)                   ║
║                                                        ║
║  src/schemas/                                          ║
║  ├── sala.py       (SalaDTO, etc) ✓ DONE               ║
║  ├── alocacao.py   (AlocacaoDTO, etc) ✓ DONE           ║
║  ├── usuario.py    (UsuarioDTO, etc) ✓ DONE            ║
║  └── semestre.py   (SemestreDTO, etc) ✓ DONE           ║
║                                                        ║
║  ────────────────────────────────────────────────      ║
║  • Pure Python objects                                 ║
║  • NO database connection                              ║
║  • Type-safe (Pydantic)                                ║
║  • Validated (Pydantic)                                ║
║  • Easy to serialize (JSON)                            ║
║  • COMPLETELY SAFE to return to pages                  ║
╚═════════════════════╤══════════════════════════════════╝
                      │
                      ↓
                   DATABASE
```

## 3. Data Flow for a Room Request

```
User clicks "Show Rooms" button in Streamlit Page
    │
    ↓
Page calls: InventoryService.get_all_salas()
    │
    ↓
Service calls: SalaRepository.get_all_with_eager_load()
    │
    ↓
Repository opens DatabaseSession:
    │
    ├─ Queries: session.query(SalaORM) \
    │           .options(joinedload(...)) \  ← eager loading
    │           .all()
    │
    ├─ Gets list of ORM objects
    │
    ├─ For each ORM object, calls orm_to_dto():
    │  ├─ Accesses orm_obj.predio.nome        ← safe, session still open
    │  ├─ Accesses orm_obj.tipo_sala.nome     ← safe
    │  ├─ Accesses orm_obj.caracteristicas   ← safe
    │  └─ Returns SalaDTO (pure Python)       ← no DB connection
    │
    └─ Returns List[SalaDTO]

    ↓
Session closes (DTOs are already created, safe!)
    │
    ↓
Repository returns: [SalaDTO, SalaDTO, SalaDTO, ...]
    │
    ↓
Service returns: [SalaDTO, SalaDTO, SalaDTO, ...]
    │
    ↓
Page receives: [SalaDTO, SalaDTO, SalaDTO, ...]
    │
    ↓
Page displays:
    for room in rooms:           # room is DTO, not ORM
        st.write(room.nome)      # ✓ works
        st.write(room.predio.nome)  # ✓ works (nested DTO)

✅ NO ERRORS! NO DETACHED OBJECTS!
```

## 4. Comparison: Before vs After

```
BEFORE (Broken Pattern):
┌────────────────────┐
│Service Method:     │
│                    │
│def get_all_salas():│
│  session =         │
│    create()        │
│  salas = session   │
│    .query(Sala)    │
│    .all()          │
│  return salas  ← ORM OBJECTS
│                    │
└────────────────────┘
         │
         ↓ returns ORM
┌────────────────────┐
│Page receives ORM   │
│salas                │
│         │          │
│         ↓          │
│session.close()     │
│(external code)     │
│         │          │
│         ↓          │
│for sala in salas:  │
│  access            │
│  sala.predio       │
│    .nome           │
│         │          │
│         ↓          │
│❌ CRASH!          │
│DetachedInstance    │
└────────────────────┘


AFTER (Fixed Pattern):
┌────────────────────┐
│Repository Method:  │
│                    │
│def get_all():      │
│  with              │
│   DatabaseSession()│
│   as session:      │
│    salas_orm =     │
│      session       │
│        .query()    │
│        .all()      │
│    return [        │
│      orm_to_dto(s) │
│      for s         │
│      in salas_orm  │
│    ]           ← DTOs
│                    │
│  ← session closes  │
└────────────────────┘
         │
         ↓ returns DTO
┌────────────────────┐
│Page receives DTO   │
│rooms (Pydantic)    │
│         │          │
│         ↓          │
│for room in rooms:  │
│  access            │
│  room.predio       │
│    .nome           │
│         │          │
│         ↓          │
│✅ WORKS!          │
│No DB connection!   │
└────────────────────┘
```

## 5. Repository Pattern - The Key Conversion

```
┌─────────────────────────────────────────┐
│ INSIDE REPOSITORY (Session Open)        │
│                                         │
│ orm_obj = ORM Model Instance            │
│ └─ Has lazy-loaded relationships        │
│ └─ Tied to SQLAlchemy session           │
│ └─ Can't access relationships outside   │
│                                         │
│ # Convert WHILE SESSION IS OPEN         │
│ predio_name = orm_obj.predio.nome ✓    │
│ tipo_sala_name = orm_obj.tipo_sala ✓   │
│ characteristics = [...]                │
│                                         │
│ # Create DTO (Pure Python)              │
│ dto = SalaDTO(                          │
│   id=orm_obj.id,                        │
│   nome=orm_obj.nome,                    │
│   predio_nome=predio_name,              │
│   ...                                   │
│ )                                       │
│                                         │
│ return dto  ← DTO (Safe!)              │
│                                         │
└─────────────────────────────────────────┘
            │
    Session closes
            │
            ↓
┌─────────────────────────────────────────┐
│ OUTSIDE REPOSITORY (Session Closed)     │
│                                         │
│ dto = SalaDTO (Pydantic Model)          │
│ └─ Pure Python object                   │
│ └─ No database connection               │
│ └─ Safe to use anywhere                 │
│ └─ Can pass to page, store, etc         │
│                                         │
│ # Can access nested data                │
│ dto.predio_nome  ✓ (was converted)     │
│ dto.tipo_sala    ✓ (was converted)     │
│                                         │
│ # CANNOT do lazy loading                │
│ dto.predio.extra_field  ✗ (not set)    │
│ └─ This is intentional!                 │
│ └─ Prevents lazy loading errors         │
│                                         │
└─────────────────────────────────────────┘
```

## 6. All Repositories Overview

```
BaseRepository[T, D]
│
├─ SalaRepository
│  ├─ orm_to_dto(SalaORM) → SalaDTO
│  ├─ dto_to_orm_create(SalaCreateDTO) → dict
│  ├─ get_all_with_eager_load() → List[SalaDTO]
│  ├─ get_by_campus(id) → List[SalaDTO]
│  ├─ get_by_predio(id) → List[SalaDTO]
│  ├─ search_by_name(name) → List[SalaDTO]
│  └─ get_simplified() → List[SalaSimplifiedDTO]
│
├─ AlocacaoRepository
│  ├─ orm_to_dto(AlocacaoORM) → AlocacaoDTO
│  ├─ get_all_with_eager_load() → List[AlocacaoDTO]
│  ├─ get_by_sala(id) → List[AlocacaoDTO]
│  ├─ get_by_demanda(id) → List[AlocacaoDTO]
│  └─ check_conflict() → bool
│
├─ UsuarioRepository
│  ├─ orm_to_dto(UsuarioORM) → UsuarioDTO
│  ├─ get_by_username(user) → UsuarioDTO
│  ├─ get_by_role(role) → List[UsuarioDTO]
│  └─ search_by_nome(name) → List[UsuarioDTO]
│
├─ SemestreRepository
│  ├─ orm_to_dto(SemestreORM) → SemestreDTO
│  ├─ get_all_with_counts() → List[SemestreDTO]
│  ├─ get_by_status(status) → List[SemestreDTO]
│  └─ get_by_nome(name) → SemestreDTO
│
└─ DemandaRepository
   ├─ orm_to_dto(DemandaORM) → DemandaDTO
   ├─ get_by_semestre(id) → List[DemandaDTO]
   └─ get_by_codigo(code) → List[DemandaDTO]

All inherit:
• create(CreateDTO) → DTO
• get_by_id(id) → Optional[DTO]
• get_all() → List[DTO]
• update(id, UpdateDTO) → DTO
• delete(id) → bool
• count() → int
• exists(id) → bool
```

## 7. DTO Hierarchy Example (Sala)

```
SalaDTO (Complete Data)
├─ id: int
├─ nome: str
├─ capacidade: int
├─ andar: str
├─ predio: PredioDTO  ← nested DTO
│  ├─ id: int
│  ├─ nome: str
│  └─ campus: CampusDTO  ← doubly nested
│     ├─ id: int
│     └─ nome: str
├─ tipo_sala: TipoSalaDTO  ← nested DTO
│  ├─ id: int
│  └─ nome: str
└─ caracteristicas: List[CaracteristicaDTO]  ← list of DTOs
   ├─ id: int
   └─ nome: str

SalaSimplifiedDTO (For Dropdowns)
├─ id: int
├─ nome: str
├─ capacidade: int
├─ predio_nome: str (flattened)
└─ tipo_sala_nome: str (flattened)

SalaDetailDTO (Enhanced)
├─ all from SalaDTO
├─ created_at: datetime
├─ updated_at: datetime
└─ status: str
```

---

This architecture guarantees:
- ✅ No DetachedInstance errors
- ✅ No "not bound to session" errors
- ✅ No lazy loading failures
- ✅ Type safety throughout
- ✅ Easy to test
- ✅ Easy to maintain
- ✅ Fast performance
