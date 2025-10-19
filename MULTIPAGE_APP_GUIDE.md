# Streamlit Multipage App - Quick Reference

## 🗺️ How Streamlit Multipage Routing Works

### File Structure = Automatic Navigation
```
project/
├── main.py                    ← DEFAULT PAGE (login/home)
└── pages/
    ├── 1_🏠_Home.py          ← First nav item
    ├── 2_🏢_Inventory.py     ← Second nav item
    ├── 3_👨‍🏫_Professors.py    ← Third nav item
    └── ...
```

### Sidebar Navigation (Auto-Generated)
Streamlit automatically creates sidebar links from file names:
- **Filename number** = sort order (1, 2, 3, ...)
- **Emoji** = icon in sidebar
- **Name after emoji** = link text

Example: `2_🏢_Inventário.py` appears as "🏢 Inventário" in sidebar

### URL Navigation
Users can also bookmark/navigate via URL:
- `localhost:8501/?page=Home`
- `localhost:8501/?page=Inventário`
- `localhost:8501/?page=Professores`

---

## 🔐 Authentication Flow

### 1. User Visits App
```
User → main.py (always first)
```

### 2. Login Page Shown
```python
# main.py
if not authenticated:
    show_login_form()
```

### 3. User Logs In
```python
authenticator.login()  # Streamlit widget
st.session_state.authentication_status = True
```

### 4. User Sees Sidebar with Page Links
```python
# main.py (after auth)
render_admin_menu()  # Shows sidebar + logout
# Streamlit auto-shows pages/ links
```

### 5. User Clicks Page Link
```
Pages auto-detected from pages/ directory
```

### 6. Page Loads
```python
# pages/X_Page.py
if not st.session_state.get("authentication_status"):
    st.stop()  # Redirect to login
```

---

## 📝 Template: Creating a New Page

### Step 1: Create file in `pages/` directory
```python
# pages/4_📚_Demands.py

"""Description of this page"""

import streamlit as st

# ============================================================
# AUTH GATING - Always do this first!
# ============================================================

if not st.session_state.get("authentication_status"):
    st.error("❌ Please login first")
    st.stop()

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Ensalamento - Demands",
    page_icon="📚",
    layout="wide",
)

# ============================================================
# IMPORTS - Add your repositories here
# ============================================================

from src.repositories.disciplina import DisciplinaRepository
from src.db import get_session

# ============================================================
# PAGE CONTENT
# ============================================================

st.title("📚 Demand Management")

# Get database session
session = get_session()

try:
    # Initialize repository
    repo = DisciplinaRepository(session)

    # Use repository
    demands = repo.get_all()

    st.write(f"Total demands: {len(demands)}")

finally:
    session.close()
```

### Step 2: That's it!
- Streamlit auto-detects the file
- File appears in sidebar with emoji
- Users can navigate to it

---

## 🏗️ Common Page Patterns

### Pattern 1: Tabbed Interface
```python
tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])

with tab1:
    st.subheader("Tab 1 Content")
    # ...

with tab2:
    st.subheader("Tab 2 Content")
    # ...
```

### Pattern 2: Data Table
```python
import pandas as pd

session = get_session()
repo = SomeRepository(session)
items = repo.get_all()

# Create DataFrame
data = [{
    "ID": item.id,
    "Name": item.name,
    "Status": item.status,
} for item in items]

df = pd.DataFrame(data)
st.dataframe(df, use_container_width=True)
session.close()
```

### Pattern 3: Filter + Display
```python
# Filters in columns
col1, col2, col3 = st.columns(3)

with col1:
    status_filter = st.selectbox("Filter by Status", ["All", "Active", "Inactive"])

with col2:
    search = st.text_input("Search")

# Apply filters
filtered = items
if status_filter != "All":
    filtered = [i for i in filtered if i.status == status_filter]
if search:
    filtered = [i for i in filtered if search.lower() in i.name.lower()]

# Display
st.dataframe(pd.DataFrame([...filtered...]))
```

### Pattern 4: CRUD Operations
```python
# Create
with st.form("create_form"):
    name = st.text_input("Name")
    if st.form_submit_button("Create"):
        repo.create(SomeDTO(name=name))
        st.success("Created!")

# Read (already shown above in table)

# Update
if st.button(f"Edit {item.id}"):
    # Show edit form

# Delete
if st.button(f"Delete {item.id}"):
    repo.delete(item.id)
    st.rerun()  # Refresh page
```

