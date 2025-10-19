# Copilot Instructions - Sistema de Ensalamento FUP/UnB

**Project:** Room allocation management system for UnB Planaltina
**Tech Stack:** Python + Streamlit + SQLAlchemy + SQLite3
**Architecture:** Modular Monolith (single Python process, repository pattern)

## Quick Architecture Overview

### Big Picture
- **Frontend + Backend:** Single Streamlit app (no separate API layer)
- **Database:** SQLite3 file-based (`data/ensalamento.db`), accessed via SQLAlchemy ORM
- **Authentication:** `streamlit-authenticator` with YAML config (`.streamlit/config.yaml`)
- **Key Constraint:** System uses SIGAA time blocks (atomic scheduling units: M1, M2, T1, etc.) to prevent conflicts

### Three-Layer Structure

```
pages/                     # Streamlit multi-page app (auto-routed from folder)
  1_🏠_Home.py            # Admin dashboard
  2_🏢_Inventário.py      # Room CRUD
  3_👨‍🏫_Professores.py   # Professor CRUD

src/
  repositories/           # Data access layer (Repository Pattern)
    base.py              # Generic CRUD, converts ORM ↔ DTO
    sala.py, professor.py, etc.

  models/                 # SQLAlchemy ORM entities
    base.py              # BaseModel (id, created_at, updated_at)
    academic.py          # Demanda, Disciplina
    allocation.py        # AlocacaoSemestral, ReservaEsporadica
    inventory.py         # Sala, Predio, Campus, TipoSala

  schemas/                # Pydantic DTO/validation models
    (mirrors models/ structure - separate ORM from API layer)

  services/               # Business logic & external integrations
    auth_service.py      # User management, password hashing (bcrypt)
    database_service.py  # High-level CRUD operations
    setup_service.py     # DB init & data seeding
    mock_api_service.py  # Simulates external "Sistema de Oferta" API

  config/
    database.py          # SQLAlchemy engine, session factory
    settings.py          # .env-based configuration
```

## Critical Developer Workflows

### Starting the App
```bash
cd /home/bgeneto/github/ensalamento-fup
streamlit run main.py
```
**First run:** Auto-initializes DB (creates schema), seeds initial data (time blocks, room types, campus, 142 professors from CSV), creates admin user. Check `.streamlit/config.yaml` for credentials.

### Database Initialization & Seeding
```bash
python init_db.py --init        # Create tables only
python init_db.py --seed        # Seed with initial data (includes 142 professors from docs/professores-fup.csv)
python init_db.py --all         # Full reset: drop, create tables, and seed
```

**Seeding includes:**
- 7 days of week (SIGAA standard: MON-SAT)
- 15 time blocks (M1-M5, T1-T6, N1-N4 - SIGAA atomic scheduling units)
- 5 room types (Sala de Aula, Laboratório, Auditório, etc.)
- 8 room characteristics (Projetor, Quadro, Acesso Cadeirantes, etc.)
- 23 real classrooms (A1-09/9, AT-22/7, etc. from FUP/UnB inventory)
- 142 professors loaded from `docs/professores-fup.csv` (username_login + nome_completo)

### Running Tests
```bash
python run_tests.py        # Runs all tests with coverage
pytest tests/ -v --tb=short
```
All tests must go in `tests/` folder. Test dependencies: `pytest`, `pytest-cov`, `pytest-asyncio`.

### Data Flow During Allocation
1. **Admin imports demands** → MockApiService generates fake course data (or integrates Sistema de Oferta)
2. **Data stored** → `Demanda` model (course, professors, preferred room type, schedule blocks)
3. **Allocation engine** → Matches demands to `Sala` based on time blocks + constraints
4. **Results saved** → `AlocacaoSemestral` records created
5. **Conflicts resolved** → Time blocks ensure atomic scheduling (no double-booking)

## Project-Specific Patterns & Conventions

### DTO ↔ ORM Pattern (Repository Pattern)
All repositories convert between SQLAlchemy ORM and Pydantic DTOs:

```python
# In BaseRepository
def orm_to_dto(self, orm_obj: T) -> D:
    """Convert ORM model to DTO - subclasses implement this"""
    raise NotImplementedError()

# Example: SalaRepository
def orm_to_dto(self, sala: Sala) -> SalaDTO:
    return SalaDTO(
        id=sala.id,
        nome=sala.nome,
        capacidade=sala.capacidade,
        # Map relationships...
    )

def dto_to_orm_create(self, dto: SalaDTO) -> Sala:
    return Sala(
        nome=dto.nome,
        capacidade=dto.capacidade,
    )
```

### Authentication Flow
- `streamlit-authenticator` handles login UI
- Credentials stored in `.streamlit/config.yaml` (pre-hashed with `stauth.Hasher.hash_passwords()`)
- Session state: `st.session_state.authentication_status`, `st.session_state.name`, `st.session_state.username`
- Use decorators: `@require_auth()`, `@require_admin()` from `auth_service.py`

### Database Initialization (One-Time)
`SetupService` seeds:
- 7 days of week (DiaSemana) — must be exactly 7
- 18 SIGAA time blocks (HorarioBloco: M1-M6, T1-T6, N1-N6)
- 5+ room types (TipoSala)
- 10+ room characteristics (Caracteristica)
- At least 1 Campus, Predio, Semestre, Usuario (admin)

**Status tracked** in `src/services/setup_service.py:get_setup_status()` — returns completion % for UI.

### Streamlit Multipage Pattern
Pages in `pages/` folder auto-appear in sidebar with emoji prefix:
- Emoji + underscore + number + underscore + name (e.g., `1_🏠_Home.py`)
- Each page checks auth at top: `if not st.session_state.get("authentication_status"): st.error(...); st.stop()`
- Services injected via imports (not DI container)

