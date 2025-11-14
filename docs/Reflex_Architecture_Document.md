# Reflex Architecture Document
# Sistema de Ensalamento FUP/UnB - Migration to Reflex v0.8.19

**Version:** 1.0 (Reflex Migration)
**Date:** November 14, 2025

---

## Executive Summary

This document defines the architecture for migrating the **Sistema de Ensalamento FUP/UnB** from Streamlit to **Reflex v0.8.19**. The migration transforms a multi-page Streamlit application into a modern, reactive single-page application while preserving all existing business logic and data models.

### Key Architectural Changes
- **State Management:** From `st.session_state` to centralized Reflex State classes with defensive mutation patterns
- **Component Structure:** From page-based routing to nested component composition
- **Data Flow:** From synchronous blocking operations to async event-driven architecture
- **Authentication:** From `streamlit-authenticator` to persistent LocalStorage/SessionStorage-based auth
- **Business Logic:** Preserved through service layer with `asyncio.to_thread` wrapping for database operations

---

## Core Architecture Principles

### State Management Fundamentals (PER REQUIRED PATTERN)

**CRITICAL:** State is the single source of truth. UI = f(State). Never manipulate DOM directly.

```python
# core/states/base_state.py
class BaseState(rx.State):
    """Shared base functionality for all states"""
    loading: bool = False
    error: str = ""
    success_message: str = ""

    def set_error(self, msg: str):
        self.error = msg
        self.loading = False
        self.success_message = ""

    def set_success(self, msg: str):
        self.success_message = msg
        self.error = ""

# core/states/auth_state.py
class AuthState(BaseState):
    """Authentication state with LocalStorage persistence"""
    username: str = rx.LocalStorage(default="")
    is_logged_in: bool = rx.LocalStorage(default=False)
    role: str = rx.LocalStorage(default="user")

    @rx.var
    def display_name(self) -> str:
        """Computed property - no manual storage"""
        return f"@{self.username}" if self.username else "Guest"
```

**Container Mutation Pattern (MANDATORY - Follows Reflex Agents Guide):**
```python
class AllocationState(rx.State):
    demands: list[dict] = []

    def add_demand(self, demand: dict):
        """✅ CORRECT - Defensive reassignment triggers UI update"""
        self.demands.append(demand)
        self.demands = list(self.demands)  # Triggers reactivity

    def remove_demand(self, demand_id: int):
        """✅ CORRECT - Defensive reassignment"""
        self.demands = [d for d in self.demands if d["id"] != demand_id]
```

### Async/Loading Pattern (ESSENTIAL)

**ALWAYS use loading flags for operations >100ms (PER PATTERN):**

```python
# core/states/allocation_state.py
class AllocationState(rx.State):
    loading_allocation: bool = False
    current_allocation: dict | None = None

    async def execute_allocation(self, semester_id: int):
        """Proper async pattern with loading states"""
        if self.loading_allocation:
            return rx.toast.info("Allocation already in progress")

        self.loading_allocation = True
        self.error = ""
        yield  # Allow UI to update

        try:
            # Async work with database operations
            result = await asyncio.to_thread(
                self._execute_allocation_sync,
                semester_id
            )

            self.current_allocation = result
            yield rx.toast.success("Allocation completed successfully")

        except Exception as e:
            self.error = str(e)
            yield rx.toast.error(f"Allocation failed: {e}")

        finally:
            self.loading_allocation = False
```

### Computed Properties Pattern (CRITICAL PERFORMANCE)

**Use `@rx.var` for derived data instead of storing redundantly:**

```python
# core/states/room_state.py
class RoomState(rx.State):
    all_rooms: list[dict] = []  # Only store source data

    @rx.var
    def available_rooms(self) -> list[dict]:
        """Automatically computed when all_rooms changes"""
        return [r for r in self.all_rooms if r["status"] == "available"]

    @rx.var
    def rooms_by_building(self) -> dict[str, list[dict]]:
        """Grouped by building - recomputed automatically"""
        grouped = {}
        for room in self.all_rooms:
            building = room["building"]
            if building not in grouped:
                grouped[building] = []
            grouped[building].append(room)
        return grouped

    @rx.var
    def utilization_stats(self) -> dict:
        """Computed utilization metrics"""
        total = len(self.all_rooms)
        available = len(self.available_rooms)
        return {
            "total": total,
            "available": available,
            "utilization": f"{((total - available) / total * 100):.1f}%" if total > 0 else "0%"
        }
```

