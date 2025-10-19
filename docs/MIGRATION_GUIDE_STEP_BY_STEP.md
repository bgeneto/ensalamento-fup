"""
STEP-BY-STEP MIGRATION GUIDE
Refactoring from Detached ORM Objects to Repository Pattern with DTOs

This guide walks you through the complete refactoring process with specific,
actionable steps.
"""

# ============================================================================
# PHASE 1: SETUP (1-2 hours)
# ============================================================================

"""
PHASE 1: Foundation Setup

What you're doing:
  Creating the base infrastructure for the new architecture

Files to create/verify:
  ✓ src/repositories/base.py (CREATED)
  ✓ src/repositories/__init__.py (CREATE)
  ✓ src/schemas/__init__.py (CREATE)
  ✓ src/schemas/sala.py (CREATED)
  ✓ src/repositories/sala.py (CREATED)

Step 1.1: Create __init__.py files
"""

# src/repositories/__init__.py
"""
Repositories module
"""
from src.repositories.sala import SalaRepository, get_sala_repository

__all__ = [
    'SalaRepository',
    'get_sala_repository',
]

# src/schemas/__init__.py
"""
Data Transfer Objects (DTOs) and Pydantic models
"""
from src.schemas.sala import (
    SalaDTO,
    SalaSimplifiedDTO,
    SalaDetailDTO,
    SalaCreateDTO,
    SalaUpdateDTO,
    PredioDTO,
    TipoSalaDTO,
    CaracteristicaDTO,
    CampusDTO,
)

__all__ = [
    'SalaDTO',
    'SalaSimplifiedDTO',
    'SalaDetailDTO',
    'SalaCreateDTO',
    'SalaUpdateDTO',
    'PredioDTO',
    'TipoSalaDTO',
    'CaracteristicaDTO',
    'CampusDTO',
]

"""
Step 1.2: Verify base repository works
Run this test:

from src.repositories.base import BaseRepository
print("✓ BaseRepository imported successfully")

Expected output: ✓ BaseRepository imported successfully
"""

# ============================================================================
# PHASE 2: MIGRATION STRATEGY (Choose One)
# ============================================================================

"""
OPTION A: INCREMENTAL MIGRATION (Recommended for production systems)

  Benefits:
  ✓ Can test gradually
  ✓ Lower risk
  ✓ Can deploy parts independently

  Steps:
  1. Refactor InventoryService (handles Salas)
  2. Update all pages using InventoryService
  3. Refactor AllocationService
  4. Update pages using AllocationService
  5. Repeat for other services

  Timeline: 2-3 weeks
  Risk: Low

OPTION B: BIG BANG MIGRATION (Recommended for smaller codebases)

  Benefits:
  ✓ Faster overall
  ✓ Consistent architecture
  ✓ No mixed patterns

  Steps:
  1. Create all repositories (1 day)
  2. Create all DTOs (1 day)
  3. Refactor all services (1 day)
  4. Update all pages (1 day)
  5. Test everything (1 day)

  Timeline: 1 week
  Risk: Medium (need good test coverage)

We'll demonstrate INCREMENTAL approach as it's safer.
"""

# ============================================================================
# PHASE 2A: INCREMENTAL STEP 1 - Refactor InventoryService
# ============================================================================

