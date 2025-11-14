# Project: Sistema de Ensalamento FUP/UnB

## Quick Start

This is a greenfield web application made with python Streamlit. You will have to use SOTA software design patterns like DRY, KISS, SOLID etc.. and propose a directory/file structure for the project. Read the documents below for complete context.



## 🛠️ Required Development Tools

**IMPORTANT**: When working in the shell, you MUST use these tools for the specified tasks:

### File & Code Search Tools
- **Finding FILES**: ALWAYS use `fd` (never use `find`)
```bash
  # Example: Find all TypeScript files
  fd -e ts -e tsx
```

- **Finding TEXT/strings**: ALWAYS use `rg` (ripgrep, never use `grep`)
```bash
  # Example: Search for "TaskStatus" in all files
  rg "TaskStatus" --type ts
```

- **Finding CODE STRUCTURE**: ALWAYS use `ast-grep` for semantic code search
```bash
  # Example: Find all React components with useState
  ast-grep --pattern 'const [$STATE, $SETTER] = useState($INIT)'
```

### Interactive & Data Tools
- **Selecting from MULTIPLE results**: ALWAYS pipe to `fzf` for interactive selection
```bash
  # Example: Interactively select a file to edit
  fd -e tsx | fzf
```

- **Interacting with JSON**: ALWAYS use `jq`
```bash
  # Example: Extract package.json dependencies
  jq '.dependencies' package.json
```

- **Interacting with YAML or XML**: ALWAYS use `yq`
```bash
  # Example: Read a value from YAML config
  yq '.database.host' config.yml
```

### Why These Tools?
- **Performance**: These tools are 10-100x faster than traditional alternatives
- **Accuracy**: Better results with smart filtering and fuzzy matching
- **Developer Experience**: Modern, user-friendly interfaces
- **Project Standard**: Required for consistency across the codebase


## 📋 Documentation Index

### Core Project Documents
- **[REQUIREMENTS.md](docs/REQUIREMENTS.md)** - Full product requirements, features, and priorities
- **[TECH_STACK.md](docs/TECH_STACK.md)** - Technology choices and rationale
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and design patterns
- **[SRS.md](docs/SRS.md)** Software Requirements Specification (THIS IS THE MOST IMPORTANT FILE!)
- **[squema.sql](docs/schema.sql)** Database modeling


## 📝 Notes for Claude Code

### Shell Command Requirements
**CRITICAL**: You MUST follow these tool requirements for ALL shell operations:
- ❌ NEVER use: `find`, `grep`, `locate`, `ack`
- ✅ ALWAYS use: `fd`, `rg`, `ast-grep`, `fzf`, `jq`, `yq` (as specified above)

### Support/Instructions Files
- When in doubt about features, check docs/REQUIREMENTS.md for priority
- Follow the component structure defined in docs/ARCHITECTURE.md
- Check docs/TECH_STACK.md
- Check SRS.md for Software Requirements Specification
- Check docs/streamlit-authenticator.md for authentication implementations instructions
- Check docs/ensalamento.md for an example of a final reservation of a room with location, hours, disciplines etc…

### Authentication Implementation (CRITICAL - Multi-Page Apps)

**REQUIRED PATTERN for Streamlit-Authenticator in multi-page apps:**

**Main page (main.py):**
```python
# Initialize authenticator ONCE
authenticator, config = setup_authenticator()

# Store in session state for all pages
st.session_state["authenticator"] = authenticator
st.session_state["config"] = config

# Render login widget ONLY on main page
authenticator.login(location="main", key="login-home")

# Show logout when authenticated
if st.session_state.get("authentication_status"):
    authenticator.logout(location="sidebar", key="logout-home")
```

