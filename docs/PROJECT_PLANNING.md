# Project Planning: Sistema de Ensalamento FUP/UnB

**Date:** October 19, 2025
**Status:** Greenfield Project - Initial Planning Phase
**Project Type:** Python Streamlit Web Application

---

## Executive Summary

The **Sistema de Ensalamento FUP/UnB** is a Streamlit-based web application designed to:

1. **Automate classroom allocation (ensalamento)** - Optimize assignment of rooms to courses/disciplines based on demand, rules, and constraints
2. **Manage ad-hoc room reservations** - Enable professors, staff, and users to book spaces (classrooms, labs, auditoriums)
3. **Provide unified visualization** - Display both scheduled courses and sporadic reservations in a unified calendar/grid interface

### Key Characteristics
- **Language:** Python
- **UI Framework:** Streamlit (multipage app)
- **Database:** SQLite3
- **Architecture:** Repository Pattern with DTOs (Data Transfer Objects)
- **Authentication:** streamlit-authenticator
- **User Interface Language:** Brazilian Portuguese (pt-BR)
- **Deployment:** Self-hosted (Docker + docker-compose recommended)

---

## 1. System Overview

### 1.1. Primary Users & Roles

| Role                | Permissions        | Key Features                                                                          |
| ------------------- | ------------------ | ------------------------------------------------------------------------------------- |
| **Admin**           | Full access        | All CRUD operations, rule management, allocation engine execution, reserve management |
| **Professor/Staff** | Limited access     | View allocations, create/manage own reservations, manage own preferences              |
| **Visitor**         | Read-only (public) | View public calendar, search functionality                                            |

### 1.2. Core Features (12 Functions)

1. **Inventory Management** - Manage campuses, buildings, rooms
2. **Room Types** - CRUD for room types (classrooms, labs, auditoriums)
3. **Time Slots** - Manage Sigaa atomic time blocks (M1-M5, T1-T6, N1-N4)
4. **Room Characteristics** - CRUD for room features (projector, wheelchair access, etc.)
5. **Professor Management** - CRUD for professors and their preferences/restrictions
6. **Demand Synchronization** - Import semester data from external "Sistema de Oferta" API
7. **Allocation Rules** - Define hard (static) and soft (dynamic) rules
8. **Allocation Engine** - Execute automated semester-long room allocation algorithm
9. **Manual Adjustment** - Edit proposed allocations
10. **Ad-hoc Reservations** - Book rooms for occasional use
11. **Unified Visualization** - Calendar/grid view combining allocations + reservations
12. **User Administration** - Manage system users and authentication

---

## 2. Project Directory Structure

