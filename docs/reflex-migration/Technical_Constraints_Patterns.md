# Technical Constraints & Patterns
# Sistema de Ensalamento FUP/UnB - Reflex Implementation

**Version:** 1.0 (Reflex Migration)
**Date:** November 14, 2025

---

## Executive Summary

This document outlines the technical constraints and implementation patterns specific to **Reflex v0.8.19** for the Sistema de Ensalamento FUP/UnB migration. It provides concrete guidelines for following established Reflex development patterns while ensuring the complex business logic of room allocation and reservation systems is properly implemented.

## Framework-Specific Constraints

### Reflex v0.8.19 Technical Limitations

* **State Size Limits:** Large datasets (>10K items) should use pagination over virtual scrolling
* **LocalStorage Limits:** ~5-10MB total storage across all state variables
* **Concurrent Operations:** Maximum 3-5 simultaneous async operations recommended
* **Bundle Size:** Target <5MB uncompressed for production builds
* **WebSocket Connections:** Automatic management - no manual connection handling needed
* **Browser Support:** Modern browsers with ES2020+ support required

### Database Constraints (SQLite3 Preservation)

* **Connection Pooling:** Single-writer limitation maintained
* **Transaction Scope:** Keep transactions short (<30 seconds) for web UX
* **Concurrent Access:** File-level locking affects simultaneous reservation attempts
* **Migration Pattern:** Schema changes require application restart
* **Backup Strategy:** File-based backup (copy `.db` file) during low-usage windows

---

## State Management Patterns (MANDATORY)

### Defensive Mutation Pattern (CRITICAL - PER AGENTS GUIDE)

**Rule:** Every mutable container assignment must be followed by defensive reassignment to trigger reactivity.

```python
class RoomState(rx.State):
    rooms: list[dict] = []

    def add_room(self, room_data: dict):
        """✅ CORRECT: Defensive reassignment pattern"""
        self.rooms.append(room_data)
        self.rooms = list(self.rooms)  # Triggers UI reactivity

    def remove_room(self, room_id: int):
        """✅ CORRECT: Defensive reassignment pattern"""
        self.rooms = [r for r in self.rooms if r["id"] != room_id]  # Direct reassignment

    def update_room_capacity(self, room_id: int, new_capacity: int):
        """✅ CORRECT: Multiple operations with final defensive reassignment"""
        for room in self.rooms:
            if room["id"] == room_id:
                room["capacity"] = new_capacity
                break
        self.rooms = list(self.rooms)  # Single reassignment at end

    # ❌ WRONG - May not trigger UI updates
    # def wrong_add_room(self, room_data: dict):
    #     self.rooms.append(room_data)  # No reassignment - UI won't update!

    # ❌ WRONG - Multiple reassignments = performance issues
    # def wrong_clear_rooms(self):
    #     self.rooms = []  # This alone is fine, but unnecessary if followed by more operations
    #     self.rooms = list(self.rooms)  # Redundant reassignment
```

### Loading State Pattern (ESSENTIAL >100ms operations)

**Rule:** All async operations must have loading states and prevent concurrent execution.

```python
class AllocationState(rx.State):
    # State variables
    loading_allocation: bool = False
    allocation_result: dict | None = None
    progress_percentage: int = 0

    async def run_allocation(self, semester_id: int):
        """✅ CORRECT: Full loading state pattern with yield updates"""

        # Prevent concurrent operations
        if self.loading_allocation:
            yield rx.toast.info("Allocation already running...")
            return

        # Initialize loading state
        self.loading_allocation = True
        self.progress_percentage = 0
        self.error = ""
        yield  # Update UI immediately

        try:
            # Progress updates with yield
            self.progress_percentage = 10
            yield rx.toast.info("Starting allocation process...")

            # Execute operation
            result = await AllocationService.execute_allocation(semester_id)

            self.progress_percentage = 50
            yield

            # Store result
            self.allocation_result = result

            self.progress_percentage = 100
            yield rx.toast.success(
                f"Allocation completed: {result['allocations_completed']} placements"
            )

        except Exception as e:
            self.error = str(e)
            yield rx.toast.error(f"Allocation failed: {e}")

        finally:
            # ALWAYS reset loading state in finally
            self.loading_allocation = False

    # ❌ WRONG - Missing loading state or no protection against concurrent calls
    # async def wrong_allocation(self, semester_id: int):
    #     self.loading_allocation = True  # No yield - UI doesn't update
    #     result = await AllocationService.execute_allocation(semester_id)
    #     self.loading_allocation = False  # Error handling missing
```

