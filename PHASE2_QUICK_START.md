# Phase 2 Implementation: Quick Start Guide

**Status**: Phase 2 Part 1 ✅ COMPLETE | Part 2 🚧 READY TO START
**Date**: November 14, 2025

---

## 🎯 What You Need to Know

### What's Already Done (Nov 14, 2025)
- ✅ **AllocationService** - Complete async wrappers for allocation engine
- ✅ **ReservationService** - Complete async wrappers for event scheduling
- ✅ **RoomService** - Complete async wrappers for room inventory
- ✅ **AuthState API Fix** - Fixed `rx.LocalStorage()` syntax error
- ✅ **All imports working** - Services and states import without errors

### What Needs to Be Done Now
1. **Complete state async methods** (allocation_state.py, reservation_state.py, room_state.py)
2. **Test service integration** with Reflex dev server
3. **Create UI components** (Phase 3)

---

## 🏃 Get Started in 5 Minutes

### Step 1: Verify Everything Works
```bash
cd ensalamento-reflex

# Check all imports
python -c "
from core.states import AllocationState, ReservationState, RoomState
from core.services import AllocationService, ReservationService, RoomService
print('✅ All imports successful')
"
```

### Step 2: Understand the Service Pattern
Open `core/services/allocation_service.py` and look at this method:

```python
@staticmethod
async def execute_allocation(semester_id: int) -> Dict[str, Any]:
    """Key pattern: async wrapper for sync operation"""
    try:
        # Import legacy services
        from src.services.allocation_service import OptimizedAutonomousAllocationService
        from src.config.database import get_db_session

        def _run_allocation():
            """Synchronous operation"""
            with get_db_session() as session:
                service = OptimizedAutonomousAllocationService(session)
                return service.allocate(semester_id)

        # Execute in thread pool (non-blocking)
        result = await BaseService.execute_async(_run_allocation)
        return result
```

**Key Points**:
- `async def` - External method is async
- `def _run_allocation()` - Inner function is sync
- `await BaseService.execute_async()` - Runs sync code in thread pool
- Returns dict with `success`, `error`, and data fields

### Step 3: Complete One State Method

Open `core/states/allocation_state.py` and find the `run_autonomous_allocation()` method stub. Fill it in:

```python
async def run_autonomous_allocation(self, semester_id: int):
    """Execute autonomous allocation with Reflex patterns."""

    # Check preconditions
    if self.loading_allocation:
        yield rx.toast.info("Alocação já está em execução")
        return

    # Set loading state
    self.loading_allocation = True
    self.error = ""
    self.allocation_progress = 0
    yield  # Update UI

    try:
        # Update progress
        self.allocation_progress = 25
        yield rx.toast.info("Iniciando processo...")

        # Call service (this is the key integration point)
        result = await AllocationService.execute_allocation(semester_id)

        # Handle result
        if result.get("success"):
            self.allocation_result = result
            self.allocation_progress = 100
            yield rx.toast.success(
                f"Alocação completa: {result.get('allocations_completed')} salas"
            )
        else:
            self.error = result.get("error", "Unknown error")
            yield rx.toast.error(f"Falha: {self.error}")

    except Exception as e:
        self.error = str(e)
        yield rx.toast.error(f"Erro: {e}")

    finally:
        self.loading_allocation = False
        self.allocation_progress = 0
```

---

## 📚 File Structure Reference

```
ensalamento-reflex/
├── core/
│   ├── states/
│   │   ├── base_state.py          ✅ Base with loading/error handling
│   │   ├── auth_state.py          ✅ Auth with LocalStorage
│   │   ├── allocation_state.py    🚧 NEED: Complete methods
│   │   ├── reservation_state.py   🚧 NEED: Complete methods
│   │   ├── room_state.py          🚧 NEED: Complete methods
│   │   ├── semester_state.py      ✅ Placeholder ready
│   │   └── navigation_state.py    ✅ SPA routing ready
│   ├── services/
│   │   ├── base_service.py        ✅ execute_async() helper
│   │   ├── allocation_service.py  ✅ 5 methods ready
│   │   ├── reservation_service.py ✅ 8 methods ready
│   │   ├── room_service.py        ✅ 8 methods ready
│   │   └── __init__.py            ✅ Exports all services
│   └── components/
│       └── (Phase 3 - UI components)
├── PHASE2_SERVICE_LAYER.md        ✅ Service documentation
└── PHASE2_QUICK_START.md          ✅ This file
```

---

## 🔗 Using Services in States

### Pattern for All Operations
```python
# Always use this pattern in state methods:

async def my_operation(self):
    # 1. Set loading state
    self.loading = True
    yield

    try:
        # 2. Call service
        result = await MyService.some_operation(arg)

        # 3. Update state with result
        self.data = result.get("data")

        # 4. Show success message
        yield rx.toast.success("Done!")

    except Exception as e:
        # 5. Handle errors
        self.error = str(e)
        yield rx.toast.error(f"Error: {e}")

    finally:
        # 6. Clean up loading state
        self.loading = False
```