```
ensalamento-fup/
├── .streamlit/
│   └── config.toml              # Streamlit configuration
├── .env.example                 # Environment template
├── .env                         # Environment variables (gitignored)
├── Dockerfile                   # Docker image definition
├── docker-compose.yaml          # Docker Compose orchestration
├── mkdocs.yml                   # Documentation config
├── requirements.txt             # Python dependencies
│
├── README.md                    # Project overview
├── CLAUDE.md                    # Development instructions for Claude
│
├── docs/                        # Documentation
│   ├── schema.sql              # Database schema
│   ├── SRS.md                  # Software Requirements Specification
│   ├── TECH_STACK.md           # Technology choices & rationale
│   ├── ARCHITECTURE.md         # System architecture (to be created)
│   ├── REQUIREMENTS.md         # Feature priorities (to be created)
│   ├── streamlit-authenticator.md  # Auth documentation
│   ├── sigaa_parser.py         # Sigaa schedule parser reference
│   ├── ensalamento.md          # Example reservation data
│   ├── PROJECT_PLANNING.md     # This file
│   └── API_INTEGRATION.md      # Sistema de Oferta API specs (to be created)
│
├── src/                         # Application source code
│   ├── __init__.py
│   ├── main.py                 # Streamlit app entry point
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # Configuration & environment variables
│   │   ├── database.py         # Database connection & session management
│   │   └── auth_config.yaml    # streamlit-authenticator config
│   │
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py            # Base model (id, created_at, updated_at)
│   │   ├── campus.py          # Campus model
│   │   ├── predio.py          # Building model
│   │   ├── sala.py            # Room model
│   │   ├── tipo_sala.py       # Room type model
│   │   ├── caracteristica.py  # Room characteristic model
│   │   ├── professor.py       # Professor model + preferences
│   │   ├── usuario.py         # User model (authentication)
│   │   ├── semestre.py        # Semester model
│   │   ├── demanda.py         # Demand model
│   │   ├── alocacao_semestral.py    # Semester allocation model
│   │   ├── reserva_esporadica.py    # Ad-hoc reservation model
│   │   ├── regra.py           # Allocation rule model
│   │   └── horario_bloco.py   # Time block model
│   │
│   ├── schemas/                # Pydantic DTOs (Data Transfer Objects)
│   │   ├── __init__.py
│   │   ├── sala.py            # SalaDTO, SalaCreateDTO, etc.
│   │   ├── professor.py       # ProfessorDTO, etc.
│   │   ├── alocacao.py        # AlocacaoDTO, etc.
│   │   ├── usuario.py         # UsuarioDTO, etc.
│   │   ├── semestre.py        # SemestreDTO, DemandaDTO, etc.
│   │   ├── reserva.py         # ReservaDTO, etc.
│   │   └── base.py            # Base DTO schema
│   │
│   ├── repositories/          # Repository Pattern layer
│   │   ├── __init__.py
│   │   ├── base.py           # BaseRepository[T, D] generic template
│   │   ├── sala_repository.py
│   │   ├── professor_repository.py
│   │   ├── usuario_repository.py
│   │   ├── alocacao_repository.py
│   │   ├── reserva_repository.py
│   │   ├── semestre_repository.py
│   │   ├── demanda_repository.py
│   │   ├── regra_repository.py
│   │   └── horario_repository.py
│   │
│   ├── services/              # Business logic layer
│   │   ├── __init__.py
│   │   ├── inventory_service.py      # Rooms, buildings, campuses
│   │   ├── professor_service.py      # Professor & preferences management
│   │   ├── auth_service.py          # User authentication & management
│   │   ├── semester_service.py      # Semester & demand management
│   │   ├── allocation_service.py    # Allocation engine & rules
│   │   ├── reservation_service.py   # Ad-hoc reservations
│   │   ├── api_service.py           # External API integration (Sistema de Oferta)
│   │   ├── email_service.py         # Email notifications (Brevo API)
│   │   └── report_service.py        # Report generation (PDF export)
│   │
│   ├── utils/                 # Utility functions
│   │   ├── __init__.py
│   │   ├── sigaa_parser.py    # Sigaa time block parsing
│   │   ├── validators.py      # Input validation helpers
│   │   ├── date_utils.py      # Date/time utilities
│   │   ├── conflict_detector.py # Conflict detection logic
│   │   └── logger.py          # Logging configuration
│   │
│   ├── ui/                    # Streamlit UI components
│   │   ├── __init__.py
│   │   ├── components.py      # Reusable Streamlit components
│   │   ├── forms.py          # Form builders
│   │   ├── tables.py         # Data editor tables (st.data_editor)
│   │   └── charts.py         # Visualization components
│   │
│   └── db/                    # Database initialization
│       ├── __init__.py
│       ├── migrations.py      # Database schema migrations
│       └── seeds.py           # Initial data seeds (dias_semana, horarios_bloco, etc.)
│
├── pages/                      # Streamlit multipage app pages
│   ├── 1_🏠_Inicio.py         # Public home page
│   ├── 2_📅_Calendario.py     # Public calendar view
│   ├── 3_🔍_Buscar.py         # Public search functionality
│   │
│   ├── 4_📊_Dashboard_Admin.py # Admin dashboard (requires login + admin role)
│   ├── 5_🏢_Inventário.py     # Inventory management (admin)
│   ├── 6_👨‍🎓_Professores.py     # Professor management (admin)
│   ├── 7_📋_Regras.py         # Allocation rules (admin)
│   ├── 8_⚙️_Semestre.py       # Semester & demand management (admin)
│   ├── 9_🎯_Alocação.py       # Allocation engine execution (admin)
│   ├── 10_✏️_Ajustar.py       # Manual adjustment of allocations (admin)
│   ├── 11_👥_Usuários.py      # User management (admin)
│   │
│   ├── 12_📅_Minhas_Reservas.py   # User's own reservations (logged-in)
│   ├── 13_⭐_Minhas_Preferências.py # Professor preferences (logged-in)
│   └── 14_📋_Relatórios.py    # Reports & PDF export (all users)
│
├── static/                     # Static assets (images, CSS, etc.)
│   ├── logo.png
│   └── styles.css
│
├── data/                       # Data directory
│   ├── ensalamento.db         # SQLite database file (created at runtime)
│   └── .gitkeep
│
├── logs/                       # Application logs
│   ├── app.log
│   └── README.md
│
├── tests/                      # Unit & integration tests
│   ├── __init__.py
│   ├── conftest.py            # pytest configuration & fixtures
│   ├── test_models.py         # ORM model tests
│   ├── test_schemas.py        # DTO validation tests
│   ├── test_repositories.py   # Repository layer tests
│   ├── test_services.py       # Business logic tests
│   ├── test_allocation_engine.py  # Allocation algorithm tests
│   ├── test_sigaa_parser.py   # Sigaa parser tests
│   └── test_integration.py    # Integration tests
│
└── .github/                    # GitHub configuration
    └── workflows/
        └── ci.yml             # CI/CD pipeline (optional)
```