### Computed Properties Pattern (PERFORMANCE CRITICAL)

**Rule:** Use `@rx.var` for derived data instead of storing redundant values.

```python
class DashboardState(rx.State):
    # Source data only (single source of truth)
    allocation_data: list[dict] = []

    # ✅ CORRECT - Computed properties that auto-update
    @rx.var
    def total_allocations(self) -> int:
        """Auto-computed when allocation_data changes"""
        return len(self.allocation_data)

    @rx.var
    def allocated_percentage(self) -> float:
        """Expensive calculation only runs when needed"""
        if not self.allocation_data:
            return 0.0
        allocated = sum(1 for item in self.allocation_data if item.get("allocated"))
        return (allocated / len(self.allocation_data)) * 100

    @rx.var
    def utilization_by_building(self) -> dict[str, dict]:
        """Complex aggregation computed automatically"""
        building_stats = {}
        for item in self.allocation_data:
            building = item.get("building", "Unknown")
            if building not in building_stats:
                building_stats[building] = {"total": 0, "allocated": 0}

            building_stats[building]["total"] += 1
            if item.get("allocated"):
                building_stats[building]["allocated"] += 1

        return building_stats

    @rx.var
    def top_utilized_rooms(self) -> list[dict]:
        """Sorted list computed from source data"""
        return sorted(
            self.allocation_data,
            key=lambda x: x.get("utilization_rate", 0),
            reverse=True
        )[:10]

    # ❌ WRONG - Don't store derived data manually
    # total_allocations: int = 0  # Redundant!
    # allocated_percentage: float = 0.0  # Redundant!

    # ❌ WRONG - Manual updates lead to inconsistency
    # def update_totals(self):
    #     self.total_allocations = len(self.allocation_data)  # Error-prone!
```

### Async Operation Patterns (CRITICAL)

**Rule:** All blocking I/O must use `asyncio.to_thread()` with proper error handling.

```python
class DatabaseState(rx.State):
    # ✅ CORRECT - Proper async wrapping
    async def load_rooms_async(self, building_id: int) -> list[dict]:
        """Proper async pattern for database operations"""
        try:
            rooms = await asyncio.to_thread(
                RoomService.get_rooms_by_building_sync,
                building_id
            )
            return rooms
        except Exception as e:
            logging.error(f"Failed to load rooms: {e}")
            return []

    # ✅ CORRECT - Complex async operation with progress
    async def import_semester_data(self, semester_id: int):
        """Async operation with progress updates and error handling"""
        self.loading_import = True
        self.import_progress = 0
        yield

        try:
            # Step 1: Fetch external data
            self.import_progress = 20
            yield rx.toast.info("Fetching data from Sistema de Oferta...")

            external_data = await self._fetch_external_data(semester_id)

            # Step 2: Process data
            self.import_progress = 60
            yield rx.toast.info("Processing course data...")

            processed_data = await asyncio.to_thread(
                self._process_course_data,
                external_data
            )

            # Step 3: Save to database
            self.import_progress = 90
            yield rx.toast.info("Saving to database...")

            await asyncio.to_thread(
                SemesterService.save_semester_data,
                semester_id, processed_data
            )

            self.import_progress = 100
            yield rx.toast.success("Import completed successfully!")

        except Exception as e:
            yield rx.toast.error(f"Import failed: {e}")
            logging.error("Import error", exc_info=True)

        finally:
            self.loading_import = False

    # ❌ WRONG - Blocking operations in async context
    # async def wrong_load_rooms(self, building_id: int):
    #     return RoomService.get_rooms_by_building_sync(building_id)  # BLOCKS!
```

