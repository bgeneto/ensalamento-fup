# Semester Seeding Implementation

## Problem
The `migrations.py` file was not seeding any academic semesters (`semestres` table), leaving the database without semester records needed for course allocation.

## Solution

### Added Semester Seeding
**File:** `src/db/migrations.py`

Added a new seeding section in `seed_db()` function that populates 6 academic semesters:

```python
# Seed semestres (academic terms)
semestres_data = [
    {"nome": "2024.1", "status": "Encerrado"},
    {"nome": "2024.2", "status": "Encerrado"},
    {"nome": "2025.1", "status": "Ativo"},
    {"nome": "2025.2", "status": "Planejamento"},
    {"nome": "2026.1", "status": "Planejamento"},
    {"nome": "2026.2", "status": "Planejamento"},
]

for semestre_data in semestres_data:
    existing = (
        session.query(Semestre)
        .filter(Semestre.nome == semestre_data["nome"])
        .first()
    )
    if not existing:
        semestre = Semestre(**semestre_data)
        session.add(semestre)
        print(f"  ✓ Added semester: {semestre_data['nome']} (status={semestre_data['status']})")
```

### Fixed Usuario Seeding
Also fixed a related issue where admin users were being created with non-existent fields (`email`, `roles`, `ativo`).

**Before:**
```python
admin_users_data = [
    {
        "username": "admin",
        "email": "admin@fup.unb.br",  # ❌ Doesn't exist in Usuario model
        "nome_completo": "Administrador Sistema",
        "roles": "admin",  # ❌ Should be "role" (singular)
        "ativo": True,  # ❌ Doesn't exist in Usuario model
    },
    # ...
]
```

**After:**
```python
admin_users_data = [
    {
        "username": "admin",
        "nome_completo": "Administrador Sistema",
        "role": "admin",  # ✅ Correct field name
    },
    {
        "username": "gestor",
        "nome_completo": "Gestor de Alocação",
        "role": "admin",
    },
]
```

## Verification Results

✅ **All 6 semesters created successfully:**
- 2024.1 (Encerrado - closed)
- 2024.2 (Encerrado - closed)
- 2025.1 (Ativo - active current semester)
- 2025.2 (Planejamento - planning)
- 2026.1 (Planejamento - planning)
- 2026.2 (Planejamento - planning)

✅ **All seeding steps completed:**
- ✓ 6 weekdays (SEG, TER, QUA, QUI, SEX, SAB)
- ✓ 15 time blocks (M1-M5, T1-T6, N1-N4)
- ✓ 6 semesters (2024.1 → 2026.2)
- ✓ 1 campus (FUP)
- ✓ 1 building (UAC)
- ✓ 5 room types
- ✓ 23 classrooms
- ✓ 8 room characteristics
- ✓ 2 admin users
- ✓ 142 professors from CSV

✅ **0 syntax errors** in modified file

## Data Model Alignment

The semester statuses correspond to allocation workflow states:
- **Encerrado**: Closed semesters (past allocations finalized)
- **Ativo**: Current semester with active allocations
- **Planejamento**: Future semesters in planning phase (not yet allocated)

## Testing
```bash
cd /home/bgeneto/github/ensalamento-fup
python init_db.py --all  # Full reset and reseed with all 6 semesters
```

Expected output includes:
```
✓ Added semester: 2024.1 (status=Encerrado)
✓ Added semester: 2024.2 (status=Encerrado)
✓ Added semester: 2025.1 (status=Ativo)
✓ Added semester: 2025.2 (status=Planejamento)
✓ Added semester: 2026.1 (status=Planejamento)
✓ Added semester: 2026.2 (status=Planejamento)
```

## Files Modified
1. `src/db/migrations.py` - Added semester seeding, fixed admin user seeding