---

## 3. Development Phases

### Phase 1: Foundation & Setup ✅ (Planned)
**Duration:** 1-2 weeks
**Deliverables:**
- [ ] Project structure scaffolding
- [ ] Database schema creation (SQLite)
- [ ] Initial database seeding (time blocks, day mappings)
- [ ] Configuration management (.env, settings)
- [ ] Base models & schemas
- [ ] Docker setup (Dockerfile, docker-compose.yaml)

**Key Files:**
- `src/config/` - Configuration & database setup
- `src/models/base.py` - Base ORM model
- `src/schemas/base.py` - Base DTO schema
- `src/db/seeds.py` - Database initialization
- `Dockerfile` & `docker-compose.yaml` - Deployment

---

### Phase 2: Authentication & User Management ✅ (Planned)
**Duration:** 1 week
**Deliverables:**
- [ ] streamlit-authenticator integration
- [ ] User CRUD pages (admin only)
- [ ] Login/logout pages
- [ ] Password reset functionality
- [ ] Role-based access control (RBAC) middleware

**Key Files:**
- `src/services/auth_service.py`
- `src/repositories/usuario_repository.py`
- `src/models/usuario.py`
- `pages/11_👥_Usuários.py` (admin)
- `src/config/auth_config.yaml`

---

### Phase 3: Inventory Management ✅ (Planned)
**Duration:** 1-2 weeks
**Deliverables:**
- [ ] Campus CRUD
- [ ] Building CRUD
- [ ] Room Type CRUD
- [ ] Room Characteristics CRUD
- [ ] Room CRUD (with multi-select characteristics)
- [ ] Admin inventory dashboard

**Key Files:**
- `src/services/inventory_service.py`
- `src/repositories/sala_repository.py`, etc.
- `pages/5_🏢_Inventário.py` (admin)

---

### Phase 4: Professor Management ✅ (Planned)
**Duration:** 1 week
**Deliverables:**
- [ ] Professor CRUD
- [ ] Professor preference management (soft rules)
- [ ] Self-service professor preferences page
- [ ] Link professors to user accounts