### Pattern 5: Export Data
```python
df = pd.DataFrame([...])

csv = df.to_csv(index=False)
st.download_button(
    label="📥 Export CSV",
    data=csv,
    file_name="data.csv",
    mime="text/csv",
)

# Or Excel
import openpyxl
buffer = BytesIO()
df.to_excel(buffer, index=False)
st.download_button(
    label="📥 Export Excel",
    data=buffer.getvalue(),
    file_name="data.xlsx",
    mime="application/vnd.ms-excel",
)
```

---

## 🔄 Session State Management

### Persist Data Across Reruns
```python
# Initialize
if "counter" not in st.session_state:
    st.session_state.counter = 0

# Use
st.session_state.counter += 1
st.write(f"Count: {st.session_state.counter}")
```

### Share State Between Pages
```python
# Page 1
st.session_state.selected_room_id = 5

# Page 2 (different file)
room_id = st.session_state.selected_room_id  # Can access!
```

### Global Auth State
```python
# Set during login (main.py)
st.session_state.authentication_status = True
st.session_state.name = "John"
st.session_state.username = "john_admin"

# Access in any page
if st.session_state.authentication_status:
    st.write(f"Hello {st.session_state.name}!")
```

---

## 🚀 Running the App

### Start Development Server
```bash
streamlit run main.py
```

### Auto-Reload on Changes
Streamlit automatically detects file changes and reloads. Just save and refresh!

### Add New Page Without Restarting
1. Create new file in `pages/` directory
2. Save it
3. Refresh browser - new page appears in sidebar!

---

## 📦 Repository Pattern in Pages

### Single Repository
```python
from src.repositories.sala import SalaRepository
session = get_session()
repo = SalaRepository(session)
salas = repo.get_all()
session.close()
```

### Multiple Repositories
```python
from src.repositories.sala import SalaRepository
from src.repositories.professor import ProfessorRepository
session = get_session()

try:
    sala_repo = SalaRepository(session)
    prof_repo = ProfessorRepository(session)

    salas = sala_repo.get_all()
    profs = prof_repo.get_all()
finally:
    session.close()
```

---

## ⚠️ Common Mistakes to Avoid

### ❌ Forgetting auth gate
```python
# WRONG - page will error if not logged in
st.title("Admin Page")
```

### ✅ Always gate first
```python
# CORRECT
if not st.session_state.get("authentication_status"):
    st.stop()

st.title("Admin Page")
```

### ❌ Not closing session
```python
# WRONG - resource leak
session = get_session()
repo = SomeRepository(session)
# Forgot to close!
```

### ✅ Use try/finally
```python
# CORRECT
session = get_session()
try:
    repo = SomeRepository(session)
    # Use repo
finally:
    session.close()  # Always close!
```

### ❌ Slow queries on every rerun
```python
# WRONG - queries database on every Streamlit rerun
repo = SomeRepository(session)
items = repo.get_all()  # Slow!
```

### ✅ Cache expensive operations
```python
# Use streamlit cache (if no user-specific data)
@st.cache_data
def load_items():
    session = get_session()
    try:
        repo = SomeRepository(session)
        return repo.get_all()
    finally:
        session.close()

items = load_items()
```

---

## 📚 Phase 3 Structure Example

### Current Setup (Phase 2.1)
```
main.py                    → Login page
pages/1_🏠_Home.py         → Dashboard (complete)
pages/2_🏢_Inventário.py   → Rooms CRUD (complete)
pages/3_👨‍🏫_Professores.py   → Professors CRUD (complete)
```

### Next (Phase 2.2)
```
pages/4_📚_Demandas.py     → Course demands (TODO)
pages/5_🚪_Alocações.py    → Allocations (TODO)
```

### Future (Phase 2.3)
```
pages/6_📅_Reservas.py     → Ad-hoc reservations (TODO)
pages/7_⚙️_Configurações.py → Settings (TODO)
```

---

## 🎯 Best Practices

1. **One responsibility per page** - Don't cram everything into one file
2. **Keep pages < 300 lines** - Break into sub-functions if needed
3. **Auth gate at top** - Always check `st.session_state.authentication_status`
4. **Close sessions properly** - Use try/finally
5. **Use imports consistently** - Same style across all pages
6. **Error handling** - Wrap repo calls in try/except
7. **User feedback** - Use st.success, st.error, st.warning
8. **Performance** - Cache expensive operations with @st.cache_data

---

## 🔗 Useful Streamlit Docs

- Multipage Apps: https://docs.streamlit.io/library/get-started/multipage-apps
- Session State: https://docs.streamlit.io/library/api-reference/session-state
- Caching: https://docs.streamlit.io/library/get-started/installation

---

**Remember:** Multipage apps are simpler, cleaner, and scale better than monolithic SPAs!
