# Detailed Migration Roadmap
# Sistema de Ensalamento FUP/UnB - Streamlit to Reflex Conversion

**Version:** 1.0 (Detailed Implementation Guide)
**Date:** November 14, 2025

---

## Executive Summary

This migration roadmap provides a detailed, step-by-step implementation plan for converting the **Sistema de Ensalamento FUP/UnB** from Streamlit to Reflex v0.8.19. The roadmap is structured in 6 phases with specific deliverables, ensuring the complex business logic is preserved while modernizing to a reactive architecture.

## Migration Overview

### **🗄️ Database Architecture: SQLite3 Preserved**
**Critical Decision:** All migration work preserves the existing **SQLite3 database architecture**. The Reflex implementation uses the exact same:
- Database file: `./ensalamento.db`
- Schema structure: No changes to existing tables (see: `/docs/schema.sql`)
- Connection patterns: Single-writer SQLite constraints maintained
- Data integrity: All existing business logic preserved

**Migration Promise:** Your database remains untouched. Both Streamlit and Reflex applications read/write to exactly the same SQLite3 database (db file can be copied to reflex directory if required).

### Current Architecture → Target Architecture

| Aspect               | Streamlit (Current)                               | Reflex (Target)                                            |
| -------------------- | ------------------------------------------------- | ---------------------------------------------------------- |
| **UI Pattern**       | Multi-page (`pages/`) with `st.rerun()`           | Single-page with state-based routing                       |
| **State Management** | `st.session_state` + custom feedback              | Centralized `rx.State` classes with defensive reassignment |
| **Data Flow**        | Synchronous operations with blocking calls        | Async operations with `asyncio.to_thread`                  |
| **Authentication**   | `streamlit-authenticator`                         | LocalStorage-based persistent auth                         |
| **User Feedback**    | `st.success()`/`st.error()` disappearing on rerun | Toast notifications with yield-based updates               |
| **Business Logic**   | Direct service calls in pages                     | Wrapped async service calls in state methods               |
| **File Structure**   | Flat page structure                               | Hierarchical component/state/service architecture          |
| **UI Language**      | Portuguese (Brazil)                               | Portuguese (Brazil)                                        |

### Success Criteria

- ✅ **Business Logic Preservation:** Allocation engine, conflict detection, and scoring algorithms work identically
- ✅ **Feature Parity:** All 9 pages functionality migrated with enhanced UX
- ✅ **Performance:** <100ms local interactions, <3s queries, <10min allocations
- ✅ **Code Quality:** Follows Reflex Agents Guide patterns (defensive mutation, computed vars, loading states)
- ✅ **User Experience:** Real-time reactive UI with proper feedback
- ✅ **Maintainability:** Clean separation of concerns with testable components

---

## Phase 1: Infrastructure Setup (Week 1-2)

### Objective
Establish Reflex project structure and core infrastructure following established patterns.

### Deliverables

#### 1.1 Project Structure Setup

```bash
# Create new directory structure
ensalamento-reflex/
├── ensalamento_reflex/
│   ├── __init__.py
│   └── ensalamento_reflex.py  # Main app file
├── core/
│   ├── __init__.py
│   ├── states/               # Reflex state classes
│   │   ├── __init__.py
│   │   ├── auth_state.py
│   │   ├── navigation_state.py
│   │   └── base_state.py
│   ├── components/           # Reusable UI components
│   │   ├── __init__.py
│   │   ├── layout/
│   │   └── common/
│   ├── services/             # Async service wrappers
│   │   ├── __init__.py
│   │   └── integration/
│   ├── dtos/                 # Type-safe data transfer
│   ├── utils/                # Helper utilities
│   └── integrations/         # External API clients
├── assets/                   # Static files
├── tests/                    # Test suite
├── pyrightconfig.json        # Type checking
└── requirements.txt          # Updated dependencies
```

**Implementation Steps:**
1. Create directory structure above
2. Set up `pyproject.toml` with Reflex dependencies
3. Configure `.env` for development
4. Initialize basic Reflex app structure

#### 1.2 Base Infrastructure Classes

```python
# core/states/base_state.py
import reflex as rx
from typing import Any, Optional

class BaseState(rx.State):
    """Shared base functionality for all Reflex states"""

    # Common error and loading handling
    loading: bool = False
    error: str = ""
    success_message: str = ""

    def set_error(self, message: str):
        """Set error state (resets loading and success)"""
        self.error = message
        self.loading = False
        self.success_message = ""

    def set_success(self, message: str):
        """Set success state (resets error)"""
        self.success_message = message
        self.error = ""

    async def handle_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Generic async operation handler with loading states"""
        if self.loading:
            return rx.toast.info(f"{operation_name} already in progress")

        self.loading = True
        self.error = ""
        yield

        try:
            result = await operation_func(*args, **kwargs)
            yield rx.toast.success(f"{operation_name} completed successfully")
            return result
        except Exception as e:
            error_msg = f"{operation_name} failed: {str(e)}"
            self.error = error_msg
            yield rx.toast.error(error_msg)
        finally:
            self.loading = False
```