**Key Files:**
- `src/services/professor_service.py`
- `src/repositories/professor_repository.py`
- `src/models/professor.py`
- `pages/6_👨‍🎓_Professores.py` (admin)
- `pages/13_⭐_Minhas_Preferências.py` (self-service)

---

### Phase 5: Semester & Demand Management ✅ (Planned)
**Duration:** 1 week
**Deliverables:**
- [ ] Semester CRUD
- [ ] External API integration (Sistema de Oferta)
- [ ] Demand import & synchronization
- [ ] Data validation & error handling
- [ ] Semester management page

**Key Files:**
- `src/services/semester_service.py`, `api_service.py`
- `src/repositories/semestre_repository.py`, `demanda_repository.py`
- `src/utils/sigaa_parser.py`
- `pages/8_⚙️_Semestre.py` (admin)

---

### Phase 6: Allocation Rules ✅ (Planned)
**Duration:** 1 week
**Deliverables:**
- [ ] Rule CRUD (hard & soft rules)
- [ ] Rule types: discipline-room-type, discipline-room, equipment requirements
- [ ] Rule conflict detection
- [ ] Rule management page

**Key Files:**
- `src/services/allocation_service.py` (rule subset)
- `src/repositories/regra_repository.py`
- `pages/7_📋_Regras.py` (admin)

---

### Phase 7: Allocation Engine ✅ (Planned)
**Duration:** 2-3 weeks
**Deliverables:**
- [ ] Sigaa schedule parser (parse "24M12" → [day=2, block=M1, M2], etc.)
- [ ] Conflict detection algorithm
- [ ] Hard rule allocation (priority-based)
- [ ] Soft rule allocation (scoring algorithm)
- [ ] Allocation execution & persistence
- [ ] Allocation results page

**Key Files:**
- `src/services/allocation_service.py` (main allocation logic)
- `src/utils/sigaa_parser.py`
- `src/utils/conflict_detector.py`
- `pages/9_🎯_Alocação.py` (admin)
- `tests/test_allocation_engine.py`

---

### Phase 8: Manual Adjustment ✅ (Planned)
**Duration:** 1 week
**Deliverables:**
- [ ] Manual room swap functionality
- [ ] Real-time conflict validation
- [ ] Rule violation alerts
- [ ] Allocation adjustment page

**Key Files:**
- `src/services/allocation_service.py` (adjustment subset)
- `pages/10_✏️_Ajustar.py` (admin)

---

### Phase 9: Ad-hoc Reservations ✅ (Planned)
**Duration:** 1-2 weeks
**Deliverables:**
- [ ] Reservation CRUD (user & admin)
- [ ] Conflict detection with allocations + other reservations
- [ ] Self-service reservation page
- [ ] Admin reservation management page
- [ ] Cancellation & editing

**Key Files:**
- `src/services/reservation_service.py`
- `src/repositories/reserva_repository.py`
- `pages/12_📅_Minhas_Reservas.py` (user)
- `pages/14_📋_Relatórios.py` (optional admin view)

---

### Phase 10: Visualization & Reporting ✅ (Planned)
**Duration:** 1-2 weeks
**Deliverables:**
- [ ] Unified calendar/grid view (allocations + reservations)
- [ ] Block consolidation (M1+M2 → 08:00/09:50)
- [ ] Filter by room/professor/course
- [ ] PDF export functionality
- [ ] Public calendar page
- [ ] Search functionality

**Key Files:**
- `src/services/report_service.py`
- `src/ui/charts.py`
- `pages/1_🏠_Inicio.py` (public home)
- `pages/2_📅_Calendario.py` (public calendar)
- `pages/3_🔍_Buscar.py` (public search)
- `pages/14_📋_Relatórios.py` (all users)

---

### Phase 11: Testing & Documentation ✅ (Planned)
**Duration:** 1 week
**Deliverables:**
- [ ] Unit tests for all layers (>80% coverage)
- [ ] Integration tests
- [ ] API endpoint tests
- [ ] Sigaa parser tests
- [ ] Documentation updates