---

## Component Architecture

### Page Structure (Single Page Application)

**Composition-based routing instead of multi-page:**

```python
# ensalamento_reflex/ensalamento_reflex.py (Main App)
import reflex as rx
from core.components.layout import main_layout
from core.states.auth_state import AuthState
from core.states.navigation_state import NavigationState

def app_content() -> rx.Component:
    """Main application component with route-based content"""
    return rx.cond(
        AuthState.is_logged_in,
        authenticated_content(),
        login_page()
    )

def authenticated_content() -> rx.Component:
    """Authenticated user interface"""
    return rx.hstack(
        sidebar_navigation(),  # Navigation sidebar
        main_content_area(),   # Dynamic content area
        width="100vw",
        height="100vh"
    )

def main_content_area() -> rx.Component:
    """Route-based content switching"""
    return rx.match(
        NavigationState.current_page,
        ("home", home_page()),
        ("inventory", inventory_page()),
        ("allocation", allocation_page()),
        ("professors", professors_page()),
        ("reservations", reservations_page()),
        default_page()  # Default/fallback
    )

# Initialize app with theme
app = rx.App(
    theme=rx.theme(
        accent_color="blue",
        gray_color="slate",
        radius="large"
    )
)

app.add_page(app_content, title="Ensalamento FUP")
```

### Component Composition Patterns

**Small, reusable components with clear props:**

```python
# core/components/common/card.py
def info_card(
    title: str,
    content: str | rx.Component,
    icon: str = "info",
    color_scheme: str = "blue"
) -> rx.Component:
    """Reusable info card component"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=20),
                rx.heading(title, size="md"),
                align="center"
            ),
            rx.box(content),
            spacing="2",
            align="start"
        ),
        color_scheme=color_scheme
    )

# Usage across pages
rx.grid(
    info_card("Total Rooms", RoomState.utilization_stats["total"], "building"),
    info_card("Available", RoomState.available_rooms.length(), "check_circle"),
    info_card("Utilization", RoomState.utilization_stats["utilization"], "bar_chart"),
    columns="3",
    spacing="4"
)
```

### Forms and Validation (Following Patterns)

```python
# core/components/forms/room_form.py
def room_form_dialog(show: bool = False) -> rx.Component:
    """Room creation/editing form following validation patterns"""
    return rx.cond(
        show,
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Add/Edit Room"),
                rx.vstack(
                    # Form fields with validation
                    rx.input(
                        placeholder="Room Name",
                        value=RoomFormState.name,
                        on_change=RoomFormState.set_name,
                        on_blur=RoomFormState.validate_name
                    ),
                    rx.cond(
                        RoomFormState.name_error != "",
                        rx.text(RoomFormState.name_error, color="red", size="sm")
                    ),

                    rx.input(
                        placeholder="Capacity",
                        value=RoomFormState.capacity,
                        on_change=RoomFormState.set_capacity,
                        on_blur=RoomFormState.validate_capacity
                    ),
                    rx.cond(
                        RoomFormState.capacity_error != "",
                        rx.text(RoomFormState.capacity_error, color="red", size="sm")
                    ),

                    rx.hstack(
                        rx.dialog.close(
                            rx.button("Cancel", variant="soft")
                        ),
                        rx.button(
                            "Save",
                            on_click=RoomFormState.save_room,
                            loading=RoomFormState.saving
                        ),
                        justify="end"
                    ),
                    spacing="3"
                ),
                min_width="400px"
            ),
            open=show
        )
    )

# Form state following patterns
class RoomFormState(rx.State):
    # Form data
    name: str = ""
    capacity: str = ""
    building_id: int = 0

    # Validation errors
    name_error: str = ""
    capacity_error: str = ""

    # State
    saving: bool = False
    is_edit: bool = False
    room_id: int | None = None

    def validate_name(self):
        if not self.name.strip():
            self.name_error = "Room name is required"
        elif len(self.name.strip()) < 2:
            self.name_error = "Room name must be at least 2 characters"
        else:
            self.name_error = ""

    def validate_capacity(self):
        try:
            cap = int(self.capacity)
            if cap <= 0:
                self.capacity_error = "Capacity must be positive"
            elif cap > 1000:
                self.capacity_error = "Capacity seems too high (max 1000)"
            else:
                self.capacity_error = ""
        except ValueError:
            self.capacity_error = "Capacity must be a number"

    async def save_room(self):
        # Validate all fields
        self.validate_name()
        self.validate_capacity()

        if self.name_error or self.capacity_error:
            return

        self.saving = True

        try:
            room_data = {
                "name": self.name,
                "capacity": int(self.capacity),
                "building_id": self.building_id
            }

            if self.is_edit and self.room_id:
                # Update existing room
                await asyncio.to_thread(RoomService.update_room, self.room_id, room_data)
                yield rx.toast.success("Room updated successfully")
            else:
                # Create new room
                await asyncio.to_thread(RoomService.create_room, room_data)
                yield rx.toast.success("Room created successfully")

            # Close dialog and refresh data
            yield RoomState.load_rooms()

        except Exception as e:
            yield rx.toast.error(f"Failed to save room: {e}")

        finally:
            self.saving = False
```