---

## Component Architecture Patterns

### Function-Based Components (MANDATORY)

**Rule:** All UI components must be pure functions returning `rx.Component`.

```python
# ✅ CORRECT - Pure function components
def room_card(room: dict) -> rx.Component:
    """Room display component"""
    return rx.card(
        rx.vstack(
            rx.heading(room["name"], size="md"),
            rx.text(f"Capacity: {room['capacity']}"),
            rx.badge(room["building"], variant="soft"),
            spacing="2",
            align="start"
        ),
        width="100%"
    )

def room_grid(rooms: list[dict]) -> rx.Component:
    """Grid of room cards"""
    if not rooms:
        return rx.text("No rooms found", color="gray")

    return rx.grid(
        *[room_card(room) for room in rooms],
        columns={"base": "1", "md": "2", "lg": "3"},
        spacing="4",
        width="100%"
    )

# ❌ WRONG - Class-based or impure components
# class RoomCard(rx.Component):  # Not how Reflex works!
#     pass

# ❌ WRONG - Side effects in components
# def bad_room_card(room: dict) -> rx.Component:
#     GlobalState.some_counter += 1  # Side effect in render!
#     return rx.card(...)
```

### Conditional Rendering Pattern

**Rule:** Use `rx.cond` for conditional rendering, not Python if/else.

```python
# ✅ CORRECT - Declarative conditional rendering
def reservation_status(status: str) -> rx.Component:
    return rx.cond(
        status == "confirmed",
        rx.badge("Confirmed", color_scheme="green"),
        rx.cond(
            status == "pending",
            rx.badge("Pending", color_scheme="yellow"),
            rx.cond(
                status == "cancelled",
                rx.badge("Cancelled", color_scheme="red"),
                rx.badge("Unknown", color_scheme="gray")
            )
        )
    )

# ❌ WRONG - Imperative conditionals in component
# def wrong_reservation_status(status: str) -> rx.Component:
#     if status == "confirmed":  # Don't do this in components!
#         return rx.badge("Confirmed", color_scheme="green")
#     elif status == "pending":
#         return rx.badge("Pending", color_scheme="yellow")
#     # ... more if/else
```

### Component Composition Pattern

**Rule:** Break complex components into smaller, reusable pieces.

```python
def allocation_progress_bar(progress: int, label: str) -> rx.Component:
    """Progress bar component"""
    return rx.vstack(
        rx.hstack(
            rx.text(label, size="sm"),
            rx.text(f"{progress}%", size="sm", font_weight="bold"),
            justify="between",
            width="100%"
        ),
        rx.progress(value=progress, max=100, width="100%"),
        spacing="1",
        width="100%"
    )

def allocation_status_card(allocation_data: dict) -> rx.Component:
    """Complex status card using composition"""
    return rx.card(
        rx.vstack(
            rx.heading("Allocation Status", size="lg"),

            # Use smaller components
            allocation_progress_bar(
                allocation_data.get("progress", 0),
                "Overall Progress"
            ),

            rx.divider(),

            # Stats grid
            rx.grid(
                rx.stat(
                    rx.stat_label("Total Classes"),
                    rx.stat_number(allocation_data.get("total_classes", 0))
                ),
                rx.stat(
                    rx.stat_label("Allocated"),
                    rx.stat_number(allocation_data.get("allocated", 0))
                ),
                rx.stat(
                    rx.stat_label("Conflicts"),
                    rx.stat_number(
                        allocation_data.get("conflicts", 0),
                        color="red"
                    )
                ),
                columns="3",
                spacing="4"
            ),

            spacing="4",
            align="start"
        ),
        width="100%"
    )
```

---

## Data Flow Constraints