**Key Files:**
- `tests/` directory
- `docs/API_INTEGRATION.md`
- `docs/ARCHITECTURE.md`

---

### Phase 12: Deployment & Polish ✅ (Planned)
**Duration:** 1 week
**Deliverables:**
- [ ] Docker build & testing
- [ ] Performance optimization
- [ ] Security review
- [ ] Error handling & logging
- [ ] Deployment documentation

**Key Files:**
- `Dockerfile`
- `docker-compose.yaml`
- `.env.example`
- `docs/DEPLOYMENT.md`

---

## 4. Technology Stack & Dependencies

### Core Framework
```python
streamlit>=1.50.0                    # Web UI framework
streamlit-authenticator>=0.4.2       # User authentication
streamlit[pdf]                       # PDF export
```

### Database & ORM
```python
sqlalchemy                           # ORM & database toolkit
aiosqlite                           # Async SQLite access
```

### Data & Validation
```python
pydantic                            # Data validation & serialization
pydantic[email]                     # Email validation
```

### Security & Crypto
```python
cryptography                        # Encryption utilities
bcrypt                             # Password hashing
python-dotenv                      # Environment variable management
```

### API & Communication
```python
requests                           # HTTP client (System de Oferta API)
pyyaml                            # YAML configuration parsing
```

### Development & Testing
```python
pytest                            # Testing framework
pytest-asyncio                    # Async test support
black                            # Code formatter
isort                            # Import sorting
flake8                           # Linter
```

### Documentation
```python
mkdocs-material                  # Documentation generator
mkdocs-with-pdf                  # PDF export for docs
```

---

## 5. Database Schema Overview

### Core Tables (12 main tables)

**Inventory:**
- `campus` - Campuses
- `predios` - Buildings
- `tipos_sala` - Room types
- `salas` - Rooms
- `caracteristicas` - Room characteristics
- `sala_caracteristicas` - Room-characteristic mapping (N:N)

**Time Management:**
- `dias_semana` - Weekdays (Sigaa mapping)
- `horarios_bloco` - Atomic time blocks (M1-M5, T1-T6, N1-N4)

**Academic Management:**
- `semestres` - Semesters (2025.1, 2025.2, etc.)
- `demandas` - Course demand (imported from API)
- `professores` - Professor records with hard restrictions
- `professor_prefere_sala` - Professor preferred rooms (N:N)
- `professor_prefere_caracteristica` - Professor preferred characteristics (N:N)

**Users & Authentication:**
- `usuarios` - System users
- `roles` - User roles (admin, professor, etc.)

**Allocation & Reservations:**
- `regras` - Allocation rules (hard/soft)
- `alocacoes_semestrais` - Semester-wide allocations
- `reservas_esporadicas` - Ad-hoc reservations

---

## 6. Key Architectural Patterns

### 6.1. Repository Pattern with DTOs

```
Streamlit Pages (No DB knowledge)
        ↓
Service Layer (Business Logic)
        ↓
Repository Layer (Data Access)
        ├→ Database Session (ORM ↔ DTO conversion)
        └→ Return DTOs (pure Python objects)
        ↓
Database Layer (SQLAlchemy ORM)
```

**Benefits:**
- Eliminates `DetachedInstanceError`
- Clean separation of concerns
- Easy to test (mock DTOs)
- Type safety via Pydantic

### 6.2. Role-Based Access Control (RBAC)

```python
# Check user role in Streamlit session state
if not st.session_state.get("authentication_status"):
    st.error("Please log in")
elif "admin" not in st.session_state.get("roles", []):
    st.error("Admin access required")
else:
    # Render admin page
```

### 6.3. Streamlit Multipage App Structure

