# Copilot Instructions - Sistema de Ensalamento FUP/UnB

**Project:** Room allocation management system for Faculdade UnB Planaltina
**Tech Stack:** Python + Streamlit + SQLAlchemy + SQLite3
**Architecture:** Modular Monolith (single Python process, repository pattern)

## Quick Architecture Overview

### Big Picture
- **Frontend + Backend:** Multipage Streamlit app (no separate API layer)
- **Database:** SQLite3 file-based (`data/ensalamento.db`), accessed via SQLAlchemy ORM
- **Authentication:** `streamlit-authenticator` with YAML config (`.streamlit/secrets.yaml`)
- **Key Constraint:** System uses SIGAA time blocks (atomic scheduling units: M1, M2, T1, etc.) to prevent conflicts

### Three-Layer Structure

```
pages/                    # Streamlit multi-page app (auto-routed from folder)
  1_🏠_Home.py            # Admin dashboard
  2_🏢_Inventário.py      # Room CRUD
  3_👨‍🏫_Professores.py     # Professor CRUD

src/
  repositories/           # Data access layer (Repository Pattern)
    base.py               # Generic CRUD, converts ORM ↔ DTO
    sala.py, professor.py, etc.

  models/                 # SQLAlchemy ORM entities
    base.py               # BaseModel (id, created_at, updated_at)
    academic.py           # Demanda, Disciplina
    allocation.py         # AlocacaoSemestral, ReservaEsporadica
    inventory.py          # Sala, Predio, Campus, TipoSala

  schemas/                # Pydantic DTO/validation models
    (mirrors models/ structure - separate ORM from API layer)

  services/               # Business logic & external integrations
    auth_service.py       # User management, password hashing (bcrypt)
    database_service.py   # High-level CRUD operations
    setup_service.py      # DB init & data seeding
    mock_api_service.py   # Simulates external "Sistema de Oferta" API

  config/
    database.py           # SQLAlchemy engine, session factory
    settings.py           # .env-based configuration
```

## Critical Developer Workflows

### Starting the App
```bash
cd /home/bgeneto/github/ensalamento-fup
streamlit run main.py
```
**First run:** Auto-initializes DB (creates schema), seeds initial data (time blocks, room types, campus, 142 professors from CSV), creates admin user. Check `.streamlit/secrets.yaml` for credentials.

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

### Authentication Flow (CRITICAL - Multi-Page Apps)

**✅ CORRECT Pattern (from Streamlit-Authenticator best practices):**

**Main page (main.py) - Initialize authenticator ONCE:**
```python
# 1. Setup authenticator
authenticator, config = setup_authenticator()

# 2. CRITICAL: Store in session state for all pages to access
st.session_state["authenticator"] = authenticator
st.session_state["config"] = config

# 3. Render login widget ONLY on main page with location="main"
authenticator.login(location="main", key="login-home")

# 4. Show logout in sidebar when authenticated
if st.session_state.get("authentication_status"):
    authenticator.logout(location="sidebar", key="logout-home")
```