---

## State Architecture (Advanced)

### State Organization by Concern

```
core/states/
├── auth_state.py          # Authentication & user management
├── navigation_state.py    # Page routing and navigation
├── room_state.py          # Room inventory management
├── professor_state.py     # Professor and preferences
├── allocation_state.py    # Allocation execution and results
├── semester_state.py      # Semester data management
├── reservation_state.py   # Reservation creation and management
└── base_state.py          # Shared functionality
```

### Global vs Local State Decision Tree

**Use GLOBAL state when:**
- Data shared across multiple pages (auth status, current semester)
- Data persists during navigation
- Multiple components need read/write access

**Use LOCAL state when:**
- Data only relevant to one page (form inputs, modal visibility)
- Data should reset when leaving page
- Temporary UI state that doesn't need persistence

### Authentication State (Global with Persistence)

```python
# core/states/auth_state.py
class AuthState(rx.State):
    """Global authentication state with LocalStorage persistence"""

    # Persistence layer - survives browser refresh
    username: str = rx.LocalStorage(default="")
    is_logged_in: bool = rx.LocalStorage(default=False)
    role: str = rx.LocalStorage(default="user")

    # Session-only state - resets on refresh
    current_token: str = rx.SessionStorage(default="")

    # Volatile state - resets on navigation
    login_loading: bool = False

    @rx.var
    def display_name(self) -> str:
        return f"@{self.username}" if self.username else "Guest"

    @rx.var
    def is_admin(self) -> bool:
        return self.role == "admin"

    async def login(self, username: str, password: str):
        """Async login with proper error handling"""
        if self.login_loading:
            return rx.toast.info("Login already in progress")

        self.login_loading = True
        yield

        try:
            # Verify credentials (server-side operation)
            user_data = await asyncio.to_thread(
                self._verify_credentials_sync,
                username, password
            )

            if user_data:
                # Set persistent state
                self.username = user_data["username"]
                self.role = user_data["role"]
                self.is_logged_in = True
                self.current_token = user_data["token"]

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
```

### Navigation State (Global)

```python
# core/states/navigation_state.py
class NavigationState(rx.State):
    """Global navigation state for SPA routing"""

    current_page: str = "home"
    breadcrumbs: list[dict] = []

    @rx.var
    def current_page_title(self) -> str:
        """Computed page title based on current page"""
        titles = {
            "home": "Dashboard",
            "inventory": "Room Inventory",
            "allocation": "Room Allocation",
            "professors": "Professor Management",
            "reservations": "Reservations"
        }
        return titles.get(self.current_page, "Unknown Page")

    def navigate_to(self, page: str):
        """Navigate to a new page"""
        self.current_page = page

        # Update breadcrumbs
        self.breadcrumbs = [
            {"label": "Home", "page": "home"},
            {"label": self.current_page_title, "page": page}
        ]

    @rx.var
    def can_go_back(self) -> bool:
        """Check if back navigation is possible"""
        return len(self.breadcrumbs) > 1

    def go_back(self):
        """Navigate to previous breadcrumb"""
        if self.can_go_back:
            self.breadcrumbs.pop()
            last_crumb = self.breadcrumbs[-1]
            self.current_page = last_crumb["page"]
```