```
/pages
  ├── 1_🏠_Inicio.py              # Public (no auth)
  ├── 2_📅_Calendario.py          # Public (no auth)
  ├── 3_🔍_Buscar.py              # Public (no auth)
  ├── 4_📊_Dashboard_Admin.py      # Admin only
  ├── 5_🏢_Inventário.py          # Admin only
  ├── 6_👨‍🎓_Professores.py         # Admin only
  ├── 7_📋_Regras.py              # Admin only
  ├── 8_⚙️_Semestre.py            # Admin only
  ├── 9_🎯_Alocação.py            # Admin only
  ├── 10_✏️_Ajustar.py            # Admin only
  ├── 11_👥_Usuários.py           # Admin only
  ├── 12_📅_Minhas_Reservas.py    # Logged-in users
  ├── 13_⭐_Minhas_Preferências.py # Logged-in professors
  └── 14_📋_Relatórios.py         # All users (if logged in)
```

---

## 7. API Integration (Sistema de Oferta)

**Expected API Response Format:**
```json
{
  "disciplinas": [
    {
      "codigo_disciplina": "CSXXX",
      "nome_disciplina": "Disciplina Name",
      "professores_disciplina": "Dr. João Silva, Dra. Maria",
      "turma_disciplina": "01",
      "vagas_disciplina": 40,
      "horario_disciplina": "24M12 6T34",
      "nivel_disciplina": "Graduação"
    }
  ]
}
```

**Key Points:**
- Parse `horario_disciplina` (e.g., "24M12") to atomic blocks
- Match professor names (text) to `professores` table
- Mark non-room disciplines (e.g., "Estágio") as "Não Alocar"

---

## 8. Sigaa Time Block Parsing

**Example Input:** `"24M12 6T34"`

**Parsing Logic:**
1. Split by space: `["24M12", "6T34"]`
2. For each token:
   - Day code (first digit): 2, 4, 6 = Monday, Wednesday, Friday
   - Block code (last 2 chars): M1, M2, T3, T4, etc.
3. **Output:** `[(day=2, block="M1"), (day=2, block="M2"), (day=4, block="T3"), (day=4, block="T4"), (day=6, block="T3"), (day=6, block="T4")]`

**Reference:** `src/utils/sigaa_parser.py` (to be implemented based on docs/sigaa_parser.py)

---

## 9. Allocation Algorithm Overview

### Step 1: Parse & Validate
- Parse all `horario_sigaa_bruto` values
- Match professors to `professores` table
- Identify conflicts early

### Step 2: Hard Rules First (Priority-Based)
- Allocate disciplines with hard rules (discipline-room-type, discipline-specific room)
- Sort by number of constraints (most constrained first)
- **STOP** if conflict detected

### Step 3: Soft Rules (Scoring Algorithm)
- For remaining demands, calculate room scores:
  - +10 points if room matches soft rule
  - +5 points if room has preferred characteristics
  - +3 points if room capacity ≥ demand vagas
  - -5 points if allocating professor elsewhere
- Allocate to highest-scoring room
- If tie, use tiebreaker (e.g., room ID)

### Step 4: Persist Results
- Save each atomic block allocation as separate row in `alocacoes_semestrais`
- Enable manual adjustment in Phase 8

---

## 10. Testing Strategy

### Unit Tests (>80% coverage)
```
tests/
├── test_models.py           # ORM model validation
├── test_schemas.py          # DTO validation
├── test_repositories.py     # CRUD operations
├── test_services.py         # Business logic
├── test_allocation_engine.py # Allocation algorithm
├── test_sigaa_parser.py     # Schedule parsing
└── test_integration.py      # End-to-end flows
```

### Test Approach
- Use pytest fixtures for database fixtures
- Mock external APIs (Sistema de Oferta)
- Test conflict detection thoroughly
- Validate all DTO serialization/deserialization

---

## 11. Environment Configuration

### `.env` Template
```bash
# Database
DATABASE_URL=sqlite:///./data/ensalamento.db

# External APIs
SISTEMA_OFERTA_API_URL=https://api.unb.br/oferta
SISTEMA_OFERTA_API_KEY=xxx

# Email (Brevo)
BREVO_API_KEY=xxx
BREVO_FROM_EMAIL=sistema@fup.unb.br

# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_LOGGER_LEVEL=info

# Security
SECRET_KEY=xxx (for authentication)
```