```python
# core/services/base_service.py
import asyncio
from typing import Callable, Any, Optional
from functools import wraps

class BaseService:
    """Base class for all service wrappers with async handling"""

    @staticmethod
    async def execute_async(operation: Callable, *args, timeout: Optional[float] = 30.0, **kwargs) -> Any:
        """Execute synchronous operation asynchronously"""
        return await asyncio.wait_for(
            asyncio.to_thread(operation, *args, **kwargs),
            timeout=timeout
        )

    @staticmethod
    def with_async_wrapper(sync_method: Callable) -> Callable:
        """Decorator to add async wrapper to sync service methods"""
        @wraps(sync_method)
        async def async_wrapper(*args, **kwargs):
            return await BaseService.execute_async(sync_method, *args, **kwargs)
        return async_wrapper
```

#### 1.3 Authentication Migration

**Convert from `streamlit-authenticator` to Reflex LocalStorage pattern:**

```python
# core/states/auth_state.py
import reflex as rx
from typing import Optional

class AuthState(BaseState):
    """Authentication state with LocalStorage persistence"""

    # Persistent state - survives browser refresh
    username: str = rx.LocalStorage(default="")
    is_logged_in: bool = rx.LocalStorage(default=False, name="auth_logged_in")
    role: str = rx.LocalStorage(default="user", name="auth_role")

    # Session-only state - resets on tab close
    current_token: str = rx.SessionStorage(default="", name="auth_token")

    # Volatile state - resets on navigation
    login_loading: bool = False

    @rx.var
    def display_name(self) -> str:
        """Computed property for display name"""
        return f"@{self.username}" if self.username else "Guest"

    @rx.var
    def is_admin(self) -> bool:
        """Computed property for admin check"""
        return self.role == "admin"

    async def login(self, username: str, password: str):
        """Async login with validation and feedback"""
        # Prevent concurrent logins
        if self.login_loading:
            yield rx.toast.info("Login already in progress")
            return

        self.login_loading = True
        yield

        try:
            # Validate credentials (server-side operation)
            user_data = await self._verify_credentials(username, password)

            if user_data:
                # Set persistent state
                self.username = user_data["username"]
                self.role = user_data["role"]
                self.is_logged_in = True
                self.current_token = user_data.get("token", "")

                yield rx.redirect("/dashboard")
                yield rx.toast.success(f"Welcome, {user_data['username']}!")
            else:
                yield rx.toast.error("Invalid credentials")

        except Exception as e:
            yield rx.toast.error(f"Login failed: {e}")

        finally:
            self.login_loading = False

    def logout(self):
        """Clear all authentication state"""
        self.username = ""
        self.is_logged_in = False
        self.role = "user"
        self.current_token = ""

        return rx.redirect("/login")

    async def _verify_credentials(self, username: str, password: str) -> Optional[dict]:
        """Verify credentials against stored users"""
        # Import existing auth logic here
        # This will wrap your current authentication mechanism
        pass
```

#### 1.4 Service Layer Wrappers

**Wrap existing business logic services for async compatibility:**

```python
# core/services/allocation_service.py
from src.services.optimized_autonomous_allocation_service import OptimizedAutonomousAllocationService
from core.services.base_service import BaseService

class AllocationService(BaseService):
    """Reflex-compatible allocation service wrapper"""

    @staticmethod
    async def execute_allocation(semester_id: int, progress_callback=None) -> dict[str, Any]:
        """Execute full allocation process asynchronously"""
        service = OptimizedAutonomousAllocationService()

        # Execute in thread pool to not block event loop
        result = await AllocationService.execute_async(
            service.execute_autonomous_allocation,
            semester_id
        )

        return result

    @staticmethod
    async def get_allocation_progress(semester_id: int) -> dict[str, Any]:
        """Get allocation progress for semester"""
        service = OptimizedAutonomousAllocationService()

        progress = await AllocationService.execute_async(
            service.get_allocation_progress,
            semester_id
        )

        return progress or {"allocated": 0, "total": 0, "percentage": 0}
```

#### 1.5 Navigation System

```python
# core/states/navigation_state.py
import reflex as rx

class NavigationState(rx.State):
    """Global navigation state for SPA"""

    current_page: str = "dashboard"
    breadcrumbs: list[dict] = []

    @rx.var
    def current_page_title(self) -> str:
        """Computed page title"""
        titles = {
            "dashboard": "Dashboard",
            "inventory": "Room Management",
            "allocation": "Room Allocation",
            "professors": "Professor Management",
            "reservations": "Reservations",
            "settings": "Settings"
        }
        return titles.get(self.current_page, "Unknown")

    @rx.var
    def can_go_back(self) -> bool:
        """Check if back navigation is available"""
        return len(self.breadcrumbs) > 1

    def navigate_to(self, page: str):
        """Navigate to a page and update breadcrumbs"""
        if page != self.current_page:
            # Add current to breadcrumbs if not already there
            current_crumb = {"label": self.current_page_title, "page": self.current_page}
            if not self.breadcrumbs or self.breadcrumbs[-1]["page"] != self.current_page:
                self.breadcrumbs.append(current_crumb)

            self.current_page = page

            # Update breadcrumbs
            self.breadcrumbs = [
                {"label": "Home", "page": "dashboard"},
                {"label": self.current_page_title, "page": page}
            ]

    def go_back(self):
        """Navigate to previous page"""
        if self.can_go_back:
            self.breadcrumbs.pop()
            last_crumb = self.breadcrumbs[-1]
            self.current_page = last_crumb["page"]
```

