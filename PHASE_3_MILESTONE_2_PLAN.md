# Phase 3 Milestone 2: Admin Multipage Interface

**Status:** Planning & Implementation
**Architecture:** Streamlit Multipage App (NOT SPA)
**Framework:** Streamlit (auto-routing via pages/ directory)

---

## 🏗️ Multipage Streamlit Architecture

### File Structure
```
ensalamento-fup/
├── main.py                          (Login, Home, Auth redirect)
├── pages/
│   ├── 1_🏠_Home.py                (Admin Dashboard)
│   ├── 2_🏢_Inventário.py          (Room/Campus/Building CRUD)
│   ├── 3_👨‍🏫_Professores.py          (Professor Import & Management)
│   ├── 4_📚_Demandas.py            (Course Demand Dashboard)
│   ├── 5_🚪_Alocações.py           (Allocation Results & Validation)
│   ├── 6_📅_Reservas.py            (Ad-hoc Reservations)
│   └── 7_⚙️_Configurações.py        (System Settings)
└── src/
    ├── repositories/               (COMPLETE ✅)
    ├── services/                   (NEW - Business logic)
    ├── schemas/                    (DTOs)
    └── models/                     (ORM)
```

### Key Differences from SPA
1. **No routing needed** - Streamlit auto-detects pages/ directory
2. **Session state persists per page** - Each page has its own `st.session_state`
3. **No client-side routing** - URL-based navigation (Streamlit handles it)
4. **Sidebar auto-generated** - Streamlit creates nav links from page names
5. **Each page is independent** - But can share session state via `st.session_state`

---

## 📋 Phase 3 Milestone 2: Implementation Plan

### Page 1: `1_🏠_Home.py` - Admin Dashboard
**Purpose:** Overview of system status, quick stats, recent activities

**Features:**
- ✅ User info card
- ✅ Key metrics (total rooms, professors, demands, allocations)
- ✅ Recent activity log
- ✅ Quick action buttons
- ✅ System status indicators

**Dependencies:**
- SalaRepository (room count)
- ProfessorRepository (prof count)
- DisciplinaRepository (demand count)
- AlocacaoRepository (allocation count)

**Status:** 🟡 TO DO

---

### Page 2: `2_🏢_Inventário.py` - Room Management
**Purpose:** Complete CRUD for rooms, buildings, campuses

**Features:**
- 📋 Tab 1: Campus Management
  - List/create/edit/delete campuses
  - Campus statistics

- 📋 Tab 2: Building Management
  - List/create/edit/delete buildings
  - Building by campus filter
  - Building statistics

- 📋 Tab 3: Room Management (MAIN)
  - Searchable room list (floor, building, capacity filters)
  - Edit room properties (capacity, characteristics, accessibility)
  - Add new room
  - Delete room
  - Room availability status
  - Room characteristics assignment

- 📋 Tab 4: Room Characteristics
  - Manage room features (projector, whiteboard, A/C, etc.)
  - Assign to rooms

**Dependencies:**
- SalaRepository (primary)
- PredioRepository (secondary)
- CampusRepository (secondary)
- CaracteristicaRepository (secondary)

**Status:** 🟡 TO DO

---

### Page 3: `3_👨‍🏫_Professores.py` - Professor Management
**Purpose:** Import and manage faculty members

**Features:**
- 📋 Tab 1: Professor List
  - Searchable list (name, email, username, department)
  - Filter by department
  - Edit professor info
  - Set availability preferences
  - Delete professor

- 📋 Tab 2: Import Professors
  - CSV upload import
  - API integration (sync from SIGAA?)
  - Bulk actions (import, update, deactivate)
  - Import preview & validation

- 📋 Tab 3: Department Management
  - List departments
  - Add/edit departments
  - Professor count by department

**Dependencies:**
- ProfessorRepository (primary)
- DepartamentoRepository (secondary)

**Status:** 🟡 TO DO

---

### Page 4: `4_📚_Demandas.py` - Course Demand Dashboard
**Purpose:** Manage course demands and allocations planning

**Features:**
- 📋 Tab 1: Demands by Semester
  - Semester selector
  - Searchable demand list (code, name, professor)
  - Filter by professor, department
  - Show: course code, name, enrollment, professor, time preference

- 📋 Tab 2: Demand Analysis
  - Large courses (>50 students)
  - High-conflict courses
  - Professor preference visualization
  - Time slot popularity

- 📋 Tab 3: Allocation Preferences
  - Set "nao_alocar" flag (exclude from allocation)
  - Preferred rooms for course
  - Preferred time slots
  - Soft constraints (professor preferences)

- 📋 Tab 4: Import Demands
  - Manual demand entry
  - API sync from Sistema de Oferta
  - Semester management

**Dependencies:**
- DisciplinaRepository (Demanda) (primary)
- DiaSemanaRepository (secondary)
- HorarioBlocoRepository (secondary)
- SemestreRepository (secondary)

**Status:** 🟡 TO DO

---

### Page 5: `5_🚪_Alocações.py` - Allocation Results
**Purpose:** View, manage, and validate course-room allocations

**Features:**
- 📋 Tab 1: Allocations Dashboard
  - Semester selector
  - Room conflict detection
  - Allocation summary stats
  - Export allocations (PDF, CSV)

- 📋 Tab 2: Room Schedule View
  - Select room
  - Display full schedule (day × time grid)
  - Show courses assigned
  - Identify empty slots

- 📋 Tab 3: Conflict Resolution
  - List conflicts (double bookings)
  - Conflict severity indicator
  - Manual reallocation form
  - Validation reports

- 📋 Tab 4: Run Allocation Algorithm
  - Configuration panel
  - Algorithm selection (if multiple strategies)
  - Start allocation process
  - Progress indicator
  - Results summary