---

## Database & API Integration

### Service Layer Pattern (PRESERVED)

**Maintain existing business logic through service layer:**

```python
# core/services/allocation_service.py (MODIFIED FOR REFLEX)
import asyncio
from typing import Dict, Any
from src.services.optimized_autonomous_allocation_service import OptimizedAutonomousAllocationService

class AllocationService:
    """Reflex-compatible service wrapper"""

    @staticmethod
    async def execute_allocation_sync(semester_id: int) -> Dict[str, Any]:
        """Async wrapper for allocation execution"""
        # Get service instance (could be singleton or new instance)
        service = OptimizedAutonomousAllocationService()

        # Execute allocation (synchronous operation)
        result = service.execute_autonomous_allocation(semester_id)

        return result

    @staticmethod
    async def get_allocation_progress(semester_id: int) -> Dict[str, Any]:
        """Async wrapper for progress checking"""
        service = OptimizedAutonomousAllocationService()
        return await asyncio.to_thread(
            service.get_allocation_progress,
            semester_id
        )
```

### State Integration Pattern

```python
# core/states/allocation_state.py
class AllocationState(rx.State):
    """Allocation operations state"""
    running_allocation: bool = False
    last_result: dict | None = None
    progress: dict = {}

    async def run_autonomous_allocation(self, semester_id: int):
        """Execute autonomous allocation with Reflex patterns"""
        if self.running_allocation:
            return rx.toast.info("Allocation already running")

        self.running_allocation = True
        yield

        try:
            result = await AllocationService.execute_allocation_sync(semester_id)

            if result.get("success"):
                self.last_result = result

                # Store PDF if available
                if "pdf_report" in result:
                    # Handle PDF storage (could use LocalStorage temporarily)
                    pass

                yield rx.toast.success(
                    f"Allocation completed: {result.get('allocations_completed', 0)} placements"
                )
            else:
                yield rx.toast.error(f"Allocation failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            yield rx.toast.error(f"Allocation error: {e}")

        finally:
            self.running_allocation = False

    async def refresh_progress(self, semester_id: int):
        """Refresh allocation progress"""
        try:
            progress = await AllocationService.get_allocation_progress(semester_id)
            self.progress = progress or {}
        except Exception as e:
            self.error = f"Failed to load progress: {e}"
```

---

## Component Layout System

### Main Layout Component

```python
# core/components/layout.py
def main_layout(content: rx.Component) -> rx.Component:
    """Main application layout with header, sidebar, and content area"""
    return rx.vstack(
        # Header
        header_component(),

        # Main content area
        rx.hstack(
            # Sidebar navigation
            sidebar_navigation(),

            # Page content
            rx.box(
                content,
                flex="1",
                padding="4",
                min_height="80vh"
            ),

            width="100%"
        ),

        # Footer
        footer_component(),

        height="100vh",
        width="100vw",
        spacing="0"
    )

def header_component() -> rx.Component:
    """Application header with logo and user menu"""
    return rx.hstack(
        # Logo/title
        rx.heading("🎓 Ensalamento FUP", size="lg"),

        # Spacer
        rx.spacer(),

        # User menu (conditional)
        rx.cond(
            AuthState.is_logged_in,
            user_menu_component(),
            login_button()
        ),

        width="100%",
        padding="4",
        bg="gray.50",
        border_bottom="1px solid var(--gray-6)"
    )

def sidebar_navigation() -> rx.Component:
    """Sidebar with navigation menu"""
    return rx.box(
        rx.vstack(
            # Navigation items
            rx.button(
                "🏠 Dashboard",
                on_click=lambda: NavigationState.navigate_to("home"),
                variant="ghost",
                width="100%",
                justify="start"
            ),
            rx.button(
                "🏢 Inventory",
                on_click=lambda: NavigationState.navigate_to("inventory"),
                variant="ghost",
                width="100%",
                justify="start"
            ),
            rx.button(
                "✅ Allocation",
                on_click=lambda: NavigationState.navigate_to("allocation"),
                variant="ghost",
                width="100%",
                justify="start"
            ),
            rx.button(
                "👨‍🏫 Professors",
                on_click=lambda: NavigationState.navigate_to("professors"),
                variant="ghost",
                width="100%",
                justify="start"
            ),
            rx.button(
                "📅 Reservations",
                on_click=lambda: NavigationState.navigate_to("reservations"),
                variant="ghost",
                width="100%",
                justify="start"
            ),

            rx.spacer(),

            # Logout button
            rx.button(
                "🚪 Logout",
                on_click=AuthState.logout,
                variant="soft",
                color_scheme="red",
                width="100%"
            ),

            width="250px",
            padding="4",
            spacing="2",
            align="start"
        ),

        height="100%",
        bg="white",
        border_right="1px solid var(--gray-6)"
    )
```