### Phase 1 Testing
- [ ] Basic Reflex app runs without errors
- [ ] Authentication state persists across refreshes
- [ ] Navigation between pages works
- [ ] Service layer wrappers function correctly
- [ ] Base state patterns work as expected

---

## Phase 2: Core Business Logic Migration (Week 3-4)

### Objective
Migrate allocation engine, reservation system, and core business logic with proper async handling.

### Deliverables

#### 2.1 Allocation State Implementation

```python
# core/states/allocation_state.py
class AllocationState(BaseState):
    """Allocation operations state"""

    # Loading states for different operations
    loading_allocation: bool = False
    loading_import: bool = False

    # Results and data
    allocation_result: Optional[dict] = None
    last_semester_id: int = 20251

    # Progress tracking
    allocation_progress: int = 0
    import_progress: int = 0

    async def run_autonomous_allocation(self, semester_id: int):
        """Execute autonomous allocation with Reflex patterns"""
        # Prevent concurrent allocations
        if self.loading_allocation:
            yield rx.toast.info("Allocation already running")
            return

        self.loading_allocation = True
        self.allocation_progress = 0
        self.error = ""
        yield

        try:
            # Progress update 1: Starting allocation
            self.allocation_progress = 10
            yield rx.toast.info("Starting allocation process...")

            # Execute allocation
            result = await AllocationService.execute_allocation(semester_id)

            if result["success"]:
                # Progress update 2: Allocation completed
                self.allocation_progress = 90
                yield rx.toast.info("Processing results...")

                # Store result
                self.allocation_result = result
                self.last_semester_id = semester_id

                # Progress complete
                self.allocation_progress = 100
                yield rx.toast.success(
                    f"Allocation completed: {result['allocations_completed']} placements"
                )

            else:
                yield rx.toast.error(f"Allocation failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            self.error = f"Allocation error: {str(e)}"
            yield rx.toast.error(f"Allocation failed: {e}")

        finally:
            self.loading_allocation = False
            self.allocation_progress = 0

    async def import_semester_data(self, semester_id: int):
        """Import semester data with progress tracking"""
        if self.loading_import:
            yield rx.toast.info("Import already in progress")
            return

        self.loading_import = True
        self.import_progress = 0
        yield

        try:
            # Phase 1: Fetch from API
            self.import_progress = 25
            yield rx.toast.info("Fetching data from Sistema de Oferta...")

            # Import data using existing service
            from src.services.oferta_api import OfertaApiService
            import_result = await AllocationService.execute_async(
                OfertaApiService.import_semester,
                semester_id
            )

            # Phase 2: Process and save
            self.import_progress = 75
            yield rx.toast.info("Processing and saving data...")

            # Save to database
            save_result = await AllocationService.execute_async(
                lambda: SemesterService.save_imported_data(semester_id, import_result)
            )

            self.import_progress = 100
            yield rx.toast.success(f"Imported {len(import_result)} courses successfully")

            # Refresh local data
            yield SemesterState.refresh_semester_data(semester_id)

        except Exception as e:
            yield rx.toast.error(f"Import failed: {e}")
            logging.error("Semester import failed", exc_info=True)

        finally:
            self.loading_import = False
            self.import_progress = 0
```

#### 2.2 Reservation System Migration