"""
STEP 2A.1: Create the Sala repository

Status: ✓ DONE - src/repositories/sala.py created

This repository handles all database queries for rooms and converts
ORM objects to DTOs automatically.

Key features:
  • get_all_with_eager_load() - Efficient loading
  • get_by_id() - Fetch by primary key
  • get_by_campus() - Filter by campus
  • search_by_name() - Search functionality
  • create() - Create new rooms
  • update() - Update existing rooms
  • delete() - Delete rooms

STEP 2A.2: Create DTOs for rooms

Status: ✓ DONE - src/schemas/sala.py created

DTOs include:
  • SalaDTO - Full room with all relationships
  • SalaSimplifiedDTO - Minimal data for dropdowns
  • SalaCreateDTO - For creation requests
  • SalaUpdateDTO - For update requests
  • PredioDTO, TipoSalaDTO, CaracteristicaDTO - Nested relationships

STEP 2A.3: Create refactored InventoryService

Status: ✓ DONE - src/services/inventory_service_refactored.py created

This service:
  • Uses SalaRepository internally
  • Returns DTOs instead of ORM objects
  • Maintains same interface as before
  • Fully backward compatible

STEP 2A.4: Test the refactored service

Create file: tests/test_refactored_service.py

from src.services.inventory_service_refactored import InventoryService
from src.schemas.sala import SalaDTO

def test_get_all_salas():
    rooms = InventoryService.get_all_salas()
    assert isinstance(rooms, list)
    if rooms:
        assert isinstance(rooms[0], SalaDTO)
    print(f"✓ Got {len(rooms)} rooms")

def test_get_sala_by_id():
    if InventoryService.get_rooms_count() > 0:
        room = InventoryService.get_sala_by_id(1)
        assert room is not None
        assert isinstance(room, SalaDTO)
        assert room.predio is not None  # ← Check relationship works
        print(f"✓ Room: {room.nome}")

def test_search():
    results = InventoryService.search_salas("Lab")
    assert isinstance(results, list)
    print(f"✓ Found {len(results)} matching rooms")

# Run tests
test_get_all_salas()
test_get_sala_by_id()
test_search()

Expected output:
  ✓ Got X rooms
  ✓ Room: Room Name
  ✓ Found Y matching rooms
  ✓ No DetachedInstance errors!
"""

# ============================================================================
# PHASE 2B: INCREMENTAL STEP 2 - Update Pages Using InventoryService
# ============================================================================

"""
STEP 2B.1: Update pages/3_Admin_Rooms.py

Before (Old code - causes DetachedInstance errors):
```python
from src.services.inventory_service import InventoryService

rooms = InventoryService.get_all_salas()  # Returns ORM objects ❌
for room in rooms:
    print(room.predio.nome)  # ❌ DetachedInstance error!
```

After (New code - safe DTOs):
```python
import streamlit as st
from src.services.inventory_service_refactored import InventoryService

# Use Streamlit caching for better performance
@st.cache_data(ttl=300)
def load_rooms():
    return InventoryService.get_all_salas()  # Returns DTOs ✓

rooms = load_rooms()
for room in rooms:
    st.write(f"Room: {room.nome}")
    st.write(f"Building: {room.predio.nome}")  # ✓ Safe! It's a DTO
    st.write(f"Capacity: {room.capacidade}")
```

STEP 2B.2: Update pages/4_Admin_Allocations.py (if using InventoryService)

Same pattern - use the refactored service that returns DTOs.

STEP 2B.3: Test the pages

1. Start Streamlit: streamlit run home.py
2. Navigate to Admin Rooms page
3. Try filtering and sorting
4. Check browser console for errors
5. Check /logs/app.log for DetachedInstance errors
6. Should see: No errors! ✓

STEP 2B.4: Deploy this phase

Once pages work:
1. git add pages/
2. git commit -m "Phase 2B: Update pages to use refactored InventoryService"
3. Deploy to production
"""

# ============================================================================
# PHASE 3: REPEAT FOR OTHER SERVICES
# ============================================================================

"""
STEP 3.1: Refactor AllocationService (Similar pattern)

Create:
  • src/repositories/alocacao.py (AlocacaoRepository)
  • src/schemas/alocacao.py (DTOs for allocations)
  • src/services/allocation_service_refactored.py

The pattern is identical to what we did for InventoryService.

STEP 3.2: Refactor SemesterService

Create:
  • src/repositories/semestre.py
  • src/schemas/semestre.py
  • src/services/semester_service_refactored.py

STEP 3.3: Refactor AuthService

Create:
  • src/repositories/usuario.py
  • src/schemas/usuario.py
  • src/services/auth_service_refactored.py

Continue for remaining services...
"""