### State Scoping Rules (CRITICAL)

**Global State (shared across app):**
- Authentication status and user data
- Current semester selection
- Navigation state (current page)
- Global loading states
- Persistent preferences

**Local State (page/component specific):**
- Form inputs and validation errors
- Modal/dialog states
- Temporary filters and search
- Component-specific loading states
- Progress indicators for local operations

```python
# ✅ CORRECT - Proper state scoping
class AuthState(rx.State):  # Global - shared everywhere
    username: str = rx.LocalStorage(default="")
    is_logged_in: bool = False
    role: str = "user"

class RoomFilterState(rx.State):  # Global - used across room views
    search_query: str = ""
    building_filter: str = "all"
    capacity_min: int = 0

def room_search_page():
    # Local state for this page only
    class SearchFormState(rx.State):
        temp_query: str = ""
        is_searching: bool = False

    # Combination of global and local state
    # ...
```

### Persistence Strategy

**LocalStorage (survives browser refresh):**
- User authentication tokens
- UI preferences (theme, sidebar state)
- Form auto-save data
- Cached reference data

**SessionStorage (resets on tab close):**
- Working form data (drafts)
- Temporary navigation state
- Sensitive operational data

```python
class PersistenceExample(rx.State):
    # ✅ CORRECT - Appropriate persistence levels

    # Survives refresh - user settings
    theme: str = rx.LocalStorage(default="light")
    sidebar_collapsed: bool = rx.LocalStorage(default=False)

    # Survives refresh - working data
    current_form_draft: dict = rx.LocalStorage(default_factory=dict)

    # Session only - sensitive data
    temp_auth_token: str = rx.SessionStorage(default="")
    working_allocation_data: dict = rx.SessionStorage(default_factory=dict)

    # No persistence - temporary UI state
    loading: bool = False
    error_message: str = ""
```

---

## Error Handling Patterns (MANDATORY)

### Toast Notification Pattern

**Rule:** All operations must provide user feedback via toast notifications.

```python
class ReservationState(rx.State):
    async def create_reservation(self, reservation_data: dict):
        """Full error handling with user feedback"""
        try:
            # Validate input
            if not reservation_data.get("title"):
                yield rx.toast.error("Please provide a reservation title")
                return

            # Check conflicts
            conflicts = await self._check_conflicts(reservation_data)
            if conflicts:
                yield rx.toast.error("Time conflict detected. Please choose different time.")
                return

            # Create reservation
            result = await ReservationService.create_reservation(reservation_data)

            if result["success"]:
                yield rx.toast.success("Reservation created successfully!")

                # Update local state
                self.reservations.append(result["reservation"])
                self.reservations = list(self.reservations)

            else:
                yield rx.toast.error(f"Failed to create reservation: {result.get('error', 'Unknown error')}")

        except Exception as e:
            yield rx.toast.error("An unexpected error occurred. Please try again.")
            logging.error("Reservation creation failed", exc_info=True)

    def _check_conflicts(self, data: dict) -> list[dict]:
        """Validate against existing reservations"""
        # Implementation here
        return []
```

### Error Recovery Pattern

```python
class RobustOperationState(rx.State):
    retry_count: int = 0
    max_retries: int = 3

    async def robust_allocation_operation(self, semester_id: int):
        """Operation with retry capability"""

        while self.retry_count < self.max_retries:
            try:
                result = await AllocationService.execute_allocation(semester_id)

                if result["success"]:
                    yield rx.toast.success("Operation completed!")
                    self.retry_count = 0  # Reset on success
                    return result

                else:
                    # Service-level error
                    yield rx.toast.error(f"Operation failed: {result.get('error', 'Unknown error')}")

                    # Check if retryable
                    if result.get("retryable", False):
                        await self._offer_retry()
                    break

            except Exception as e:
                self.retry_count += 1

                if self.retry_count < self.max_retries:
                    yield rx.toast.warning(f"Attempt {self.retry_count} failed. Retrying...")
                    await asyncio.sleep(2 ** self.retry_count)  # Exponential backoff
                else:
                    yield rx.toast.error("Operation failed after all retry attempts")
                    break

    async def _offer_retry(self):
        """Offer user the chance to retry"""
        # In practice, this might trigger a dialog
        yield rx.toast.info("Would you like to retry the operation?")
```