```python
# core/states/reservation_state.py
class ReservationState(BaseState):
    """Reservation management state"""

    # Data
    reservations: list[dict] = []
    filtered_reservations: list[dict] = []

    # UI state
    selected_reservation: Optional[dict] = None
    show_create_dialog: bool = False

    # Filters
    search_query: str = ""
    status_filter: str = "all"
    date_range_start: str = ""
    date_range_end: str = ""

    @rx.var
    def total_reservations(self) -> int:
        """Computed total count"""
        return len(self.reservations)

    @rx.var
    def upcoming_reservations(self) -> list[dict]:
        """Computed upcoming reservations"""
        from datetime import datetime
        now = datetime.now()
        return [
            r for r in self.reservations
            if datetime.fromisoformat(r["data_reserva"]) > now
        ]

    @rx.var
    def todays_reservations(self) -> list[dict]:
        """Computed today's reservations"""
        today = datetime.now().date().isoformat()
        return [
            r for r in self.reservations
            if r["data_reserva"].startswith(today)
        ]

    def update_filters(self):
        """Update filtered results based on current filters"""
        filtered = self.reservations

        # Search filter
        if self.search_query:
            query = self.search_query.lower()
            filtered = [
                r for r in filtered
                if query in r.get("titulo_evento", "").lower() or
                   query in r.get("nome_solicitante", "").lower()
            ]

        # Status filter
        if self.status_filter != "all":
            filtered = [
                r for r in filtered
                if r.get("status", "Aprovada") == self.status_filter
            ]

        # Date range filters
        if self.date_range_start:
            filtered = [
                r for r in filtered
                if r["data_reserva"] >= self.date_range_start
            ]
        if self.date_range_end:
            filtered = [
                r for r in filtered
                if r["data_reserva"] <= self.date_range_end
            ]

        self.filtered_reservations = filtered
        self.filtered_reservations = list(self.filtered_reservations)  # Defensive reassignment

    async def load_reservations(self):
        """Load all reservations from database"""
        try:
            reservations = await ReservationService.get_all_reservations()
            self.reservations = reservations
            self.update_filters()  # Apply current filters

        except Exception as e:
            yield rx.toast.error(f"Failed to load reservations: {e}")

    async def create_reservation(self, reservation_data: dict):
        """Create new reservation with validation"""
        try:
            # Validate data
            if not reservation_data.get("titulo_evento"):
                yield rx.toast.error("Reservation title is required")
                return

            if not reservation_data.get("data_reserva"):
                yield rx.toast.error("Reservation date is required")
                return

            # Check conflicts
            conflicts = await ReservationService.check_conflicts(reservation_data)
            if conflicts:
                yield rx.toast.error("Time conflict detected. Please choose different time.")
                return

            # Create reservation
            result = await ReservationService.create_reservation(reservation_data)

            if result["success"]:
                yield rx.toast.success("Reservation created successfully!")

                # Refresh data
                yield self.load_reservations()

                # Close dialog
                self.show_create_dialog = False

            else:
                yield rx.toast.error(f"Failed to create reservation: {result.get('error')}")

        except Exception as e:
            yield rx.toast.error(f"Unexpected error: {e}")
            logging.error("Reservation creation failed", exc_info=True)

    def show_reservation_details(self, reservation: dict):
        """Show details for selected reservation"""
        self.selected_reservation = reservation

    def clear_selection(self):
        """Clear current selection"""
        self.selected_reservation = None
```

#### 2.3 Room Management State

```python
# core/states/room_state.py
class RoomState(BaseState):
    """Room inventory management state"""

    # Data
    rooms: list[dict] = []
    displayed_rooms: list[dict] = []  # For pagination

    # Pagination
    page: int = 1
    page_size: int = 20

    # Filters
    search_query: str = ""
    building_filter: str = "all"
    capacity_min: int = 0

    @rx.var
    def total_pages(self) -> int:
        """Computed total pages for pagination"""
        total_filtered = len(self.filtered_rooms)
        return (total_filtered + self.page_size - 1) // self.page_size

    @rx.var
    def filtered_rooms(self) -> list[dict]:
        """Computed filtered rooms based on current filters"""
        filtered = self.rooms

        # Search filter
        if self.search_query:
            query = self.search_query.lower()
            filtered = [
                room for room in filtered
                if query in room["name"].lower() or
                   query in room.get("description", "").lower()
            ]

        # Building filter
        if self.building_filter != "all":
            filtered = [
                room for room in filtered
                if room.get("building") == self.building_filter
            ]

        # Capacity filter
        if self.capacity_min > 0:
            filtered = [
                room for room in filtered
                if room.get("capacity", 0) >= self.capacity_min
            ]

        return filtered

    def update_displayed_rooms(self):
        """Update displayed rooms based on pagination"""
        filtered = self.filtered_rooms
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        self.displayed_rooms = filtered[start:end]
        self.displayed_rooms = list(self.displayed_rooms)  # Defensive reassignment

    def next_page(self):
        """Navigate to next page"""
        if self.page < self.total_pages:
            self.page += 1
            self.update_displayed_rooms()

    def prev_page(self):
        """Navigate to previous page"""
        if self.page > 1:
            self.page -= 1
            self.update_displayed_rooms()

    def apply_filters(self):
        """Apply current filters and reset to page 1"""
        self.page = 1
        self.update_displayed_rooms()

    async def load_rooms(self):
        """Load rooms from database"""
        try:
            rooms = await RoomService.get_all_rooms()
            self.rooms = rooms
            self.apply_filters()

        except Exception as e:
            yield rx.toast.error(f"Failed to load rooms: {e}")

    async def create_room(self, room_data: dict):
        """Create new room"""
        try:
            # Validate
            if not room_data.get("name"):
                yield rx.toast.error("Room name is required")
                return

            # Create
            result = await RoomService.create_room(room_data)

            if result["success"]:
                yield rx.toast.success("Room created successfully!")
                yield self.load_rooms()
            else:
                yield rx.toast.error(f"Failed to create room: {result.get('error')}")

        except Exception as e:
            yield rx.toast.error(f"Room creation failed: {e}")
```

### Phase 2 Testing
- [ ] Allocation engine works with async wrapping
- [ ] Reservation creation with conflict detection
- [ ] Room CRUD operations function
- [ ] Computed properties update correctly
- [ ] Filter and pagination work properly

---

## Phase 3: UI Component Development (Week 5-7)

### Objective
Build reactive UI components that leverage the state management system.

