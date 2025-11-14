# Streamlit → Reflex Migration: Execution Guide

**Status**: Phase 1 ✅ Complete | Phase 2 🚧 In Progress
**Date**: November 14, 2025
**Reflex Version**: v0.8.19

---

## 📋 Executive Summary

The migration from Streamlit to Reflex has completed Phase 1 infrastructure. All core state classes, authentication, and navigation patterns are established. Phase 2 requires completing service integrations and business logic migration. This document serves as the execution guide.

---

## ✅ Phase 1: Infrastructure (COMPLETE)

### What's Done
- ✅ Directory structure (`ensalamento-reflex/core/` with states, services, components)
- ✅ Base state classes (`BaseState`, `AuthState`, `NavigationState`)
- ✅ State files created for all major features:
  - `core/states/allocation_state.py` (255 lines)
  - `core/states/reservation_state.py` (288 lines)
  - `core/states/room_state.py` (299 lines)
  - `core/states/semester_state.py` (136 lines)
- ✅ Base service infrastructure (`core/services/base_service.py`)
- ✅ Project configuration (requirements.txt, rxconfig.py, pyrightconfig.json)
- ✅ All imports validated and working

### Issues Fixed (Today)
- **AuthState LocalStorage API**: Fixed incorrect `object=` and `name=` parameters in `rx.LocalStorage()` and `rx.SessionStorage()`. Now using positional defaults only.

---

## 🚧 Phase 2: Core Business Logic (Next Priority)

### What Needs to Be Done

#### 2.1 Service Integration Layer
**File**: `core/services/allocation_service.py` (NEED TO CREATE)

```python
# Services for wrapping legacy business logic
class AllocationService(BaseService):
    """Async wrapper for allocation engine"""

    @staticmethod
    async def execute_allocation(semester_id: int) -> dict:
        """Wrap OptimizedAutonomousAllocationService.allocate()"""
        # Use asyncio.to_thread pattern from base_service.py
        pass

    @staticmethod
    async def import_semester_data(semester_id: int) -> dict:
        """Wrap OfertaApiService.import_semester()"""
        pass
```

**File**: `core/services/reservation_service.py` (NEED TO CREATE)

```python
class ReservationService(BaseService):
    """Async wrapper for reservation management"""

    @staticmethod
    async def get_all_reservations() -> list[dict]:
        """Load reservations from database"""
        pass

    @staticmethod
    async def create_reservation(data: dict) -> dict:
        """Create new reservation with validation"""
        pass

    @staticmethod
    async def check_conflicts(data: dict) -> list[dict]:
        """Check for time/room conflicts"""
        pass
```

**File**: `core/services/room_service.py` (NEED TO CREATE)

```python
class RoomService(BaseService):
    """Async wrapper for room inventory"""

    @staticmethod
    async def get_all_rooms() -> list[dict]:
        """Load rooms with available schedule info"""
        pass

    @staticmethod
    async def create_room(data: dict) -> dict:
        """Create new room"""
        pass
```

#### 2.2 DTO Models (Type-Safe Data Transfer)
**File**: `core/dtos/models.py` (NEED TO CREATE)

Define Pydantic models for:
- `AllocationResultDTO`
- `ReservationDTO`
- `RoomDTO`
- `SemesterDTO`
- `ProfessorDTO`

#### 2.3 Service Integration Points
The following existing Streamlit services need async wrappers:
1. `src/services/allocation_service.py` → Optimize allocation engine
2. `src/services/reservation_service.py` → Event scheduling
3. `src/repositories/sala.py` → Room CRUD
4. `src/repositories/reserva_esporadica.py` → Reservation CRUD
5. `src/services/setup_service.py` → Database initialization

---

## 📊 Current File Status

### ✅ Completed Files
```
ensalamento-reflex/
├── core/
│   ├── states/
│   │   ├── base_state.py ✅
│   │   ├── auth_state.py ✅ (Fixed LocalStorage API)
│   │   ├── navigation_state.py ✅
│   │   ├── allocation_state.py ✅
│   │   ├── reservation_state.py ✅
│   │   ├── room_state.py ✅
│   │   └── semester_state.py ✅
│   ├── services/
│   │   └── base_service.py ✅
│   └── ...
├── requirements.txt ✅
├── rxconfig.py ✅
└── app.py ✅ (Functional login app)
```

### 🚧 To Be Created (Phase 2)
```
ensalamento-reflex/
├── core/
│   ├── services/
│   │   ├── allocation_service.py 🚧
│   │   ├── reservation_service.py 🚧
│   │   ├── room_service.py 🚧
│   │   ├── semester_service.py 🚧
│   │   └── __init__.py 🚧
│   ├── dtos/
│   │   ├── models.py 🚧
│   │   ├── allocation.py 🚧
│   │   └── __init__.py 🚧
│   └── components/
│       ├── layout/
│       │   ├── main_layout.py 🚧
│       │   ├── sidebar.py 🚧
│       │   └── header.py 🚧
│       └── common/
│           ├── loading_spinner.py 🚧
│           └── toast_notifications.py 🚧
└── pages/
    ├── allocation_page.py 🚧
    ├── reservations_page.py 🚧
    ├── rooms_page.py 🚧
    └── dashboard_page.py 🚧
```

---

## 🔧 Implementation Checklist: Phase 2

### Step 1: Create Service Wrapper Layer
- [ ] Create `core/services/allocation_service.py` with async wrappers
- [ ] Create `core/services/reservation_service.py` with async wrappers
- [ ] Create `core/services/room_service.py` with async wrappers
- [ ] Create `core/services/semester_service.py` with async wrappers
- [ ] Test all service imports and basic functionality
- [ ] Verify async/to_thread pattern works with legacy `src/` services