---

## Performance Constraints & Optimizations

### List Virtualization (Large Datasets)

**Rule:** Lists >100 items must use pagination to prevent UI lag.

```python
class PaginatedRoomList(rx.State):
    all_rooms: list[dict] = []
    page: int = 1
    page_size: int = 20

    @rx.var
    def total_pages(self) -> int:
        return (len(self.all_rooms) + self.page_size - 1) // self.page_size

    @rx.var
    def current_page_rooms(self) -> list[dict]:
        """Only return rooms for current page"""
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        return self.all_rooms[start:end]

    def next_page(self):
        if self.page < self.total_pages:
            self.page += 1

    def prev_page(self):
        if self.page > 1:
            self.page -= 1

def paginated_room_list() -> rx.Component:
    """UI that only renders 20 rooms at a time"""
    return rx.vstack(
        # Header with pagination controls
        rx.hstack(
            rx.button("Previous", on_click=PaginatedRoomList.prev_page),
            rx.text(f"Page {PaginatedRoomList.page} of {PaginatedRoomList.total_pages}"),
            rx.button("Next", on_click=PaginatedRoomList.next_page),
            spacing="2"
        ),

        # Render only current page's rooms
        rx.foreach(
            PaginatedRoomList.current_page_rooms,
            lambda room: room_card(room)
        ),

        spacing="4"
    )
```

### Debounced Search Pattern

**Rule:** Text input for search must be debounced to prevent excessive operations.

```python
class SearchState(rx.State):
    search_query: str = ""
    search_results: list[dict] = []
    is_searching: bool = False
    _search_task: asyncio.Task | None = None

    def update_search(self, query: str):
        """Called on every keystroke - debounces actual search"""
        self.search_query = query

        # Cancel any pending search
        if self._search_task and not self._search_task.done():
            self._search_task.cancel()

        # Schedule new search with 300ms delay
        self._search_task = asyncio.create_task(self._debounced_search())

    async def _debounced_search(self):
        """Actual search operation with debounce delay"""
        try:
            # Wait for user to stop typing
            await asyncio.sleep(0.3)

            # Only search if we still have a query
            if not self.search_query.strip():
                self.search_results = []
                return

            self.is_searching = True

            # Perform search
            results = await asyncio.to_thread(
                self._search_database_sync,
                self.search_query.strip()
            )
            self.search_results = results

        except asyncio.CancelledError:
            # Search was cancelled - ignore
            pass
        except Exception as e:
            self.error = f"Search failed: {e}"
        finally:
            self.is_searching = False

def search_input() -> rx.Component:
    return rx.vstack(
        rx.input(
            placeholder="Search rooms...",
            value=SearchState.search_query,
            on_change=SearchState.update_search,  # Triggers on every keystroke
            width="100%"
        ),

        rx.cond(
            SearchState.is_searching,
            rx.text("Searching...", size="sm", color="gray"),
            rx.text(f"{len(SearchState.search_results)} results found", size="sm", color="gray")
        ),

        spacing="2",
        width="100%"
    )
```

---

## Database Interaction Constraints

### Transaction Scope Limitations

**Rule:** Database operations must complete within reasonable time limits for web UX.