---

## Data Flow Architecture

### Request/Response Flow

```
User Interaction → Event Handler → State Method → Service Layer → Database
                       ↓
                UI Updates Automatically ← State Changes
```

### State Synchronization

**All state changes are reactive and automatic:**

```python
# 1. User clicks button
rx.button("Save", on_click=FormState.save_data)

# 2. Event triggers state method
class FormState(rx.State):
    async def save_data(self):
        # State change triggers immediate UI update
        self.loading = True
        yield  # UI updates to show spinner

        # Business logic
        await self._perform_save()

        # State change triggers final UI update
        self.loading = False
        yield rx.toast.success("Saved!")
```

---

## Security Architecture

### Authentication & Authorization

```python
# core/components/auth.py
def protected_route(component: rx.Component) -> rx.Component:
    """Higher-order component for protected routes"""
    return rx.cond(
        AuthState.is_logged_in,
        component,  # Render protected content
        rx.center(
            rx.vstack(
                rx.heading("Please log in", size="lg"),
                rx.button(
                    "Go to Login",
                    on_click=lambda: rx.redirect("/login")
                ),
                spacing="4"
            ),
            height="50vh"
        )
    )

def admin_only(component: rx.Component) -> rx.Component:
    """Higher-order component for admin-only content"""
    return rx.cond(
        AuthState.is_admin,
        component,  # Render admin content
        rx.center(
            rx.text("Access denied - Admin privileges required", color="red"),
            height="50vh"
        )
    )

# Usage
def allocation_page():
    return protected_route(
        admin_only(
            allocation_content()  # Only admins can access
        )
    )
```

### Data Sanitization (PRESERVED)

```python
# core/utils/validation.py
import html
import bleach

def sanitize_text_input(text: str) -> str:
    """Sanitize user input for display"""
    if not text:
        return ""

    # Escape HTML entities
    escaped = html.escape(text.strip())

    # Allow only safe tags if needed
    clean = bleach.clean(
        escaped,
        tags=['b', 'i', 'u', 'p', 'br'],  # Allow limited formatting
        strip=True
    )

    return clean

# Used in forms
class CommentState(rx.State):
    def add_comment(self, text: str):
        # Sanitize before storing
        safe_text = sanitize_text_input(text)
        self.comments.append({"text": safe_text, "author": AuthState.username})
        self.comments = list(self.comments)  # Defensive reassignment
```

---

## Performance Optimizations

### Lazy Loading & Pagination

```python
# core/states/professor_state.py
class ProfessorState(rx.State):
    all_professors: list[dict] = []
    displayed_professors: list[dict] = []
    page: int = 1
    page_size: int = 20
    total_count: int = 0
    loading_professors: bool = False

    @rx.var
    def total_pages(self) -> int:
        return (self.total_count + self.page_size - 1) // self.page_size

    async def load_professor_page(self):
        """Load professors for current page only"""
        if self.loading_professors:
            return

        self.loading_professors = True

        try:
            # Load paginated data from service
            result = await asyncio.to_thread(
                ProfessorService.get_professors_paginated,
                page=self.page,
                page_size=self.page_size
            )

            self.displayed_professors = result["professors"]
            self.total_count = result["total"]

        except Exception as e:
            self.error = f"Failed to load professors: {e}"

        finally:
            self.loading_professors = False

    def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            # Trigger reload
            return self.load_professor_page()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            return self.load_professor_page()
```

