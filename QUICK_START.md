# 🚀 Quick Start - Phase 3 Multipage App

## Start the App
```bash
cd /home/bgeneto/github/ensalamento-fup
streamlit run main.py
```

## Login
- **Username:** `admin` or `gestor`
- **Password:** `admin123` or `gestor2024`

## Navigate
Sidebar auto-generated from `pages/` directory:
- 🏠 Home - Dashboard with metrics
- 🏢 Inventário - Room management (CRUD)
- 👨‍🏫 Professores - Professor management (CRUD)
- 📚 Demandas - Course demands (coming next)
- 🚪 Alocações - Allocations (coming next)
- 📅 Reservas - Ad-hoc reservations (future)
- ⚙️ Configurações - Settings (future)

---

## What's Working Now

### 🏠 Home Dashboard
- ✅ Shows 23 real rooms
- ✅ Key metrics (rooms, professors, demands, allocations)
- ✅ Recent activities feed
- ✅ Quick action buttons
- ✅ System status indicators
- ✅ Setup guide

### 🏢 Inventory - Rooms
- ✅ List all 23 rooms
- ✅ Filter by floor, capacity, name
- ✅ Export to CSV
- ✅ View room details
- ✅ Delete rooms
- ⏳ Edit rooms (form ready)

### 👨‍🏫 Professors
- ✅ List professors (0 in DB - ready for import)
- ✅ Search by name/email
- ✅ Filter by department
- ✅ Export to CSV
- ✅ View professor details
- ✅ Delete professors
- ✅ Department statistics with chart
- ⏳ CSV import (validation working, save TODO)
- ⏳ Manual entry form (ready)

---

## How Pages Work

### File Structure
```
pages/
  ├── 1_🏠_Home.py          (emoji + name = sidebar link)
  ├── 2_🏢_Inventário.py    (number = sort order)
  └── 3_👨‍🏫_Professores.py
```

### Automatic Routing
Streamlit automatically creates sidebar from page filenames:
- **1, 2, 3** = display order
- **Emoji** = icon
- **Name** = link text

### Auth Gating
Every page starts with:
```python
if not st.session_state.get("authentication_status"):
    st.error("❌ Please login first")
    st.stop()
```

---

## Database Status

### Current Data
```
salas (rooms): 23 total
  - Andar 0 (ground floor): 7
  - Andar 1 (first floor): 16

professores (professors): 0 (empty, ready for import)

demandas (course demands): 0 (empty)

alocacoes (allocations): 0 (empty)
```

### Check DB
```bash
sqlite3 data/ensalamento.db
SELECT COUNT(*) FROM salas;        # 23
SELECT COUNT(*) FROM professores;  # 0
.quit
```

---

## Repositories Active

### In Use Now
- ✅ SalaRepository (Home, Inventory pages)
- ✅ ProfessorRepository (Professors page)
- ⏳ DisciplinaRepository (ready for Demands page)
- ⏳ DiaSemanaRepository (ready for Demands page)
- ⏳ HorarioBlocoRepository (ready for Demands page)
- ⏳ AlocacaoRepository (ready for Allocations page)

### All 6 Tested & Working
All repositories tested in Phase 3 M1 ✅

---

## Code Organization

### main.py (70 lines)
- Login page
- Auth setup
- Sidebar with logout

### pages/1_🏠_Home.py (230 lines)
- Dashboard with metrics
- Uses all 4 main repos

### pages/2_🏢_Inventário.py (280 lines)
- Room CRUD interface
- Uses SalaRepository

### pages/3_👨‍🏫_Professores.py (290 lines)
- Professor CRUD interface
- Uses ProfessorRepository

### Total UI Code: ~800 lines
Clean, focused, maintainable!

---

## Session State Management

### Authentication State (Global)
```python
st.session_state.authentication_status  # True/False
st.session_state.name                   # "John Doe"
st.session_state.username               # "jdoe"
```

### Page-Specific State (Local)
Each page can have its own state:
```python
if "editing_room_id" not in st.session_state:
    st.session_state.editing_room_id = None
```

### Persist Across Reruns
```python
st.session_state.my_value = "stays"  # Survives Streamlit reruns
```

---

## Common Operations