**Other pages (pages/*.py):**
```python
# Check authentication
if st.session_state.get("authentication_status"):
    # Retrieve authenticator from session state
    authenticator = st.session_state.get("authenticator")

    # Call login with unrendered location (CRITICAL for page refresh fix)
    authenticator.login(location="unrendered", key="authenticator-page-name")

    # Show logout
    authenticator.logout(location="sidebar", key="logout-page-name")

    # Page content...

elif st.session_state.get("authentication_status") is None or st.session_state == {}:
    st.warning("👈 Por favor, faça login na página inicial para acessar o sistema.")
    st.page_link("main.py", label="🏠 Voltar para Home", icon="🏠")
    st.stop()
else:
    st.error("❌ Acesso negado.")
    st.stop()
```

**❌ MISTAKES TO AVOID:**
- ❌ Re-creating authenticator on every page (breaks session persistence)
- ❌ Using `location="sidebar"` or `location="main"` on non-main pages (causes error)
- ❌ Not storing authenticator in `st.session_state` (pages can't access it)
- ❌ Using same widget keys on multiple pages (causes ID collisions)
- ❌ Not calling `.login(location="unrendered")` on other pages (breaks page refresh)

**Reference Documentation:**
- `MULTIPAGE_AUTH_FIX.md` - Detailed explanation of the fix
- `SESSION_STATE_PERSISTENCE_SUMMARY.md` - Technical implementation summary
- `AUTHENTICATION_MISTAKES_TO_AVOID.md` - Common mistakes and solutions
- `TESTING_GUIDE.md` - How to test the authentication flow
- [Towards Data Science Article](https://towardsdatascience.com/implementing-streamlit-authenticator-across-multi-page-apps-5ad70ac315b3/) - Original source

### Streamlit Feedback & Toast Pattern

- Persist messages across `st.rerun()` by storing payloads in `st.session_state` **before** rerunning.
- Display them after rerun using the shared helpers in `src/utils/ui_feedback.py`:
  - `set_session_feedback("state_key", success, "Mensagem...", ttl=6, **extra)` inside the action handler.
  - `display_session_feedback("state_key")` early in the render branch to emit the toast (returns the payload so you can show extra details like error lists).
  - Use `clear_session_feedback("state_key")` when you need to force removal ahead of TTL expiration.
- Default TTL is 6 seconds; adjust per use case. The helper prevents duplicate toast emissions via the `displayed` flag.
- See `pages/3_👨‍🏫_Professores.py` for a full example covering CRUD updates and CSV imports.

### Streamlit Caching Strategy (CRITICAL for Performance)

**REQUIRED MODULE**: All cached helpers are in `src/utils/cache_helpers.py`

**Cache Types & Use Cases:**

1. **`@st.cache_resource`** - For singleton objects (stateless utilities)
   ```python
   from src.utils.cache_helpers import get_sigaa_parser

   # ✅ ALWAYS use cached singleton (never create new instances)
   parser = get_sigaa_parser()  # 622x faster on cache hits
   readable = parser.parse_to_human_readable("24M12")
   ```

2. **`@st.cache_data`** - For reference data lookups (with TTL)
   ```python
   from src.utils.cache_helpers import (
       get_predio_options,      # Building ID → name (5-min TTL)
       get_tipo_sala_options,   # Room type ID → name (5-min TTL)
       get_semester_options,    # Semester list (10-min TTL)
   )

   # ✅ Use cached lookups in all pages
   predio_options = get_predio_options()  # {1: "AT", 2: "UAC", ...}
   semester_list = get_semester_options()  # [(5, "2026-1"), (4, "2025-2"), ...]
   ```

**❌ NEVER Cache:**
- Functions with side effects (`st.write`, `st.markdown`, etc.)
- Database sessions or ORM objects
- User-specific data without user ID in cache key
- Data that changes multiple times per minute

**✅ ALWAYS Cache:**
- Utility object singletons (SigaaScheduleParser)
- Reference data lookups (buildings, room types, semesters)
- Pure functions with deterministic outputs
- Expensive computations with stable inputs

**Cache Invalidation:**
```python
from src.utils.cache_helpers import clear_all_caches, clear_reference_data_cache

# After admin updates reference data:
clear_reference_data_cache()  # Clears lookups only
# OR
clear_all_caches()  # Nuclear option (clears everything)
st.rerun()
```

**References:**
- `docs/CACHING_OPTIMIZATION_ANALYSIS.md` - Full strategy & analysis
- `docs/PHASE_2_SEMESTER_CACHE_SUMMARY.md` - Implementation examples
- `src/utils/cache_helpers.py` - All cached helper functions

### Tests, Fix and Summaries

- All test files you need to create must be placed in the  ‘tests’  folder at the project’s root.
- All text or markdown files you create to summarize a fix or document a new implementation should go into the  ‘docs’  folder, **never** in the root directory.