---

## 🧪 Quick Testing

### Test a Service Directly (in Python REPL)
```python
cd ensalamento-reflex

# python
# >>> import asyncio
# >>> from core.services import RoomService
# >>>
# >>> async def test():
# ...     rooms = await RoomService.get_all_rooms()
# ...     print(f"Found {len(rooms)} rooms")
# ...     return rooms
# >>>
# >>> result = asyncio.run(test())
```

### Test Reflex App
```bash
cd ensalamento-reflex
reflex run  # Starts dev server on http://localhost:3000
```

---

## 📋 State Methods to Complete

### AllocationState (in `allocation_state.py`)
- [ ] `run_autonomous_allocation()` - Run allocation algorithm
- [ ] `import_semester_data()` - Import courses from API
- [ ] `get_status()` - Get allocation progress

### ReservationState (in `reservation_state.py`)
- [ ] `load_reservations()` - Load list with filters
- [ ] `create_reservation()` - Create with conflict check
- [ ] `update_reservation()` - Edit existing
- [ ] `delete_reservation()` - Remove
- [ ] `update_filters()` - Apply search/filters

### RoomState (in `room_state.py`)
- [ ] `load_rooms()` - Load list with filters
- [ ] `create_room()` - Create with validation
- [ ] `update_room()` - Edit existing
- [ ] `delete_room()` - Remove
- [ ] `update_displayed_rooms()` - Handle pagination

---

## 🎯 Implementation Order (Recommended)

1. **AllocationState.run_autonomous_allocation()** - Core feature
2. **RoomState.load_rooms()** - Simpler, good warm-up
3. **ReservationState.load_reservations()** - Similar pattern
4. **ReservationState.create_reservation()** - More complex with validation
5. **Other methods** - Follow same pattern

---

## 🚀 Once You've Implemented Methods

After implementing state methods:

1. **Test in Reflex dev server**:
   ```bash
   reflex run
   ```

2. **Create simple UI components** to test state methods work

3. **Move to Phase 3**: UI component development

---

## 📖 Documentation to Reference

- **Service Details**: `ensalamento-reflex/PHASE2_SERVICE_LAYER.md`
- **Migration Guide**: `docs/reflex-migration/Migration_Roadmap.md` (section 2.1-2.3)
- **Architecture**: `docs/reflex-migration/Reflex_Architecture_Document.md`
- **Patterns**: `docs/reflex-migration/Reflex_Agents_guide.md`

---

## 💡 Common Patterns

### Loading State + Toast Feedback
```python
async def my_operation(self):
    self.loading = True
    yield
    try:
        result = await SomeService.do_something()
        if result["success"]:
            self.data = result["data"]
            yield rx.toast.success("Success!")
        else:
            yield rx.toast.error(result.get("error"))
    except Exception as e:
        yield rx.toast.error(f"Error: {e}")
    finally:
        self.loading = False
```

### Update List + Filtering
```python
async def load_items(self):
    self.items = await ItemService.get_all()
    self.apply_filters()  # Recompute filtered_items

def update_search(self, query: str):
    self.search_query = query
    self.apply_filters()

def apply_filters(self):
    # Filter logic
    filtered = self.items
    if self.search_query:
        filtered = [i for i in filtered if self.search_query in i.get("name", "")]
    self.filtered_items = list(filtered)  # Defensive reassignment
```

### CRUD with Validation
```python
async def create_item(self, data: dict):
    # Validate
    if not data.get("name"):
        yield rx.toast.error("Name required")
        return

    # Create
    result = await ItemService.create(data)

    if result["success"]:
        yield rx.toast.success("Created!")
        await self.load_items()  # Refresh
    else:
        yield rx.toast.error(result.get("error"))
```

---

## ❓ Quick Troubleshooting

| Issue                                                 | Solution                                                  |
| ----------------------------------------------------- | --------------------------------------------------------- |
| `ImportError: cannot import name 'AllocationService'` | Run from `ensalamento-reflex/` directory                  |
| Service methods not working in state                  | Make sure method is `async` and uses `await`              |
| UI not updating after yield                           | Use defensive reassignment: `self.list = list(self.list)` |
| Toast not showing                                     | Make sure to use `yield rx.toast.xxx()`                   |

---

## 📞 Need Help?

1. Check `PHASE2_SERVICE_LAYER.md` for service documentation
2. Look at `core/services/*.py` for implementation examples
3. Review `core/states/base_state.py` for state patterns
4. See `docs/reflex-migration/` for detailed architecture

---

**Ready to implement?** Start with `AllocationState.run_autonomous_allocation()` method and follow the pattern above!