### Deliverables

#### 3.1 Layout Components

```python
# core/components/layout/main_layout.py
def main_layout(content: rx.Component) -> rx.Component:
    """Main application layout with navigation"""
    return rx.hstack(
        # Sidebar navigation
        sidebar_navigation(),

        # Main content area
        rx.box(
            rx.vstack(
                # Header
                app_header(),

                # Page content
                rx.box(
                    content,
                    padding="6",
                    flex="1",
                    min_height="80vh"
                ),

                # Footer
                app_footer(),

                spacing="0"
            ),
            flex="1",
            height="100vh"
        ),

        width="100vw",
        height="100vh",
        spacing="0"
    )

def sidebar_navigation() -> rx.Component:
    """Sidebar with navigation menu"""
    return rx.box(
        rx.vstack(
            # Logo/title
            rx.heading("🎓 Ensalamento", size="6", padding="4"),

            # Navigation items
            navigation_item("Dashboard", "dashboard", "home"),
            navigation_item("Rooms", "inventory", "building"),
            navigation_item("Allocation", "allocation", "check_circle"),
            navigation_item("Professors", "professors", "person"),
            navigation_item("Reservations", "reservations", "calendar"),

            # Spacer
            rx.spacer(),

            # User section
            rx.divider(),
            rx.vstack(
                rx.text(AuthState.display_name, font_weight="bold"),
                rx.cond(
                    AuthState.is_logged_in,
                    rx.button("Logout", on_click=AuthState.logout, size="4")
                ),
                padding="4",
                spacing="2"
            ),

            width="250px",
            padding="4",
            spacing="2",
            align="start"
        ),
        height="100%",
        bg="gray.50",
        border_right="1px solid var(--gray-6)"
    )

def navigation_item(label: str, page_key: str, icon: str) -> rx.Component:
    """Individual navigation item"""
    return rx.button(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(label),
            align="center",
            width="100%",
            justify="start"
        ),
        on_click=lambda: NavigationState.navigate_to(page_key),
        variant="ghost",
        width="100%",
        justify="start",
        bg=rx.cond(
            NavigationState.current_page == page_key,
            "blue.100",
            "transparent"
        )
    )
```

#### 3.2 Dashboard Components

```python
# core/components/dashboard/stats_cards.py
def stats_overview() -> rx.Component:
    """Dashboard statistics overview"""
    return rx.grid(
        stat_card(
            "Total Rooms",
            RoomState.rooms.length(),
            "building",
            "blue"
        ),
        stat_card(
            "Total Professors",
            ProfessorState.professors.length(),
            "person",
            "green"
        ),
        stat_card(
            "Active Reservations",
            ReservationState.upcoming_reservations.length(),
            "calendar",
            "orange"
        ),
        stat_card(
            "Today's Classes",
            AllocationState.todays_classes_count,
            "book",
            "purple"
        ),
        columns="4",
        spacing="4",
        width="100%"
    )

def stat_card(title: str, value: rx.Var | int | str, icon: str, color: str) -> rx.Component:
    """Reusable statistics card component"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size="6"4, color=f"{color}.500"),
                rx.spacer(),
                rx.heading(str(value), size="8", color=f"{color}.600")
            ),
            rx.text(title, color="gray.600", font_size="4"),
            align="start",
            spacing="2"
        ),
        width="100%",
        padding="4"
    )

# core/components/dashboard/recent_activity.py
def recent_activity() -> rx.Component:
    """Recent activity feed"""
    return rx.card(
        rx.vstack(
            rx.heading("Recent Activity", size="8"),
            rx.divider(),

            # Activity list (would come from state)
            rx.vstack(
                activity_item("Room A1-01 allocated to MAT123", "2 hours ago"),
                activity_item("New reservation for Seminar Room", "4 hours ago"),
                activity_item("Professor Dr. Silva profile updated", "1 day ago"),
                activity_item("Bulk import completed: 45 courses", "2 days ago"),
                spacing="3",
                align="start"
            ),

            width="100%",
            padding="4",
            spacing="4"
        ),
        width="100%"
    )

def activity_item(description: str, timestamp: str) -> rx.Component:
    """Individual activity item"""
    return rx.hstack(
        rx.box(
            rx.icon("circle", size=8, color="blue.500"),
            margin_right="3"
        ),
        rx.vstack(
            rx.text(description, font_size="4"),
            rx.text(timestamp, font_size="xs", color="gray.500"),
            align="start",
            spacing="0"
        ),
        width="100%",
        align="start"
    )
```

#### 3.3 Data Management Components

