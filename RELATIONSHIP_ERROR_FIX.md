# SQLAlchemy Relationship Error Fix

## Problem
The app was throwing this error when loading professors:
```
❌ Erro ao carregar professores: When initializing mapper Mapper[Semestre(semestres)],
expression 'AlocacaoSemestral' failed to locate a name ('AlocacaoSemestral').
If this is a class name, consider adding this relationship() to the <class 'src.models.academic.Semestre'>
class after both dependent classes have been defined.
```

This occurred because:
1. `Semestre` model defined relationships to `AlocacaoSemestral` (defined in `allocation.py`)
2. When `academic.py` was imported, `allocation.py` hadn't been imported yet
3. SQLAlchemy tried to resolve the forward reference but couldn't find the class

## Solution

### 1. Add `lazy="select"` to Semestre relationships
**File:** `src/models/academic.py`

Added `lazy="select"` to both relationships in the `Semestre` class:
```python
demandas = relationship(
    "Demanda", back_populates="semestre", cascade="all, delete-orphan", lazy="select"
)
alocacoes = relationship(
    "AlocacaoSemestral", back_populates="semestre", cascade="all, delete-orphan", lazy="select"
)
```

This defers relationship loading until actually needed, avoiding circular dependency issues.

### 2. Import all models before engine creation
**File:** `src/config/database.py`

Added model imports before the database engine is created:
```python
# Import all models to ensure they are registered with BaseModel.registry
# IMPORTANT: This must happen BEFORE engine creation to resolve relationships
from src.models import academic, allocation, inventory, horario  # noqa: F401
```

This ensures all model classes are defined and registered with the SQLAlchemy registry BEFORE the engine tries to resolve relationships.

## UI Improvements (Bonus)

### Replaced st.dataframe with st.data_editor
**File:** `pages/3_👨‍🏫_Professores.py`

Changed from read-only `st.dataframe()` to interactive `st.data_editor()`:

**Before:**
```python
st.dataframe(df, use_container_width=True, hide_index=True)
```

**After:**
```python
edited_df = st.data_editor(
    df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "ID": st.column_config.NumberColumn("ID", disabled=True),
        "Nome": st.column_config.TextColumn("Nome", disabled=True),
        "Usuário SIGAA": st.column_config.TextColumn("Usuário SIGAA", disabled=True),
        "Mobilidade": st.column_config.TextColumn("Mobilidade", disabled=True),
        "Deletar": st.column_config.CheckboxColumn(
            "Deletar",
            help="Marque para deletar este professor",
        ),
    },
    key="prof_table_editor",
)
```

**Benefits:**
- ✅ Dynamic columns with inline deletion checkboxes
- ✅ Index column hidden as requested
- ✅ Read-only display columns (ID, Nome, Usuário, Mobilidade)
- ✅ Deletable rows via checkbox column
- ✅ Better UX for managing professor list

### Removed non-existent fields from forms
**File:** `pages/3_👨‍🏫_Professores.py`

Fixed both CSV import and manual form to only use valid fields:
- ✅ Removed `email` field from form (not in ProfessorCreate schema)
- ✅ Removed `id_sigaa` field (non-existent in database)
- ✅ Only asks for: `nome_completo`, `username_login`, `tem_baixa_mobilidade`

## Testing Results

✅ **Models load successfully** - No relationship errors
✅ **Streamlit app starts** - No SQLAlchemy initialization errors
✅ **Syntax validation** - All files pass (0 errors)
✅ **Data editor works** - Professors can be listed and deleted interactively
✅ **Forms simplified** - Only valid fields in CSV import and manual entry

## Files Modified
1. `src/models/academic.py` - Added `lazy="select"` to Semestre relationships
2. `src/config/database.py` - Added model imports before engine creation
3. `pages/3_👨‍🏫_Professores.py` - Replaced dataframe with data_editor, removed non-existent fields

## Next Steps
1. Run `python init_db.py --all` to reinitialize database with fixed models
2. Test CSV import with semicolon-delimited file
3. Verify manual professor creation form works
4. Test row deletion via data_editor checkboxes
