# Implementation Roadmap & Task Breakdown

## Quick Reference: 12 Development Phases

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SISTEMA DE ENSALAMENTO FUP/UnB - DEVELOPMENT ROADMAP                  │
└─────────────────────────────────────────────────────────────────────────┘

Phase  Duration   Focus Area                      Dependencies    Status
─────────────────────────────────────────────────────────────────────────
  1    1-2 wks   Foundation & Setup              -              📋
  2    1 wk      Authentication & Users          Phase 1        📋
  3    1-2 wks   Inventory Management            Phase 1-2      📋
  4    1 wk      Professor Management            Phase 1-3      📋
  5    1 wk      Semester & Demand               Phase 1-2      📋
  6    1 wk      Allocation Rules                Phase 1-2      📋
  7    2-3 wks   Allocation Engine               Phase 4-6      📋
  8    1 wk      Manual Adjustment               Phase 7        📋
  9    1-2 wks   Ad-hoc Reservations             Phase 2-3      📋
 10    1-2 wks   Visualization & Reports         Phase 7-9      📋
 11    1 wk      Testing & Documentation         All phases     📋
 12    1 wk      Deployment & Polish             All phases     📋
─────────────────────────────────────────────────────────────────────────
       18 weeks  TOTAL PROJECT DURATION