```python
class DatabaseConstraints:
    # Maximum time for a single operation (seconds)
    MAX_OPERATION_TIME = 30

    # Maximum records to process in UI thread
    MAX_UI_RECORDS = 1000

    # Database connection pooling (SQLite limitations)
    MAX_CONCURRENT_WRITERS = 1

# ✅ CORRECT - Proper database operation scoping
async def safe_database_operation(operation_func, *args, **kwargs):
    """Wrapper for database operations with timeout and error handling"""
    try:
        # Execute with timeout to prevent hanging UI
        result = await asyncio.wait_for(
            asyncio.to_thread(operation_func, *args, **kwargs),
            timeout=DatabaseConstraints.MAX_OPERATION_TIME
        )
        return result

    except asyncio.TimeoutError:
        raise Exception("Database operation timed out")
    except Exception as e:
        logging.error(f"Database operation failed: {e}")
        raise

# Usage in state
class RoomState(rx.State):
    async def load_rooms_with_constraint(self):
        """Safe database operation with proper constraints"""
        try:
            rooms = await safe_database_operation(
                RoomService.get_all_rooms_sync,
                limit=DatabaseConstraints.MAX_UI_RECORDS
            )
            self.rooms = rooms
            self.rooms = list(self.rooms)  # Defensive reassignment

        except Exception as e:
            yield rx.toast.error(f"Failed to load rooms: {e}")
```

---

## Testing Constraints & Patterns

### Unit Testing State Methods

```python
# tests/test_allocation_state.py
import pytest
from core.states.allocation_state import AllocationState

@pytest.mark.asyncio
async def test_allocation_success():
    """Test successful allocation flow"""
    state = AllocationState()

    # Mock the service
    with patch('core.services.AllocationService') as mock_service:
        mock_service.execute_allocation.return_value = {
            "success": True,
            "allocations_completed": 42
        }

        # Execute the method
        await state.run_allocation(20251)

        # Verify state changes
        assert state.allocation_result is not None
        assert state.allocation_result["allocations_completed"] == 42
        assert not state.loading_allocation

@pytest.mark.asyncio
async def test_allocation_failure():
    """Test allocation failure handling"""
    state = AllocationState()

    with patch('core.services.AllocationService') as mock_service:
        mock_service.execute_allocation.side_effect = Exception("Network error")

        # Method should handle exception gracefully
        await state.run_allocation(20251)

        # Verify error state
        assert "Network error" in state.error
        assert not state.loading_allocation
```

### Component Testing Pattern

```python
# tests/test_components.py
import pytest
from core.components.room_card import room_card

def test_room_card_renders():
    """Test room card component renders correctly"""
    room = {"name": "A1-01", "capacity": 30, "building": "Main"}

    component = room_card(room)

    # Reflex components are Python objects that can be inspected
    assert component is not None
    # Further assertions based on component structure

def test_room_card_with_missing_data():
    """Test component handles missing data gracefully"""
    incomplete_room = {"name": "A1-01"}  # Missing capacity and building

    # Should not crash, should handle gracefully
    component = room_card(incomplete_room)
    assert component is not None
```

---

## Migration Implementation Rules

### Phase 1: Infrastructure Setup
- [ ] Create `core/` directory structure
- [ ] Set up state class hierarchy
- [ ] Configure LocalStorage/SessionStorage patterns
- [ ] Implement base service layer wrappers
- [ ] Create DTO structures

### Phase 2: Core Business Logic Migration
- [ ] Migrate allocation engine with async wrappers
- [ ] Implement reservation system with conflict detection
- [ ] Create reactive forms for CRUD operations
- [ ] Set up computed properties for derived data

### Phase 3: UI Component Development
- [ ] Implement main layout with sidebar navigation
- [ ] Create dashboard with reactive statistics
- [ ] Build allocation interface with progress indicators
- [ ] Develop reservation calendar components

### Phase 4: Integration & Testing
- [ ] Connect all state management layers
- [ ] Implement proper error boundaries
- [ ] Add comprehensive loading states
- [ ] Configure production deployments

### Phase 5: Optimization & Production
- [ ] Implement pagination for large datasets
- [ ] Add debounced search and filtering
- [ ] Optimize bundle size and loading performance
- [ ] Implement caching strategies

These constraints and patterns ensure the Reflex migration maintains code quality, performance, and user experience while leveraging the full reactive capabilities of the framework.