### Computed Var Memoization

```python
# Automatic performance benefits
class DashboardState(rx.State):
    raw_allocation_data: list[dict] = []

    @rx.var
    def allocation_summary(self) -> dict:
        """Automatically recomputed only when raw_allocation_data changes"""
        # Expensive computation - runs only when needed
        allocated = sum(1 for item in self.raw_allocation_data if item["allocated"] == True)
        total = len(self.raw_allocation_data)

        return {
            "allocated": allocated,
            "total": total,
            "percentage": f"{(allocated / total * 100):.1f}%" if total > 0 else "0%"
        }

    @rx.var
    def daily_stats(self) -> dict[str, dict]:
        """Grouped by day - expensive but automatic"""
        grouped = {}
        for item in self.raw_allocation_data:
            day = item["day"]
            if day not in grouped:
                grouped[day] = {"allocated": 0, "total": 0}
            grouped[day]["total"] += 1
            if item["allocated"]:
                grouped[day]["allocated"] += 1
        return grouped
```

---

## Error Handling & Resilience

### Global Error Boundary

```python
# core/components/error_boundary.py
def error_boundary(content: rx.Component) -> rx.Component:
    """Global error boundary component"""
    return rx.cond(
        ErrorState.has_error,
        rx.center(
            rx.vstack(
                rx.icon("alert_triangle", size=50, color="red"),
                rx.heading("Something went wrong", size="lg"),
                rx.text(ErrorState.error_message),

                rx.cond(
                    ErrorState.show_details,
                    rx.box(
                        rx.text("Error Details:", font_weight="bold"),
                        rx.code_block(ErrorState.error_details),
                        width="100%",
                        max_height="200px",
                        overflow="auto"
                    )
                ),

                rx.hstack(
                    rx.button(
                        "Try Again",
                        on_click=ErrorState.retry_last_action
                    ),
                    rx.button(
                        "Reload Page",
                        on_click=lambda: rx.redirect(rx.get_current_url())
                    ),
                    spacing="2"
                ),

                spacing="4",
                align="center"
            ),
            height="50vh"
        ),
        content  # Normal content when no error
    )

class ErrorState(rx.State):
    """Global error state"""
    has_error: bool = False
    error_message: str = ""
    error_details: str = ""
    show_details: bool = False
    last_action: str = ""

    def handle_error(self, error: Exception, action: str = ""):
        """Central error handling"""
        self.has_error = True
        self.error_message = str(error)
        self.error_details = traceback.format_exc()
        self.last_action = action

        # Log to console for debugging
        print(f"Error in {action}: {error}")
        print(f"Details: {self.error_details}")

    def clear_error(self):
        """Clear error state"""
        self.has_error = False
        self.error_message = ""
        self.error_details = ""
        self.show_details = False
        self.last_action = ""

    def toggle_details(self):
        """Show/hide error details"""
        self.show_details = not self.show_details

    def retry_last_action(self):
        """Attempt to retry the last failed action"""
        if self.last_action:
            # Logic to retry based on last_action
            # This would need to be implemented per action type
            pass
        self.clear_error()
```

---

## Migration Strategy Summary

### Preserved Business Logic
- ✅ Allocation algorithm and scoring system
- ✅ Conflict detection and atomic block model
- ✅ Professor preferences and constraints
- ✅ Reservation system and recurrence patterns
- ✅ All data models and relationships

### Transformed Patterns
- Streamlit session state → Reflex state classes with defensive mutation
- Page routing → Component composition with state-based navigation
- Synchronous operations → Async event handlers with loading states
- Multi-page app → Single-page reactive application
- `st.session_state` feedback → Toast notifications from state methods

### New Capabilities (Reflex Benefits)
- ✅ Real-time reactive UI updates
- ✅ Persistent client-side authentication
- ✅ Better error handling and loading states
- ✅ Modern component-based architecture
- ✅ Improved performance through computed properties

This architecture maintains the robustness of your existing business logic while modernizing the frontend into a maintainable, reactive Reflex application.