```

---

## Phase-by-Phase Task Breakdown

### PHASE 1: Foundation & Setup (1-2 weeks)

**Objective:** Set up project structure, database, configuration, and base models

**Tasks:**
- [ ] Create directory structure (src/, pages/, tests/, etc.)
- [ ] Set up `.env` and `.env.example` files
- [ ] Create `settings.py` configuration management
- [ ] Implement database session manager (`DatabaseSession` context manager)
- [ ] Create SQLite database file (`data/ensalamento.db`)
- [ ] Run database migrations (create all tables from schema.sql)
- [ ] Seed database with initial data:
  - [ ] 6 days of week (dias_semana: 2-7 = MON-SAT)
  - [ ] 15 time blocks (horarios_bloco: M1-M5, T1-T6, N1-N4)
  - [ ] Sample campus/building/room data (optional for testing)
- [ ] Create base ORM model (`BaseModel` with id, created_at, updated_at)
- [ ] Create base DTO schema (`BaseSchema`)
- [ ] Implement all ORM models (12 tables)
- [ ] Implement all DTO schemas (Pydantic)
- [ ] Set up `BaseRepository[T, D]` generic template
- [ ] Create Dockerfile and docker-compose.yaml
- [ ] Test database connection locally

**Deliverables:**
- ✅ Complete project structure
- ✅ Functional SQLite database
- ✅ All ORM models & DTO schemas
- ✅ Docker setup ready to build
- ✅ Base repository template

**Tests:**
- [ ] `pytest tests/test_models.py` (model creation, relationships)
- [ ] `pytest tests/test_schemas.py` (DTO validation)
- [ ] Manual database verification (list tables, count rows)

---

### PHASE 2: Authentication & User Management (1 week)

**Objective:** Implement user authentication and role-based access control

**Tasks:**
- [ ] Create `usuarios` table with roles support
- [ ] Implement `UsuarioRepository` (CRUD operations)
- [ ] Implement `AuthService` with password hashing (bcrypt)
- [ ] Create `auth_config.yaml` template for streamlit-authenticator
- [ ] Implement `authenticate()` helper function (check session state)
- [ ] Create Login page (`src/main.py` or dedicated login.py)
- [ ] Create User Management page (`pages/11_👥_Usuários.py`) - Admin only
- [ ] Implement Logout functionality
- [ ] Implement Password Reset functionality
- [ ] Test authentication flow end-to-end

**Deliverables:**
- ✅ User authentication working
- ✅ Role-based access control
- ✅ Admin user management interface
- ✅ Session state management

**Tests:**
- [ ] `pytest tests/test_services.py::test_auth_*`
- [ ] Manual: Login → Logout → Password Reset
- [ ] Manual: Admin creates user → User logs in

---

### PHASE 3: Inventory Management (1-2 weeks)

**Objective:** Implement CRUD for physical spaces (campuses, buildings, rooms, types, characteristics)

**Tasks:**
- [ ] Implement `CampusRepository` + `SalaRepository` + related repos
- [ ] Implement `InventoryService` (CRUD operations for all entities)
- [ ] Create Campus Management page (admin)
- [ ] Create Building Management page (admin)
- [ ] Create Room Type Management page (admin) - with safety checks
- [ ] Create Room Characteristics Management page (admin)
- [ ] Create Room Management page (admin) with:
  - [ ] Multi-select characteristics
  - [ ] st.data_editor with hide_index=True
  - [ ] Dynamic row addition/deletion
- [ ] Implement validation:
  - [ ] Prevent duplicate names (unique constraints)
  - [ ] Prevent deletion of room types if rooms exist
  - [ ] Capacity validation (>0)
- [ ] Create Admin Dashboard page (overview of inventory)

**Deliverables:**
- ✅ Complete inventory management system
- ✅ Admin pages for all entities
- ✅ Data validation & error handling
- ✅ Dynamic data editor tables

**Tests:**
- [ ] `pytest tests/test_repositories.py` (CRUD operations)
- [ ] `pytest tests/test_services.py::test_inventory_*`
- [ ] Manual: Admin creates campus → building → room with characteristics

---

### PHASE 4: Professor Management (1 week)

**Objective:** Manage professors and their soft preferences (rooms, characteristics)

**Tasks:**
- [ ] Create `Professor` ORM model with hard restriction (low_mobility)
- [ ] Create professor preference mapping tables:
  - [ ] `professor_prefere_sala` (N:N)
  - [ ] `professor_prefere_caracteristica` (N:N)
- [ ] Implement `ProfessorRepository` (with preference loading)
- [ ] Implement `ProfessorService` (CRUD + preference management)
- [ ] Create Professor Management page (admin) with:
  - [ ] CRUD for professors
  - [ ] Link professor to username (optional)
  - [ ] Manage soft preferences (preferred rooms/characteristics)
- [ ] Create "Minhas Preferências" page (self-service for logged-in professors)
- [ ] Implement validation:
  - [ ] Require name_completo to match API format
  - [ ] Validate username linkage (must exist in usuarios)
  - [ ] Safety checks when deleting professors with allocations

**Deliverables:**
- ✅ Professor management system
- ✅ Soft preference management (admin)
- ✅ Self-service preference page (professor)
- ✅ Database constraints & validation

**Tests:**
- [ ] `pytest tests/test_services.py::test_professor_*`
- [ ] Manual: Admin creates professor → Link to user → User updates preferences

---

### PHASE 5: Semester & Demand Management (1 week)

**Objective:** Import semester data from external API and manage allocations

**Tasks:**
- [ ] Implement `SemestreRepository` + `DemandaRepository`
- [ ] Implement `ApiService` (call Sistema de Oferta API)
- [ ] Implement `SemesterService` with:
  - [ ] Semester CRUD
  - [ ] API synchronization logic
  - [ ] Data validation & error handling
  - [ ] Mark non-room disciplines as "Não Alocar"
- [ ] Create Semester Management page (admin) with:
  - [ ] List semesters
  - [ ] Create new semester
  - [ ] Sync with API (big button)
  - [ ] View imported demands (table)
- [ ] Error handling for:
  - [ ] API unreachable
  - [ ] Invalid API response format
  - [ ] Duplicate imports
- [ ] Test with mock API data

**Deliverables:**
- ✅ Semester management system
- ✅ API integration with error handling
- ✅ Demand import and validation
- ✅ Admin page for semester operations

**Tests:**
- [ ] `pytest tests/test_services.py::test_semester_*` (with mocked API)
- [ ] Manual: Admin syncs semester → Verify data imported
- [ ] Test API error scenarios (timeout, invalid JSON)

---

### PHASE 6: Allocation Rules (1 week)

**Objective:** Define and manage allocation rules (hard & soft)

**Tasks:**
- [ ] Create `Regra` ORM model with JSON config field
- [ ] Implement `RegraRepository`
- [ ] Define rule types:
  - [ ] DISCIPLINA_TIPO_SALA (hard: discipline → room type)
  - [ ] DISCIPLINA_SALA (hard: discipline → specific room)
  - [ ] DISCIPLINA_REQUER_CARACTERISTICA (soft: prefer rooms with characteristic)
  - [ ] PROFESSOR_PREFERE_SALA (soft: via professor preferences)
  - [ ] PROFESSOR_PREFERE_CARACTERISTICA (soft: via professor preferences)
- [ ] Implement `AllocationService.validate_rules()` for conflict detection
- [ ] Create Allocation Rules page (admin) with:
  - [ ] Create rule (dropdown for rule type)
  - [ ] Edit rule
  - [ ] Delete rule (with safety checks)
  - [ ] View active rules in table

**Deliverables:**
- ✅ Rule storage and management
- ✅ Rule type definitions
- ✅ Conflict detection for hard rules
- ✅ Admin rule management interface

**Tests:**
- [ ] `pytest tests/test_services.py::test_rules_*`
- [ ] Manual: Create conflicting hard rules → Detect conflict

---

### PHASE 7: Allocation Engine (2-3 weeks) ⭐ CRITICAL

**Objective:** Implement the core allocation algorithm

**Tasks:**

**Sub-phase 7A: Sigaa Schedule Parser (1 week)**
- [ ] Implement `SigaaParser` class in `src/utils/sigaa_parser.py`
- [ ] Parse time block codes: "24M12 6T34" → list of (day, block)
- [ ] Validate time blocks against database
- [ ] Handle edge cases (invalid codes, partial blocks)
- [ ] Comprehensive unit tests

**Sub-phase 7B: Conflict Detection (1 week)**
- [ ] Implement `ConflictDetector` class in `src/utils/conflict_detector.py`
- [ ] Check overlaps:
  - [ ] Room + Time block overlaps
  - [ ] Professor + Time block overlaps
  - [ ] Hard rule conflicts
- [ ] Return detailed conflict information (for error messages)
- [ ] Unit tests for all conflict types

**Sub-phase 7C: Allocation Algorithm (1 week)**
- [ ] Implement `AllocationService.execute_allocation()` with:
  - [ ] Parse all demands (horario_sigaa_bruto)
  - [ ] Match professors to names
  - [ ] Phase 1: Allocate hard rules (priority-sorted)
  - [ ] Phase 2: Allocate remaining (scoring algorithm)
  - [ ] Persist results to `alocacoes_semestrais`
  - [ ] Return allocation report (successes, conflicts, warnings)
- [ ] Scoring algorithm:
  - [ ] +10 points: Matches hard rule
  - [ ] +5 points: Has preferred characteristic
  - [ ] +3 points: Capacity sufficient
  - [ ] +2 points: Professor preferred room
  - [ ] Tiebreaker: room ID (ascending)
- [ ] Error handling:
  - [ ] Hard rule conflicts → Stop & report
  - [ ] No room available → Warn & skip
  - [ ] Professor not found → Warn & continue

**Sub-phase 7D: Allocation Execution Page (1 week)**
- [ ] Create "Execução de Alocação" page (admin)
- [ ] Steps:
  - [ ] Select semester
  - [ ] Preview demands to be allocated
  - [ ] Big "Executar Alocação" button
  - [ ] Progress bar / status updates
  - [ ] Result summary (X allocated, Y conflicts, Z warnings)
  - [ ] View detailed allocation results (table)

**Deliverables:**
- ✅ Sigaa schedule parser (fully tested)
- ✅ Conflict detection (fully tested)
- ✅ Allocation algorithm (core logic)
- ✅ Allocation execution page

**Tests:**
- [ ] `pytest tests/test_sigaa_parser.py` (60+ test cases)
- [ ] `pytest tests/test_allocation_engine.py` (100+ test cases)
  - [ ] Hard rule allocation
  - [ ] Soft rule scoring
  - [ ] Conflict detection
  - [ ] Edge cases (no rooms available, all constraints, etc.)
- [ ] Manual: Execute allocation → Verify results in database

---

### PHASE 8: Manual Adjustment (1 week)

**Objective:** Allow manual fine-tuning of allocations

**Tasks:**
- [ ] Implement `AllocationService.swap_allocation()` for room swaps
- [ ] Implement `AllocationService.validate_allocation()` for validation
- [ ] Create "Ajustar Ensalamento" page (admin) with:
  - [ ] View current allocations (table with search/filter)
  - [ ] Select allocation to move
  - [ ] Choose new room
  - [ ] Real-time conflict validation
  - [ ] Confirm & save swap
- [ ] Validation checks:
  - [ ] New room available at time block
  - [ ] No conflicts with other allocations
  - [ ] No conflicts with ad-hoc reservations (Phase 9)
  - [ ] Rule violation alerts (don't block, just warn)
- [ ] Undo capability (keep allocation history?)

**Deliverables:**
- ✅ Manual allocation adjustment functionality
- ✅ Real-time validation
- ✅ Admin adjustment page

**Tests:**
- [ ] `pytest tests/test_services.py::test_adjust_*`
- [ ] Manual: Swap allocation → Verify no conflicts

---

### PHASE 9: Ad-hoc Reservations (1-2 weeks)

**Objective:** Enable users to reserve rooms for occasional use

**Tasks:**
- [ ] Create `ReservaEsporadica` ORM model
- [ ] Implement `ReservaRepository`
- [ ] Implement `ReservationService` with:
  - [ ] CRUD operations
  - [ ] Conflict detection (vs. allocations + other reservations)
  - [ ] User authorization (can only manage own reservations, except admin)
  - [ ] Cancellation logic
- [ ] Create "Minhas Reservas" page (logged-in users) with:
  - [ ] List user's own reservations
  - [ ] Create new reservation (date, time, room, description)
  - [ ] Edit reservation (if not started yet)
  - [ ] Cancel reservation
  - [ ] View all available rooms (calendar)
- [ ] Create admin reservation management (optional)
- [ ] Validation:
  - [ ] Room available at requested time
  - [ ] No conflicts with allocations
  - [ ] No conflicts with other reservations
  - [ ] User can only manage own reservations

**Deliverables:**
- ✅ Ad-hoc reservation system
- ✅ Conflict checking with allocations
- ✅ User-facing reservation page
- ✅ Cancellation & editing

**Tests:**
- [ ] `pytest tests/test_services.py::test_reservation_*`
- [ ] Manual: Create reservation → View in calendar → Cancel

---

### PHASE 10: Visualization & Reports (1-2 weeks)

**Objective:** Unified calendar view and report generation

**Tasks:**

**Sub-phase 10A: Unified Calendar (1 week)**
- [ ] Create visualization combining:
  - [ ] `alocacoes_semestrais` (semester-wide)
  - [ ] `reservas_esporadicas` (ad-hoc bookings)
- [ ] Features:
  - [ ] Grid/calendar view (rooms × time blocks)
  - [ ] Consolidate adjacent blocks (M1+M2 → 08:00-09:50)
  - [ ] Show discipline name, professor, vagas
  - [ ] Click for details
  - [ ] Filter by room / professor / course
  - [ ] Week view / Month view
- [ ] Create "Calendario" page (public, no login required)
- [ ] Create Allocation Search page (public, searchable)

**Sub-phase 10B: Report Generation (1 week)**
- [ ] Implement PDF export (using `streamlit[pdf]`)
  - [ ] By room (one page per room)
  - [ ] By professor
  - [ ] By course
  - [ ] Full semester report
- [ ] Report contents:
  - [ ] Allocation details (discipline, professor, time, location)
  - [ ] Reservation details (if admin report)
  - [ ] Legend & notes
- [ ] Create "Relatórios" page (all users)
  - [ ] Select report type
  - [ ] Select semester / room / professor / course
  - [ ] Generate & download PDF

**Deliverables:**
- ✅ Unified calendar visualization
- ✅ Public calendar page
- ✅ PDF report generation
- ✅ Filtering & search

**Tests:**
- [ ] Manual: View calendar → Filter by room → Verify accuracy
- [ ] Manual: Generate PDF → Open & verify layout

---

### PHASE 11: Testing & Documentation (1 week)

**Objective:** Comprehensive testing and documentation

**Tasks:**
- [ ] Write unit tests for all layers:
  - [ ] Models (validation, constraints)
  - [ ] Schemas (DTO serialization)
  - [ ] Repositories (CRUD operations, queries)
  - [ ] Services (business logic)
  - [ ] Utilities (parsers, validators)
- [ ] Write integration tests:
  - [ ] End-to-end allocation workflow
  - [ ] API integration
  - [ ] Conflict detection
- [ ] Achieve >80% code coverage
- [ ] Update documentation:
  - [ ] `docs/ARCHITECTURE.md` (system design)
  - [ ] `docs/API_INTEGRATION.md` (API specs)
  - [ ] `docs/DATABASE.md` (schema details)
  - [ ] `docs/DEPLOYMENT.md` (deployment guide)
  - [ ] `docs/USER_GUIDE.md` (end-user guide)
  - [ ] `README.md` (project overview)
- [ ] Code quality:
  - [ ] Run `black` formatter
  - [ ] Run `isort` import sorter
  - [ ] Run `flake8` linter
  - [ ] Fix any issues

**Deliverables:**
- ✅ >80% test coverage
- ✅ All unit & integration tests passing
- ✅ Comprehensive documentation
- ✅ Code formatted & linted

**Tests:**
- [ ] `pytest tests/ --cov=src --cov-report=html`
- [ ] `black --check src/ pages/ tests/`
- [ ] `flake8 src/ pages/ tests/`

---

### PHASE 12: Deployment & Polish (1 week)

**Objective:** Production-ready deployment and final touches

**Tasks:**
- [ ] Docker build & test:
  - [ ] `docker build -t ensalamento-fup .`
  - [ ] `docker run -p 8501:8501 ensalamento-fup`
  - [ ] Verify app loads
- [ ] Performance optimization:
  - [ ] Profile Streamlit page load times
  - [ ] Optimize database queries (add indexes if needed)
  - [ ] Cache frequently accessed data
  - [ ] Lazy-load large datasets
- [ ] Security review:
  - [ ] Password hashing ✅
  - [ ] SQL injection prevention ✅
  - [ ] XSS protection ✅
  - [ ] CSRF tokens (if needed)
  - [ ] Rate limiting (if needed)
- [ ] Error handling & logging:
  - [ ] Try-catch all service methods
  - [ ] Log errors with timestamps
  - [ ] Display user-friendly error messages
  - [ ] Verify logs directory
- [ ] Final polish:
  - [ ] Test all pages load correctly
  - [ ] Verify responsive design (mobile/tablet/desktop)
  - [ ] Test all CRUD operations
  - [ ] Test authentication flow
  - [ ] Test allocation algorithm
  - [ ] Verify PDF exports
- [ ] Deployment documentation:
  - [ ] `.env.example` with all required variables
  - [ ] `docs/DEPLOYMENT.md` with step-by-step guide
  - [ ] NGINX reverse proxy config (HTTPS)
  - [ ] Systemd service file (optional)
- [ ] Create release notes

**Deliverables:**
- ✅ Docker image ready for production
- ✅ Comprehensive deployment documentation
- ✅ Performance optimized
- ✅ Security hardened
- ✅ All features tested end-to-end

**Tests:**
- [ ] Full end-to-end testing (all features)
- [ ] Performance testing (page load times < 2s)
- [ ] Security testing (try to hack it!)
- [ ] Docker build & run testing

---

## Task Checklist Template

Use this template for tracking progress on each phase:

```markdown
## Phase X: [Name] (X-Y weeks)