```python
# core/components/data/room_table.py
def room_management_table() -> rx.Component:
    """Room management table with pagination and filters"""
    return rx.card(
        rx.vstack(
            # Header with actions
            rx.hstack(
                rx.heading("Room Inventory", size="8"),
                rx.spacer(),
                rx.button(
                    rx.icon("plus", size=16),
                    "Add Room",
                    on_click=RoomState.show_create_dialog
                ),
                align="center"
            ),

            rx.divider(),

            # Filters
            rx.hstack(
                rx.input(
                    placeholder="Search rooms...",
                    value=RoomState.search_query,
                    on_change=RoomState.set_search_query,
                    width="300px"
                ),
                rx.select(
                    ["all", "Main Building", "Annex", "Lab Block"],
                    value=RoomState.building_filter,
                    on_change=RoomState.set_building_filter,
                    width="200px"
                ),
                rx.number_input(
                    placeholder="Min capacity",
                    value=RoomState.capacity_min,
                    on_change=RoomState.set_capacity_min,
                    width="150px"
                ),
                spacing="3"
            ),

            # Table
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Name"),
                            rx.table.column_header_cell("Building"),
                            rx.table.column_header_cell("Capacity"),
                            rx.table.column_header_cell("Type"),
                            rx.table.column_header_cell("Actions"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            RoomState.displayed_rooms,
                            room_table_row
                        )
                    ),
                ),
                max_height="500px",
                overflow="auto"
            ),

            # Pagination
            rx.cond(
                RoomState.total_pages > 1,
                pagination_controls(),
                rx.box()  # Hidden when not needed
            ),

            width="100%",
            spacing="4"
        ),
        width="100%"
    )

def room_table_row(room: dict) -> rx.Component:
    """Table row for room data"""
    return rx.table.row(
        rx.table.cell(room["name"]),
        rx.table.cell(room.get("building", "Unknown")),
        rx.table.cell(str(room.get("capacity", 0))),
        rx.table.cell(room.get("room_type", "Standard")),
        rx.table.cell(
            rx.hstack(
                room_action_button("edit", room["id"], "Edit"),
                room_action_button("delete", room["id"], "Delete", "red"),
                spacing="2"
            )
        )
    )

def room_action_button(action: str, room_id: int, label: str, color: str = "blue") -> rx.Component:
    """Action button for room operations"""
    return rx.button(
        label,
        size="4",
        color_scheme=color,
        variant="soft",
        on_click=lambda: RoomState.handle_room_action(action, room_id)
    )

def pagination_controls() -> rx.Component:
    """Pagination controls"""
    return rx.hstack(
        rx.button(
            "Previous",
            on_click=RoomState.prev_page,
            disabled=RoomState.page == 1
        ),
        rx.text(
            f"Page {RoomState.page} of {RoomState.total_pages}",
            font_size="4"
        ),
        rx.button(
            "Next",
            on_click=RoomState.next_page,
            disabled=RoomState.page == RoomState.total_pages
        ),
        spacing="4",
        justify="center"
    )
```

#### 3.4 Form Components

```python
# core/components/forms/reservation_form.py
def reservation_form_dialog() -> rx.Component:
    """Reservation creation/update dialog"""
    return rx.cond(
        ReservationState.show_create_dialog,
        rx.dialog.root(
            rx.dialog.overlay(),
            rx.dialog.content(
                rx.vstack(
                    # Header
                    rx.dialog.title("Create Reservation"),
                    rx.dialog.description("Fill in the reservation details below"),

                    # Form content
                    rx.vstack(
                        # Basic info
                        rx.input(
                            placeholder="Event Title",
                            value=ReservationState.form_title,
                            on_change=ReservationState.set_form_title,
                            required=True
                        ),
                        rx.cond(
                            ReservationState.form_title_error != "",
                            rx.text(ReservationState.form_title_error, color="red", size="4")
                        ),

                        # Date and time
                        rx.input(
                            type="date",
                            value=ReservationState.form_date,
                            on_change=ReservationState.set_form_date
                        ),

                        rx.select(
                            ["M1", "M2", "T1", "T2", "N1", "N2"],
                            placeholder="Select time block",
                            value=ReservationState.form_time_block,
                            on_change=ReservationState.set_form_time_block
                        ),

                        # Room selection
                        room_selector(),

                        # Additional info
                        rx.text_area(
                            placeholder="Description (optional)",
                            value=ReservationState.form_description,
                            on_change=ReservationState.set_form_description
                        ),

                        rx.input(
                            placeholder="Your name",
                            value=ReservationState.form_requester_name,
                            on_change=ReservationState.set_form_requester_name
                        ),

                        spacing="4",
                        align="stretch"
                    ),

                    # Footer actions
                    rx.hstack(
                        rx.dialog.close(
                            rx.button("Cancel", variant="soft")
                        ),
                        rx.button(
                            "Create Reservation",
                            on_click=ReservationState.submit_reservation,
                            loading=ReservationState.form_submitting
                        ),
                        justify="end",
                        spacing="3"
                    ),

                    spacing="6"
                ),
                max_width="600px"
            ),
        )
    )

def room_selector() -> rx.Component:
    """Room selection component with search"""
    return rx.vstack(
        rx.heading("Select Room", size="4"),
        rx.select(
            # Would be populated from RoomState
            ["Room A1-01 (30 seats)", "Room A1-02 (25 seats)", "Auditorium (200 seats)"],
            placeholder="Choose a room...",
            value=ReservationState.form_selected_room,
            on_change=ReservationState.set_form_selected_room
        ),

        # Room details preview
        rx.cond(
            ReservationState.form_selected_room != "",
            rx.box(
                rx.vstack(
                    rx.heading("Room Details", size="4"),
                    rx.text(f"Selected: {ReservationState.form_selected_room}"),
                    rx.text("Capacity: 30 seats"),
                    rx.text("Equipment: Projector, Whiteboard"),
                    padding="3",
                    bg="gray.50",
                    border_radius=6
                ),
                margin_top="2"
            )
        ),

        align="start",
        spacing="2"
    )
```