---

## 12. Deployment Checklist

- [ ] Docker image builds successfully
- [ ] Database migrations run without errors
- [ ] All tests pass (>80% coverage)
- [ ] Security review (password hashing, SQL injection, XSS)
- [ ] Performance testing (page load times < 2s)
- [ ] Logging configured for debugging
- [ ] Error handling comprehensive
- [ ] Documentation complete & tested
- [ ] Production environment variables configured
- [ ] HTTPS/TLS certificate configured (nginx proxy)

---

## 13. Key Milestones

| Date       | Milestone                         | Status    |
| ---------- | --------------------------------- | --------- |
| Week 1-2   | Phase 1: Foundation               | 📋 Planned |
| Week 3     | Phase 2: Authentication           | 📋 Planned |
| Week 4-5   | Phase 3: Inventory                | 📋 Planned |
| Week 6     | Phase 4: Professors               | 📋 Planned |
| Week 7     | Phase 5: Semesters & Demand       | 📋 Planned |
| Week 8     | Phase 6: Allocation Rules         | 📋 Planned |
| Week 9-11  | Phase 7: Allocation Engine        | 📋 Planned |
| Week 12    | Phase 8: Manual Adjustment        | 📋 Planned |
| Week 13-14 | Phase 9: Ad-hoc Reservations      | 📋 Planned |
| Week 15-16 | Phase 10: Visualization & Reports | 📋 Planned |
| Week 17    | Phase 11: Testing & Docs          | 📋 Planned |
| Week 18    | Phase 12: Deployment & Polish     | 📋 Planned |

---

## 14. Design Principles & Best Practices

### Code Organization
- **DRY (Don't Repeat Yourself)** - Reusable components & functions
- **KISS (Keep It Simple, Stupid)** - Clear, readable code
- **SOLID Principles** - Proper separation of concerns
- **SOC (Separation of Concerns)** - Clear layer boundaries

### Naming Conventions
- **Files:** `snake_case.py`
- **Classes:** `PascalCase` (ORM models, services, repositories)
- **Functions/Methods:** `snake_case()`
- **Constants:** `UPPER_CASE`
- **DTOs:** Suffix with "DTO" (e.g., `SalaDTO`)
- **Repositories:** Suffix with "Repository" (e.g., `SalaRepository`)

### Error Handling
- Validate input at service layer
- Return meaningful error messages
- Log all errors for debugging
- Display user-friendly errors in UI

### Performance Considerations
- Use eager loading in repositories (avoid N+1 queries)
- Cache frequently accessed data (e.g., time blocks)
- Limit API calls (batch when possible)
- Profile Streamlit page load times

### Security
- Always hash passwords (bcrypt)
- Validate all external input
- Prevent SQL injection (use SQLAlchemy ORM)
- Protect against XSS (Streamlit handles this)
- Use environment variables for secrets

---

## 15. Next Steps

1. **Review & Approve Planning** - Confirm scope and phases with stakeholders
2. **Set Up Development Environment** - Create .env, Dockerfile, docker-compose
3. **Implement Phase 1** - Foundation: models, schemas, database
4. **Begin Phase 2** - Authentication: streamlit-authenticator integration
5. **Iterative Development** - Follow phased approach with testing at each stage
6. **Documentation** - Update docs as features are completed
7. **Deployment** - Containerize and deploy to FUP/UnB servers

---

## 16. References & Resources

- **Streamlit Docs:** https://docs.streamlit.io/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/
- **Pydantic Docs:** https://docs.pydantic.dev/
- **streamlit-authenticator Docs:** See `docs/streamlit-authenticator.md`
- **Project SRS:** `docs/SRS.md`
- **Tech Stack:** `docs/TECH_STACK.md`
- **Requirements:** `docs/REQUIREMENTS.md` (to be created)

---

**Document Version:** 1.0
**Last Updated:** October 19, 2025
**Status:** ✅ Ready for Implementation