- [ ] Task 1
  - [ ] Subtask 1a
  - [ ] Subtask 1b
- [ ] Task 2
  - [ ] Subtask 2a

### Tests
- [ ] Unit tests written
- [ ] Unit tests passing
- [ ] Integration tests written
- [ ] Integration tests passing

### Documentation
- [ ] Code documented
- [ ] README updated
- [ ] User guide updated

### Code Quality
- [ ] Code formatted (black)
- [ ] Imports sorted (isort)
- [ ] Linting passing (flake8)
- [ ] No TODO/FIXME comments left

### Status
✅ COMPLETED / 🚧 IN PROGRESS / 📋 NOT STARTED
```

---

## Key Files by Phase

| Phase | Key Files to Create/Modify                                                                                                                                |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | `src/config/`, `src/models/`, `src/schemas/`, `src/db/`, `Dockerfile`                                                                                     |
| 2     | `src/services/auth_service.py`, `pages/11_👥_Usuários.py`, `src/config/auth_config.yaml`                                                                   |
| 3     | `src/services/inventory_service.py`, `pages/5_🏢_Inventário.py`, `pages/4_📊_Dashboard_Admin.py`                                                            |
| 4     | `src/services/professor_service.py`, `pages/6_👨‍🎓_Professores.py`, `pages/13_⭐_Minhas_Preferências.py`                                                      |
| 5     | `src/services/semester_service.py`, `src/services/api_service.py`, `pages/8_⚙️_Semestre.py`                                                                |
| 6     | `src/repositories/regra_repository.py`, `pages/7_📋_Regras.py`                                                                                             |
| 7     | `src/utils/sigaa_parser.py`, `src/utils/conflict_detector.py`, `src/services/allocation_service.py`, `pages/9_🎯_Alocação.py`                              |
| 8     | `pages/10_✏️_Ajustar.py`                                                                                                                                   |
| 9     | `src/services/reservation_service.py`, `pages/12_📅_Minhas_Reservas.py`                                                                                    |
| 10    | `src/ui/charts.py`, `src/services/report_service.py`, `pages/1_🏠_Inicio.py`, `pages/2_📅_Calendario.py`, `pages/3_🔍_Buscar.py`, `pages/14_📋_Relatórios.py` |
| 11    | `tests/` directory (comprehensive test suite)                                                                                                             |
| 12    | Final polish, security review, deployment docs                                                                                                            |

---

## Dependencies Between Phases

```
Phase 1 (Foundation)
    ├→ Phase 2 (Auth)
    │   ├→ Phase 3 (Inventory)
    │   │   ├→ Phase 9 (Reservations)
    │   │   └→ Phase 10 (Visualization)
    │   ├→ Phase 4 (Professors)
    │   ├→ Phase 5 (Semesters)
    │   └→ Phase 6 (Rules)
    │       └→ Phase 7 (Allocation Engine)
    │           ├→ Phase 8 (Manual Adjustment)
    │           └→ Phase 10 (Visualization)
    └→ Phase 11 (Testing)
    └→ Phase 12 (Deployment)
```

---

**Document Version:** 1.0
**Last Updated:** October 19, 2025
**Status:** ✅ Ready for Implementation