---

## Phase 4: Integration & Testing (Week 8-9)

### Objective
Connect all components, implement error boundaries, and ensure end-to-end functionality.

### Deliverables

#### 4.1 Main Application File

```python
# ensalamento_reflex/ensalamento_reflex.py
import reflex as rx

from core.components.layout.main_layout import main_layout
from core.states.auth_state import AuthState
from core.states.navigation_state import NavigationState

# Import page components
from core.components.pages.dashboard import dashboard_page
from core.components.pages.allocation import allocation_page
from core.components.pages.professors import professors_page
from core.components.pages.reservations import reservations_page
from core.components.pages.inventory import inventory_page

def app_content() -> rx.Component:
    """Main application content with routing"""
    return rx.cond(
        AuthState.is_logged_in,
        # Authenticated content
        main_layout(
            page_router()
        ),
        # Login page
        login_page()
    )

def page_router() -> rx.Component:
    """Route to appropriate page based on navigation state"""
    return rx.match(
        NavigationState.current_page,
        ("dashboard", dashboard_page()),
        ("allocation", allocation_page()),
        ("inventory", inventory_page()),
        ("professors", professors_page()),
        ("reservations", reservations_page()),
        # Default fallback
        dashboard_page()
    )

def login_page() -> rx.Component:
    """Login page component"""
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("🎓 Ensalamento FUP", size="3"),
                rx.text("Entre com suas credenciais", margin_bottom="4"),

                # Login form
                rx.vstack(
                    rx.input(
                        placeholder="Username",
                        value=AuthState.login_username,
                        on_change=AuthState.set_login_username,
                        width="100%"
                    ),
                    rx.input(
                        type="password",
                        placeholder="Password",
                        value=AuthState.login_password,
                        on_change=AuthState.set_login_password,
                        width="100%"
                    ),
                    rx.button(
                        "Login",
                        on_click=AuthState.login,
                        loading=AuthState.login_loading,
                        width="100%"
                    ),

                    # Error display
                    rx.cond(
                        AuthState.login_error != "",
                        rx.callout(
                            AuthState.login_error,
                            icon="alert_triangle",
                            color_scheme="red"
                        )
                    ),

                    spacing="3",
                    width="300px"
                ),

                spacing="6",
                align="center"
            ),
            width="400px",
            padding="6"
        ),
        height="100vh"
    )

# App configuration
app = rx.App(
    theme=rx.theme(
        accent_color="blue",
        gray_color="slate",
        radius="large"
    )
)

# Add main page
app.add_page(app_content, title="Ensalamento FUP")
```

#### 4.2 Error Boundaries & Fallbacks

```python
# core/components/error/error_boundary.py
import reflex as rx
from core.states.error_state import ErrorState

def error_boundary(content: rx.Component) -> rx.Component:
    """Global error boundary component"""
    return rx.cond(
        ErrorState.has_global_error,
        error_display(),
        content
    )

def error_display() -> rx.Component:
    """Error display component"""
    return rx.center(
        rx.vstack(
            rx.icon("alert_triangle", size=64, color="red.500"),
            rx.heading("Something went wrong", size="3"),
            rx.text(ErrorState.global_error_message, text_align="center"),
            rx.divider(),

            rx.cond(
                ErrorState.show_error_details,
                rx.box(
                    rx.heading("Technical Details", size="5"),
                    rx.code_block(
                        ErrorState.global_error_details,
                        language="text",
                        max_height="300px",
                        overflow="auto"
                    ),
                    width="100%",
                    margin="4"
                )
            ),

            rx.hstack(
                rx.button(
                    "Try Again",
                    on_click=lambda: ErrorState.retry_last_operation()
                ),
                rx.button(
                    "Reload App",
                    on_click=lambda: rx.redirect("/")
                ),
                rx.button(
                    "Show Details",
                    on_click=ErrorState.toggle_error_details,
                    variant="soft"
                ),
                spacing="3"
            ),

            spacing="6",
            align="center",
            max_width="600px"
        ),
        height="100vh",
        padding="6"
    )

# Usage in main app
def app_content() -> rx.Component:
    return error_boundary(
        rx.cond(
            AuthState.is_logged_in,
            main_layout(page_router()),
            login_page()
        )
    )
```

---

## Phase 5: Performance Optimization & Production (Week 10-11)

### Objective
Optimize performance, add production-ready features, and prepare for deployment.

### Deliverables

#### 5.1 Performance Optimizations