### ⚠️ CRITICAL: Streamlit Messages & st.rerun() Pattern
**Problem:** When using `st.rerun()` to refresh the page, all messages (`st.success()`, `st.error()`, `st.warning()`) displayed in the same render cycle disappear before users can read them.

**Wrong Pattern (Messages Flash & Disappear):**
```python
if st.button("Import"):
    result = do_import()
    st.success("✅ Import complete!")  # ❌ Disappears on rerun
    st.rerun()
```

**Correct Pattern (Persistent Messages):**
```python
if st.button("Import"):
    result = do_import()
    # Store result in session state BEFORE rerun
    st.session_state.import_result = {
        "success": True,
        "message": "✅ Import complete!",
        "count": len(result),
        "errors": [],
    }
    st.rerun()

# Display persisted message AFTER rerun completes
if "import_result" in st.session_state:
    result = st.session_state.import_result
    if result["success"]:
        st.success(f"{result['message']} ({result['count']} items)")
        if result.get("errors"):
            st.warning(f"⚠️ {len(result['errors'])} errors:")
            for error in result["errors"][:5]:
                st.write(f"  • {error}")
    else:
        st.error(result["message"])

    # Optional: Clear button to dismiss after user reads
    if st.button("🔄 Clear", key="clear_result"):
        del st.session_state.import_result
        st.rerun()
```

**Key Points:**
- ✅ Store message data in `st.session_state` BEFORE calling `st.rerun()`
- ✅ Display persisted messages AFTER rerun (outside the button/form scope)
- ✅ Include clear button so users can dismiss when done reading
- ✅ Always use unique keys for session state variables to avoid conflicts
- ✅ Use this pattern for: imports, form submissions, bulk operations, confirmations

**Real Example:** See `pages/3_👨‍🏫_Professores.py` CSV import section for working implementation.

### File Organization Rules
- **Source code:** `src/` folder (tracked by Python path in main.py)
- **Tests:** `tests/` folder (test files match source structure: `test_repositories.py`, `test_models.py`)
- **Data:** `data/` folder (SQLite DB file, CSV exports)
- **Docs:** `docs/` folder (Markdown, never root)
- **Configuration:** `.streamlit/config.yaml` (auth), `.env` (secrets via `Settings` class)

## Integration Points & External Dependencies

### External APIs (Mocked for Dev)
- **Sistema de Oferta:** Course/demand data. Mocked in `MockApiService`. Real integration via REST API (URL/key in `.env`)
- **Brevo Email:** Notifications. Configured in `.env` (`BREVO_API_KEY`, `BREVO_FROM_EMAIL`)

### Dependency Injection Pattern (Session-Based)
```python
# Repositories require SQLAlchemy session
with get_db_session() as session:
    sala_repo = SalaRepository(session)
    salas = sala_repo.get_all()  # Returns list of DTOs
```

### Datetime Handling
- All models use `datetime.utcnow` (UTC, not local time)
- SIGAA schedule parsing: Map SIGAA time block codes to `HorarioBloco` DB records

## Key Files to Reference

| File | Purpose |
|------|---------|
| `main.py` | Streamlit entry point, auth setup, page config |
| `src/config/database.py` | SQLAlchemy engine, `get_db_session()` factory |
| `src/models/base.py` | BaseModel ORM template (id, created_at, updated_at) |
| `src/repositories/base.py` | Generic CRUD + ORM↔DTO conversion |
| `src/services/setup_service.py` | DB init workflow + data seeding |
| `src/services/auth_service.py` | Auth decorators, password hashing |
| `docs/SRS.md` | **MASTER requirements** (read first for ambiguity) |
| `docs/ARCHITECTURE.md` | Tech decisions rationale |

## Common Tasks

### Add a New Page
1. Create `pages/N_🏷️_PageName.py` (increment N, add emoji)
2. Add auth check at top: `if not st.session_state.get("authentication_status"): st.error(...); st.stop()`
3. Import repos: `from src.repositories.x import XRepository`
4. Get session: `with get_db_session() as session: repo = XRepository(session); ...`

### Add a New Entity
1. Create ORM model in `src/models/` (inherit from `BaseModel`)
2. Create Pydantic schema in `src/schemas/` (DTO)
3. Create repository in `src/repositories/` (implement `orm_to_dto()`, `dto_to_orm_create()`)
4. Update `src/config/database.py` to import the model
5. Add seeding logic in `SetupService` if needed
6. Write tests in `tests/test_repositories.py`

### Debug Database State
```python
from src.config.database import get_db_session
from src.models.inventory import Sala

with get_db_session() as session:
    salas = session.query(Sala).all()
    for sala in salas:
        print(f"{sala.nome}: {sala.capacidade} seats")
```

## Testing Requirements
- All new code needs unit tests in `tests/`
- Use `pytest` fixtures from `tests/conftest.py` (session, engine, sample data)
- Coverage target: 80%+
- Run: `python run_tests.py`

## Shell Tools (from CLAUDE.md)
When in terminal, use MODERN tools (NOT `grep`, `find`, etc.):
- **Find files:** `fd -e py` (not `find`)
- **Search text:** `rg "pattern" --type py` (not `grep`)
- **Code structure:** `ast-grep --pattern 'const [$STATE, $SETTER] = useState($INIT)'`
- **Interactive selection:** Pipe results to `fzf`
- **JSON:** `jq '.field'`
- **YAML:** `yq '.field'`

---

**Last Updated:** Phase 3 M2
**See Also:** `QUICK_START.md` (features status), `CLAUDE.md` (AI development context)