**Dependencies:**
- AlocacaoRepository (primary)
- SalaRepository (secondary)
- DisciplinaRepository (secondary)
- AllocationService (TBD)

**Status:** 🟡 TO DO

---

### Page 6: `6_📅_Reservas.py` - Ad-hoc Reservations
**Purpose:** Manage one-off room reservations (events, meetings, etc.)

**Features:**
- 📋 Create Reservation
  - Room selector
  - Date/time picker
  - Duration
  - Purpose/description
  - Attendee count

- 📋 View Reservations
  - Calendar view
  - List view (filterable by room, date)
  - Edit/cancel reservations
  - Conflict warnings

- 📋 Room Availability Checker
  - Pick room & date
  - Show free time slots
  - Quick book

**Dependencies:**
- ReservaRepository (TBD)
- SalaRepository
- AlocacaoRepository (to check conflicts)

**Status:** 🟡 TO DO

---

### Page 7: `7_⚙️_Configurações.py` - Settings
**Purpose:** System configuration and metadata management

**Features:**
- 📋 Tab 1: System Settings
  - Current semester
  - Academic calendar settings
  - Allocation algorithm parameters
  - Email notification settings

- 📋 Tab 2: Integration Settings
  - Sistema de Oferta API key
  - SIGAA connection settings
  - Brevo email service settings

- 📋 Tab 3: About
  - System info (version, last update)
  - Database statistics
  - System health check

**Dependencies:**
- None (config file based)

**Status:** 🟡 TO DO

---

## 🔧 Supporting Services Layer (NEW)

Need to create service layer between repositories and pages for business logic:

### `src/services/allocation_service.py`
- Allocation algorithm implementation
- Conflict detection wrapper
- Room availability checking
- Optimization logic

### `src/services/import_service.py`
- CSV import handlers
- API integration (Sistema de Oferta, SIGAA)
- Data validation
- Bulk operations

### `src/services/scheduler_service.py`
- Schedule generation
- Conflict analysis
- Statistics gathering

### `src/services/notification_service.py`
- Email notifications (using Brevo)
- Allocation confirmation emails
- Schedule exports

---

## 📊 Implementation Priority

### Phase 3 Milestone 2.1 - Core Admin Pages (CURRENT)
1. ✅ `1_🏠_Home.py` - Dashboard (use existing repos)
2. ✅ `2_🏢_Inventário.py` - Room CRUD (use SalaRepository)
3. ✅ `3_👨‍🏫_Professores.py` - Professor management (use ProfessorRepository)

### Phase 3 Milestone 2.2 - Allocation Pages
1. `4_📚_Demandas.py` - Demand dashboard (use DisciplinaRepository)
2. `5_🚪_Alocações.py` - Allocation results (use AlocacaoRepository + AllocationService)

### Phase 3 Milestone 2.3 - Advanced Features
1. `6_📅_Reservas.py` - Ad-hoc reservations (new ReservaRepository)
2. `7_⚙️_Configurações.py` - Settings management

---

## 🛠️ Common Streamlit Patterns Used

### Pattern 1: Repository-Based CRUD List
```python
from src.repositories.sala import SalaRepository
from src.db import get_session

st.subheader("Salas Cadastradas")

session = get_session()
repo = SalaRepository(session)
salas = repo.get_all()

if salas:
    df = pd.DataFrame([
        {
            "ID": s.id,
            "Nome": s.nome,
            "Capacidade": s.capacidade,
            "Andar": s.andar or "N/A",
        }
        for s in salas
    ])
    st.dataframe(df, use_container_width=True)
else:
    st.info("Nenhuma sala cadastrada")
```

### Pattern 2: Form-Based Create
```python
with st.form("form_sala"):
    nome = st.text_input("Nome da Sala")
    capacidade = st.number_input("Capacidade", min_value=1)
    andar = st.selectbox("Andar", ["0", "1", "2"])

    if st.form_submit_button("Criar Sala"):
        dto = SalaCreate(nome=nome, capacidade=capacidade, andar=andar, ...)
        sala = repo.create(dto)
        st.success(f"Sala criada: {sala.nome}")
```

### Pattern 3: Session State for Page Navigation
```python
if "current_tab" not in st.session_state:
    st.session_state.current_tab = 0

tabs = st.tabs(["Lista", "Novo", "Importar"])
with tabs[0]:
    # List view
    pass
with tabs[1]:
    # Create view
    pass
```

### Pattern 4: Auth-Gated Page
```python
# At top of each page file
if not st.session_state.get("authentication_status"):
    st.error("❌ Acesso negado. Faça login primeiro.")
    st.stop()

# Rest of page content
```

---

## 📦 Dependencies Needed

Check if installed:
```bash
pip list | grep -E "pandas|plotly|streamlit"
```

May need to add to requirements.txt:
- `pandas` - Data manipulation for tables/exports
- `plotly` - Interactive charts (optional)
- `openpyxl` - Excel export (optional)
- `python-dateutil` - Date handling

---

## ✅ Checklist for Milestone 2.1

- [ ] Create `1_🏠_Home.py` with dashboard widgets
- [ ] Create `2_🏢_Inventário.py` with room CRUD
- [ ] Create `3_👨‍🏫_Professores.py` with professor management
- [ ] Test authentication redirect to pages
- [ ] Verify repository integration in each page
- [ ] Add auth-gating to all pages
- [ ] Test multipage navigation

---

## 🚀 Getting Started

The plan is to:
1. Simplify `main.py` - only handle login + redirect
2. Create page files in `pages/` directory
3. Each page handles one admin section
4. Use repositories directly in page logic (no middleware)
5. Keep session state per page but share auth state globally

This is **true multipage architecture** - Streamlit handles routing automatically!