```python
# core/states/cache_state.py - Enhanced
import reflex as rx
from datetime import datetime, timedelta

class CacheState(rx.State):
    """Advanced caching state with TTL and invalidation"""

    # Cache data with timestamps
    room_cache: dict[str, dict] = rx.SessionStorage(default_factory=dict)
    professor_cache: dict[str, dict] = rx.SessionStorage(default_factory=dict)
    allocation_cache: dict[str, dict] = rx.SessionStorage(default_factory=dict)

    # Cache metadata
    cache_timestamps: dict[str, str] = rx.SessionStorage(default_factory=dict)

    CACHE_TTL_MINUTES = 5

    def is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid"""
        if cache_key not in self.cache_timestamps:
            return False

        try:
            cached_time = datetime.fromisoformat(self.cache_timestamps[cache_key])
            return datetime.now() - cached_time < timedelta(minutes=self.CACHE_TTL_MINUTES)
        except (ValueError, TypeError):
            return False

    def get_cached_data(self, cache_type: str, key: str) -> dict | None:
        """Get data from cache if valid"""
        cache = getattr(self, f"{cache_type}_cache", {})
        if self.is_cache_valid(f"{cache_type}_{key}"):
            return cache.get(key)
        return None

    def set_cached_data(self, cache_type: str, key: str, data: dict):
        """Store data in cache with timestamp"""
        cache = getattr(self, f"{cache_type}_cache", {})
        cache[key] = data

        # Update cache attribute
        setattr(self, f"{cache_type}_cache", dict(cache))

        # Update timestamp
        self.cache_timestamps[f"{cache_type}_{key}"] = datetime.now().isoformat()
        self.cache_timestamps = dict(self.cache_timestamps)

    def invalidate_cache(self, cache_type: str = None, key: str = None):
        """Invalidate cache - all, by type, or specific key"""
        if cache_type and key:
            # Invalidate specific key
            cache = getattr(self, f"{cache_type}_cache", {})
            cache.pop(key, None)
            setattr(self, f"{cache_type}_cache", dict(cache))

            self.cache_timestamps.pop(f"{cache_type}_{key}", None)
            self.cache_timestamps = dict(self.cache_timestamps)
        elif cache_type:
            # Invalidate entire cache type
            setattr(self, f"{cache_type}_cache", {})
            # Remove all timestamps for this type
            keys_to_remove = [k for k in self.cache_timestamps.keys() if k.startswith(f"{cache_type}_")]
            for key in keys_to_remove:
                self.cache_timestamps.pop(key, None)
            self.cache_timestamps = dict(self.cache_timestamps)
        else:
            # Invalidate all caches
            self.room_cache = {}
            self.professor_cache = {}
            self.allocation_cache = {}
            self.cache_timestamps = {}

    async def load_with_cache(self, cache_type: str, key: str, fetch_func, *args, **kwargs):
        """Load data with caching"""
        # Try cache first
        cached = self.get_cached_data(cache_type, key)
        if cached:
            return cached

        # Fetch fresh data
        data = await fetch_func(*args, **kwargs)

        # Cache result
        self.set_cached_data(cache_type, key, data)

        return data
```

#### 5.2 Production Configuration

```python
# core/config/production.py
import os
from typing import Dict, Any

class ProductionConfig:
    """Production configuration with security and performance optimizations"""

    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY is required in production")

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/ensalamento.db")

    # Caching
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 minutes

    # API Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # External APIs
    API_TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT", "30.0"))
    SISTEMA_OFERTA_URL = os.getenv("SISTEMA_OFERTA_URL")
    SISTEMA_OFERTA_TOKEN = os.getenv("SISTEMA_OFERTA_TOKEN")

    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """Get database connection configuration"""
        return {
            "url": cls.DATABASE_URL,
            "echo": cls.DEBUG,
            "pool_pre_ping": True,
            "pool_recycle": 300
        }

    @classmethod
    def get_reflex_config(cls) -> Dict[str, Any]:
        """Get Reflex app configuration"""
        return {
            "loglevel": "warning" if not cls.DEBUG else "info",
            "port": int(os.getenv("PORT", "8000")),
            "host": "0.0.0.0",
            "reload": False  # Disable in production
        }
```

---

## Phase 6: Production Deployment & Monitoring (Week 12)

### Objective
Deploy to production and establish monitoring capabilities.

### Final Deliverables

#### 6.1 Deployment Configuration

**Docker Compose for Production:**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  ensalamento-reflex:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "80:8000"
    environment:
      - ENVIRONMENT=production
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=sqlite:///data/ensalamento.db
    volumes:
      - ./data:/app/data  # Persistent database
      - ./logs:/app/logs  # Logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Nginx Reverse Proxy:**
```nginx
# nginx.conf
server {
    listen 80;
    server_name ensalamento.fup.unb.br;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubdomains";

    # Serve static files
    location /_static/ {
        alias /app/_static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Proxy to Reflex app
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for Reflex
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 6.2 Monitoring & Logging

```python
# core/utils/monitoring.py
import logging
import time
from functools import wraps
from typing import Callable, Any
import psutil
import reflex as rx

class MonitoringUtils:
    """Production monitoring utilities"""

    @staticmethod
    def setup_logging():
        """Configure structured logging for production"""
        logging.basicConfig(
            level=logging.INFO,
            format