### Step 2: Create DTO Models
- [ ] Define all data transfer objects in `core/dtos/`
- [ ] Map from legacy DTOs/schemas to new format
- [ ] Add validation rules for each DTO
- [ ] Generate type hints for IDE support

### Step 3: Complete State Method Implementations
For each state class (`allocation_state.py`, `reservation_state.py`, `room_state.py`):
- [ ] Implement all async methods in the state classes
- [ ] Add proper error handling with `rx.toast` feedback
- [ ] Implement defensive mutation patterns (`self.state = list(self.state)`)
- [ ] Test computed properties (`@rx.var`) render correctly

### Step 4: Layout Components
- [ ] Create `main_layout.py` (header, sidebar, content area)
- [ ] Create `sidebar.py` (navigation menu)
- [ ] Create `header.py` (breadcrumbs, user menu)
- [ ] Create loading and error boundary components

### Step 5: Integration Testing
- [ ] Test allocation engine performance with async wrapper
- [ ] Verify database CRUD operations work
- [ ] Test state mutations trigger UI updates
- [ ] Verify LocalStorage persistence works across page refreshes

### Step 6: Create Feature Pages (Phase 3 prep)
- [ ] Allocation page with progress tracking
- [ ] Reservations page with CRUD operations
- [ ] Rooms inventory page with filters
- [ ] Dashboard with statistics

---

## 🔗 Key Integration Points

### Database Access Pattern
```python
# All legacy services imported in Reflex context
from src.config.database import get_db_session
from src.repositories.sala import SalaRepository

# Wrapped in async with to_thread
async def get_rooms():
    def _fetch():
        with get_db_session() as session:
            repo = SalaRepository(session)
            return [
                {
                    "id": s.id,
                    "name": s.nome,
                    "capacity": s.capacidade,
                }
                for s in repo.get_all()
            ]

    result = await asyncio.to_thread(_fetch)
    return result
```

### State Method Pattern
```python
# In allocation_state.py
async def run_autonomous_allocation(self, semester_id: int):
    """Example of proper state method pattern"""
    # 1. Check preconditions
    if self.loading_allocation:
        yield rx.toast.info("Already running")
        return

    # 2. Set loading state
    self.loading_allocation = True
    self.error = ""
    yield

    try:
        # 3. Execute async operation
        result = await AllocationService.execute_allocation(semester_id)

        # 4. Update state with results
        self.allocation_result = result
        self.allocation_progress = 100
        yield rx.toast.success("Done!")

    except Exception as e:
        self.error = str(e)
        yield rx.toast.error(f"Failed: {e}")

    finally:
        # 5. Clean up
        self.loading_allocation = False
```

---

## 📝 Documentation References

For implementation details, refer to:
1. **Migration Roadmap**: `/docs/reflex-migration/Migration_Roadmap.md` (phases 2-6)
2. **Architecture Document**: `/docs/reflex-migration/Reflex_Architecture_Document.md`
3. **Reflex Agents Guide**: `/docs/reflex-migration/Reflex_Agents_guide.md`
4. **Technical Constraints**: `/docs/reflex-migration/Technical_Constraints_Patterns.md`
5. **API Specifications**: `/docs/reflex-migration/API_Interface_Specifications.md`

---

## 🧪 Testing Strategy

### Unit Tests (Phase 2)
```bash
# Create tests for service wrappers
tests/
├── test_allocation_service.py
├── test_reservation_service.py
├── test_room_service.py
└── test_states.py
```

### Integration Tests (Phase 4)
```bash
# Full workflow tests
pytest tests/integration/ -v
```

---

## 🚀 Quick Start: Next Steps

### Immediate Actions (Next Session)
1. **Create service wrappers** (`core/services/*.py`)
   ```bash
   cd ensalamento-reflex
   touch core/services/{allocation,reservation,room,semester}_service.py
   ```

2. **Implement AllocationService** as template
   - Follow `BaseService.execute_async()` pattern
   - Wrap `src/services/allocation_service.py` functions
   - Test with simple allocation request

3. **Test service integration**
   ```bash
   cd ensalamento-reflex
   python -c "from core.services import AllocationService; print('✅ Works')"
   ```

4. **Implement state methods** in `allocation_state.py`
   - Complete `run_autonomous_allocation()` method
   - Add progress tracking
   - Test with Reflex dev server

### Week 3-4 Goals
- Complete all service wrappers
- Implement all state methods
- Create layout and basic components
- Validate business logic preservation

---

## 📞 Support & Reference

**Issues Encountered & Solutions**:
1. **LocalStorage API Error**: Fixed `rx.LocalStorage(object=...)` → `rx.LocalStorage(...)`
2. **Import failures**: All core states now import successfully

**Performance Targets**:
- Allocation: <10 minutes (same as Streamlit)
- Queries: <3 seconds
- Local interactions: <100ms

**Database Strategy**:
- Reflex uses isolated SQLite during dev
- Can share same DB file with Streamlit for testing
- Zero schema changes required

---

## 📅 Timeline

- ✅ **Phase 1** (Nov 14): Infrastructure ← COMPLETE
- 🚧 **Phase 2** (Nov 15-21): Core Business Logic ← STARTING
- ⏳ **Phase 3** (Nov 22-28): UI Components
- ⏳ **Phase 4** (Nov 29-Dec 5): Integration & Testing
- ⏳ **Phase 5** (Dec 6-12): Performance Optimization
- ⏳ **Phase 6** (Dec 13-19): Production Deployment

---

**Last Updated**: November 14, 2025
**Status**: Ready for Phase 2 Implementation