# ============================================================================
# PHASE 4: TESTING STRATEGY
# ============================================================================

"""
Test each refactored service thoroughly:

Unit tests:
  • Test repository methods individually
  • Mock database layer
  • Verify DTOs are returned
  • Test error handling

Integration tests:
  • Test services with real database
  • Verify no DetachedInstance errors
  • Test relationship access
  • Verify data correctness

Streamlit tests:
  • Test pages load without errors
  • Verify data displays correctly
  • Test filtering and searching
  • Check error handling

Example test structure:

tests/
├── test_repositories/
│   ├── test_sala_repository.py
│   ├── test_alocacao_repository.py
│   └── ...
├── test_services/
│   ├── test_inventory_service.py
│   ├── test_allocation_service.py
│   └── ...
└── test_pages/
    ├── test_admin_rooms_page.py
    ├── test_admin_allocations_page.py
    └── ...
"""

# ============================================================================
# PHASE 5: CLEANUP (After everything works)
# ============================================================================

"""
Once all services are refactored and tested:

1. Remove old service implementations (optional)
   • Keep both versions initially for safety
   • After 1-2 weeks in production, remove old code

2. Update imports everywhere
   • from src.services.inventory_service → _refactored
   • Or rename _refactored to the original name

3. Delete old service files
   • src/services/inventory_service_old.py
   • src/services/allocation_service_old.py
   • etc.

4. Update documentation
   • Update architecture docs
   • Add repository pattern explanation
   • Add DTO usage guide
"""

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
Problem: "ImportError: cannot import name 'SalaRepository'"
Solution: Make sure src/repositories/__init__.py exists and exports it

Problem: "AttributeError: 'SalaDTO' object has no attribute 'X'"
Solution: Check that dto_to_orm() is creating all fields correctly

Problem: "Still getting DetachedInstance errors"
Solution:
  1. Make sure you're using refactored service (not old one)
  2. Check that orm_to_dto() is called inside session
  3. Verify relationships are being accessed inside orm_to_dto()

Problem: "Performance is slower"
Solution:
  1. Add @st.cache_data to Streamlit functions
  2. Use eager loading in repositories
  3. Profile queries to find bottlenecks
"""

# ============================================================================
# BENEFITS AFTER REFACTORING
# ============================================================================

"""
✓ NO MORE DETACHED INSTANCE ERRORS
  All data is DTOs, never ORM objects outside repository

✓ BETTER PERFORMANCE
  Eager loading prevents N+1 queries
  Streamlit caching eliminates repeated queries

✓ CLEANER CODE
  Clear separation of concerns
  Easy to understand data flow

✓ EASIER TESTING
  Mock repositories
  No database needed for unit tests

✓ READY FOR FEATURES
  Can easily add caching layer
  Can add authentication/authorization
  Can build REST API

✓ FUTURE-PROOF
  Easy to switch databases (e.g., PostgreSQL)
  Easy to add search/index layer
  Easy to add logging/monitoring
"""

# ============================================================================
# SUMMARY
# ============================================================================

"""
Timeline:
  Phase 1 (Setup): 1-2 hours
  Phase 2A (Refactor InventoryService): 2-3 hours
  Phase 2B (Update Pages): 1-2 hours
  Phase 3 (Other Services): 6-10 hours
  Phase 4 (Testing): 4-6 hours
  Phase 5 (Cleanup): 1 hour

  TOTAL: 15-24 hours (~3-4 days)

Key Files Created:
  • src/repositories/base.py (BASE)
  • src/repositories/sala.py (EXAMPLE)
  • src/schemas/sala.py (EXAMPLE DTOs)
  • src/services/inventory_service_refactored.py (EXAMPLE)

Next Steps:
  1. Review this guide
  2. Start with Phase 1 (Setup)
  3. Create base repository (DONE)
  4. Create first set of DTOs (DONE)
  5. Create first repository (DONE)
  6. Create refactored service (DONE)
  7. Test and deploy
  8. Repeat for other services

Questions? Review the code files for detailed examples!
"""