### Display Data Table
```python
import pandas as pd
from src.repositories.sala import SalaRepository
from src.db import get_session

session = get_session()
repo = SalaRepository(session)
salas = repo.get_all()

df = pd.DataFrame([{"ID": s.id, "Nome": s.nome} for s in salas])
st.dataframe(df, use_container_width=True)

session.close()
```

### Add Filter
```python
floor_filter = st.selectbox("Filtrar por Andar", ["Todos", "Térreo", "1º Andar"])

if floor_filter == "Térreo":
    filtered = repo.get_by_andar("0")
elif floor_filter == "1º Andar":
    filtered = repo.get_by_andar("1")
else:
    filtered = repo.get_all()
```

### Export to CSV
```python
csv = df.to_csv(index=False)
st.download_button(
    label="📥 Export CSV",
    data=csv,
    file_name="data.csv",
    mime="text/csv",
)
```

### Delete Item
```python
if st.button("🗑️ Delete"):
    repo.delete(item_id)
    st.success("Deleted!")
    st.rerun()
```

---

## Next Phase Stubs (Ready to Expand)

### Page 4: Demands
```
pages/4_📚_Demandas.py  (stub, 60 lines)
```
Tabs:
- Tab 1: Demands by semester
- Tab 2: Demand analysis
- Tab 3: Allocation preferences
- Tab 4: Import demands

### Page 5: Allocations
```
pages/5_🚪_Alocações.py (stub, 60 lines)
```
Tabs:
- Tab 1: Allocations dashboard
- Tab 2: Room schedule view
- Tab 3: Conflict resolution
- Tab 4: Run algorithm

### Allocation Service (TODO)
```
src/services/allocation_service.py (NOT CREATED YET)
```
- Conflict detection
- Course-room matching
- Optimization logic

---

## Testing Checklist

- [ ] Start app: `streamlit run main.py`
- [ ] Login: admin / admin123
- [ ] See sidebar with 7 pages
- [ ] Click 🏠 Home - see dashboard with 23 rooms
- [ ] Click 🏢 Inventário - see room list, filters, delete button
- [ ] Click 👨‍🏫 Professores - see professor management
- [ ] Test filters on each page
- [ ] Test CSV export
- [ ] Test delete button
- [ ] Logout and verify login page reappears

---

## File Locations

### Core Files
```
main.py                                 ← Main entry point (auth)
pages/
  ├── 1_🏠_Home.py                    ← Dashboard
  ├── 2_🏢_Inventário.py              ← Room management
  └── 3_👨‍🏫_Professores.py            ← Professor management
```

### Database
```
data/ensalamento.db                     ← SQLite database
```

### Repositories
```
src/repositories/
  ├── base.py                           ← Base repository
  ├── sala.py                           ← Room repository ✅
  ├── professor.py                      ← Professor repository ✅
  ├── disciplina.py                     ← Demand repository ✅
  ├── dia_semana.py                     ← Weekday repository ✅
  ├── horario_bloco.py                  ← Time block repository ✅
  └── alocacao.py                       ← Allocation repository ✅
```

### Documentation
```
PHASE_3_MILESTONE_2_PLAN.md             ← Detailed plan
PHASE_3_MILESTONE_2_STARTED.md          ← Completion summary
MULTIPAGE_APP_GUIDE.md                  ← Reference guide
PHASE_3_M2_SESSION_SUMMARY.md           ← This session summary
```

---

## Troubleshooting

### Page not showing in sidebar?
- Check filename format: `X_📌_Name.py`
- Number must be at start (1, 2, 3...)
- File must be in `pages/` directory
- Restart Streamlit

### Auth error on page?
- Make sure auth check is at TOP of page
- Restart Streamlit after login

### Database errors?
- Check: `sqlite3 data/ensalamento.db ".schema"`
- Ensure session.close() is called
- Use try/finally blocks

### Import errors?
- Check paths are correct (e.g., `from src.repositories.sala import SalaRepository`)
- Ensure __init__.py files exist
- Run from project root directory

---

## Ready for Phase 3 M2.2!

Next steps:
1. ✅ Multipage architecture (done)
2. ✅ 3 complete pages (done)
3. ✅ Repository integration (done)
4. 🟡 Demand page (next)
5. 🟡 Allocation page (next)
6. 🟡 Allocation algorithm (after)

**Status:** Ready to build Phase 2.2! 🚀