**Other pages (pages/*.py) - Retrieve and maintain session:**
```python
# 1. Check authentication status first
if st.session_state.get("authentication_status"):
    # 2. Retrieve authenticator from session state
    authenticator = st.session_state.get("authenticator")

    # 3. CRITICAL: Call .login(location="unrendered") with UNIQUE key
    # This maintains session WITHOUT rendering widget (fixes page refresh issue)
    authenticator.login(location="unrendered", key="authenticator-page-name")

    # 4. Show logout with UNIQUE key
    authenticator.logout(location="sidebar", key="logout-page-name")

    # Page content loads normally...
    st.set_page_config(page_title="Page Title")

elif st.session_state.get("authentication_status") is None or st.session_state == {}:
    st.warning("👈 Por favor, faça login na página inicial para acessar o sistema.")
    st.page_link("main.py", label="🏠 Voltar para Home", icon="🏠")
    st.stop()
else:
    st.error("❌ Acesso negado.")
    st.stop()
```

**Why this works:**
1. ✅ Authenticator stored in session state (persists across pages and refreshes)
2. ✅ `.login(location="unrendered")` validates session from cookies WITHOUT rendering widget
3. ✅ Unique keys prevent widget ID collisions between pages
4. ✅ On page refresh (F5), session state is restored and auth persists

**❌ MISTAKES TO AVOID:**

| ❌ Wrong | ✅ Correct | Why |
|---------|-----------|-----|
| Re-initialize authenticator on every page | Store once in session state on main page | Multiple authenticators break session persistence |
| Use `location="sidebar"` in `.login()` | Use `location="main"` on main page, `location="unrendered"` on other pages | Invalid locations cause "Location must be one of..." error |
| Don't store authenticator in session state | Always store: `st.session_state["authenticator"] = authenticator` | Pages can't access authenticator if not in session state |
| Use same keys on all pages (e.g., key="logout") | Use unique keys per page (e.g., key="logout-page-name") | Duplicate keys cause widget ID collisions |
| Call `.login()` on every page with location="main" | Only call with location="main" on main.py | Multiple login widgets will confuse the app |
| Try to re-authenticate by re-creating authenticator | Retrieve from session state | Session state from cookies is lost if recreated |

**Reference:** [Implementing Streamlit-Authenticator Across Multi-Page Apps](https://towardsdatascience.com/implementing-streamlit-authenticator-across-multi-page-apps-5ad70ac315b3/)

See also: `MULTIPAGE_AUTH_FIX.md`, `SESSION_STATE_PERSISTENCE_SUMMARY.md`, `AUTHENTICATION_MISTAKES_TO_AVOID.md`

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
- ✅ Prefer `src.utils.ui_feedback` helpers (`set_session_feedback`, `display_session_feedback`) for DRY toast + TTL handling across pages

**Real Example:** See `pages/3_👨‍🏫_Professores.py` CSV import section for working implementation.

### Toast-Based Feedback Helper (Reusable)

- Call `set_session_feedback("state_key", success_bool, "Message", ttl=6, **kwargs)` before `st.rerun()` inside the action handler.
- After rerun, invoke `display_session_feedback("state_key", success_icon="✅", error_icon="❌")` near the top of the render branch to emit the toast; the helper returns the payload so you can present supplemental details (e.g., list of CSV errors) elsewhere when needed.
- Feedback entries auto-expire after the provided TTL and do not require manual clear buttons; to force removal, use `clear_session_feedback("state_key")`.

### File Organization Rules
- **Source code:** `src/` folder (tracked by Python path in main.py)
- **Tests:** `tests/` folder (test files match source structure: `test_repositories.py`, `test_models.py`)
- **Data:** `data/` folder (SQLite DB file, CSV exports)
- **Docs:** `docs/` folder (Markdown, never root)
- **Configuration:** `.streamlit/secrets.yaml` (auth), `.env` (secrets via `Settings` class)

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

## st.data_editor — Best practices to avoid infinite reruns and unique/primary key conflicts

When using Streamlit's `st.data_editor` in this project we must follow a strict pattern to avoid an issue that causes infinite reload loops when the user submits a row that fails server-side validation (for example: duplicate unique key such as `username_login` or composite uniqueness like `nome + predio_id`). The pattern below has been applied to `pages/3_👨‍🏫_Professores.py` and `pages/2_🏢_Inventário.py`.

Summary (short):
- Never call `st.rerun()` immediately after detecting a validation error for a user-provided row. Doing so re-renders the page while the invalid value still exists in the editor and retriggers the same validation error → infinite loop.
- Batch all DB operations for the single data-editor render pass: collect deletions, additions and updates, perform them, record which operations succeeded, and call `st.rerun()` only once if and only if at least one DB change actually persisted.
- Use `set_session_feedback()` to store user-visible messages (error or success) before rerunning. Use `display_session_feedback()` after rerun to show messages.

Contract (what each data-editor handler should guarantee):
- Inputs: `df` (original DataFrame), `edited_df` (returned by `st.data_editor`).
- Outputs: DB state consistent with successful rows; session feedback describing success/errors; optional single rerun to refresh persisted data.
- Error modes: validation errors (missing fields, duplicates), DB exceptions, FK constraint failures.
- Success criteria: no infinite rerun loop; user can correct invalid rows in-place; persisted changes shown after at most one rerun.

Step-by-step pattern to follow (copy into any page using `st.data_editor`):

1. Render the `st.data_editor` with `num_rows='dynamic'` and include an (internal) `ID` column to map rows back to DB records.

2. After receiving `edited_df`, compare lengths and IDs to categorize: deletions, additions (rows where `ID` is NaN or 0), or possible updates (rows with ID and changed values).

3. Execute in this order inside a single user action (no intermediate `st.rerun()` calls):
   - Deletions: compute `deleted_ids = original_ids - edited_ids`. Try to delete all `deleted_ids` inside one DB session (or a loop inside one session). If deletion succeeds, mark `changes_made = True`. If a deletion fails, record the error via `set_session_feedback(..., action='delete')` and set `errors_occurred = True` but do NOT call `st.rerun()`.

   - Additions: iterate new rows and validate locally first (required fields present, types, basic sanity). For each new row:
     - If validation fails, call `set_session_feedback(..., action='create')` and set `errors_occurred = True` and continue to next row (do NOT rerun).
     - Check for duplicates using repository helper methods (e.g., `get_by_username_login()` or a selective `get_all()` lookup). If duplicate, `set_session_feedback(..., action='create')` and mark `errors_occurred = True`; continue (do NOT rerun).
     - If valid, create the record via repository inside the batch session and increment `created_count` and set `changes_made = True`.

   - Updates: iterate existing rows with changed values and validate each change similarly:
     - Local validation first (required fields).
     - If changing unique keys (like username or composite keys), check repositories for existing records excluding the current record. If conflict, `set_session_feedback(..., action='update')` and set `errors_occurred = True`; do NOT rerun.
     - If valid, persist the update and set `changes_made = True`.

4. After processing all rows:
   - If `changes_made` is True: set a success `set_session_feedback(...)` summarizing how many records were created/updated/deleted and then call `st.rerun()` exactly once to reload data from the DB so the editor reflects persistent state.
   - If only `errors_occurred` is True (and `changes_made` is False): DO NOT call `st.rerun()`. The editor retains the invalid values so the user can correct them. `display_session_feedback()` will show the error messages from the previous cycle.

5. Always call `display_session_feedback()` near the top of the render branch so stored messages are shown after a rerun.

Checklist for PRs that add a `st.data_editor`:
- [ ] Include an internal `ID` column to map rows to DB records.
- [ ] Implement server-side validation for required fields and uniqueness checks before committing.
- [ ] Batch DB changes and only call `st.rerun()` after successful commits.
- [ ] Use `set_session_feedback()` for all user-facing errors and success messages; `display_session_feedback()` to render them after rerun.
- [ ] Add unit tests for repository uniqueness checks when practical.
- [ ] Manually test: add duplicate, edit to duplicate, delete rows — verify no infinite reloads and proper feedback.

Example pseudo-code snippet (core loop):

```python
# after rendering data_editor and building df / edited_df
changes_made = False
errors_occurred = False

# deletions
deleted_ids = original_ids - edited_ids
if deleted_ids:
    try:
        with get_db_session() as session:
            repo = MyRepo(session)
            for id in deleted_ids:
                repo.delete(id)
        changes_made = True
    except Exception as e:
        set_session_feedback('crud', False, f"Erro ao deletar: {e}")
        errors_occurred = True

# additions
for row in new_rows:
    if not valid(row):
        set_session_feedback('crud', False, 'Campos inválidos')
        errors_occurred = True
        continue
    if repo.exists(unique_key=row['key']):
        set_session_feedback('crud', False, 'Chave duplicada')
        errors_occurred = True
        continue
    repo.create(dto)
    changes_made = True

# updates (similar validation, check conflict excluding current id)

if changes_made:
    set_session_feedback('crud', True, 'Alterações salvas')
    st.rerun()
# else: show errors and allow user correction
```

Why this pattern is important
- Prevents the UI from repeatedly rerendering while the invalid value remains in the `data_editor` (the root cause of the infinite reload loop).
- Lets the user see and fix validation errors in-place.
- Keeps DB operations atomic per user action and minimizes UI churn by rerunning only when necessary.

Testing recommendations
- Add unit tests for repository-level uniqueness checks (`get_by_username_login`, composite-key checks) in `tests/`.
- Add a short manual QA checklist to your PR template reminding reviewers to try adding and editing duplicates in the page's `data_editor`.

If you'd like, I can also add a small helper in `src/utils/` (for example `data_editor_helpers.py`) that provides a reusable wrapper implementing this pattern so pages only call a small helper function with repository callbacks. I can prepare that as a follow-up change.

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
